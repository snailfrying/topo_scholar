import argparse
import csv
import hashlib
import html
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlencode, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
INPUT_CSV = ROOT / "data" / "metadata" / "origin_failed_review.csv"
OUTPUT_CSV = ROOT / "data" / "metadata" / "origin_source_candidates.csv"
CACHE_DIR = ROOT / "data" / "cache" / "origin_source_search"


FIELDS = [
    "discovered_at",
    "place_id",
    "code",
    "name",
    "full_name",
    "province",
    "city",
    "review_category",
    "query",
    "rank",
    "title",
    "url",
    "domain",
    "snippet",
    "source_class",
    "source_score",
]


KEYWORDS = {
    "origin": "\u5730\u540d\u7531\u6765",
    "name_origin": "\u540d\u79f0\u7531\u6765",
    "history": "\u5386\u53f2\u6cbf\u9769",
    "gov": "\u653f\u5e9c",
    "gazetteer": "\u5730\u65b9\u5fd7",
    "overview": "\u6982\u51b5",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def cache_path(query: str) -> Path:
    digest = hashlib.sha1(query.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{digest}.html"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def clean_html(value: str) -> str:
    value = re.sub(r"<script.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def normalize_url(url: str) -> str:
    if url.startswith("/ck/a?"):
        return url
    return html.unescape(url)


def domain_of(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except ValueError:
        return ""


def classify_source(url: str, title: str, snippet: str) -> tuple[str, int]:
    domain = domain_of(url)
    text = f"{domain} {title} {snippet}"
    score = 0
    source_class = "other"

    if domain.endswith(".gov.cn") or ".gov.cn" in domain:
        source_class = "local_government"
        score += 60
    if "mca.gov.cn" in domain or "dmfw.mca.gov.cn" in domain:
        source_class = "mca"
        score += 70
    if any(token in text for token in ("dfz", "fangzhi", KEYWORDS["gazetteer"], "\u5730\u60c5")):
        source_class = "gazetteer"
        score += 45
    if any(token in text for token in ("\u6c11\u653f", "\u884c\u653f\u533a\u5212", "\u5efa\u7f6e")):
        score += 12
    if any(token in text for token in (KEYWORDS["origin"], KEYWORDS["name_origin"], "\u5f97\u540d", "\u56e0", "\u53d6")):
        score += 18
    if any(token in text for token in (KEYWORDS["history"], "\u53bf\u60c5", "\u5e02\u60c5", KEYWORDS["overview"])):
        score += 8
    if any(token in domain for token in ("baike", "wikipedia", "zhihu", "sohu", "163.com", "qq.com")):
        score -= 30
        if source_class == "other":
            source_class = "reference_only"
    return source_class, max(score, 0)


def build_queries(row: dict[str, str], max_queries: int) -> list[str]:
    name = row["name"]
    province = row.get("province", "")
    city = row.get("city", "")
    full = " ".join(part for part in (province, city, f'"{name}"') if part)
    category = row.get("review_category", "")

    queries = [
        f"{full} {KEYWORDS['origin']} {KEYWORDS['gov']}",
        f"{full} {KEYWORDS['history']} {KEYWORDS['gov']}",
        f'"{name}" {KEYWORDS["name_origin"]} site:gov.cn',
        f'"{name}" {KEYWORDS["history"]} {KEYWORDS["gazetteer"]}',
    ]
    if category in {"direct_admin_county_level_city", "municipality_county_or_district_missing"}:
        queries.insert(1, f"{full} \u5e02\u60c5 {KEYWORDS['history']}")
    if category in {"nonstandard_or_functional_area", "special_managed_area"}:
        queries.insert(1, f"{full} \u8bbe\u7acb {KEYWORDS['history']}")
    return queries[:max_queries]


def fetch_bing(query: str, sleep_seconds: float, force: bool) -> str:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = cache_path(query)
    if path.exists() and not force:
        return path.read_text(encoding="utf-8", errors="replace")

    url = "https://www.bing.com/search?" + urlencode({"q": query, "count": "10", "mkt": "zh-CN"})
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
        ),
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    request = Request(url, headers=headers)
    with urlopen(request, timeout=20) as response:
        data = response.read()
    text = data.decode("utf-8", errors="replace")
    path.write_text(text, encoding="utf-8")
    if sleep_seconds > 0:
        time.sleep(sleep_seconds)
    return text


def parse_bing_results(text: str, limit: int) -> list[dict[str, str]]:
    items = re.findall(r'(<li class="b_algo"[^>]*>.*?)(?=<li class="b_algo"|</ol>)', text, flags=re.I | re.S)
    results: list[dict[str, str]] = []
    for item in items:
        match = re.search(r'<h2[^>]*>.*?<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?</h2>', item, flags=re.I | re.S)
        if not match:
            continue
        url = normalize_url(match.group(1))
        title = clean_html(match.group(2))
        snippet_match = re.search(r"<p[^>]*>(.*?)</p>", item, flags=re.I | re.S)
        snippet = clean_html(snippet_match.group(1)) if snippet_match else ""
        if not url.startswith("http"):
            continue
        results.append({"title": title, "url": url, "snippet": snippet})
        if len(results) >= limit:
            break
    return results


def is_relevant(row: dict[str, str], result: dict[str, str]) -> bool:
    name = row["name"]
    text = f"{result['title']} {result['snippet']} {unquote(result['url'])}"
    return name in text


def load_existing(path: Path) -> set[tuple[str, str, str]]:
    if not path.exists():
        return set()
    seen: set[tuple[str, str, str]] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            seen.add((row.get("place_id", ""), row.get("query", ""), row.get("url", "")))
    return seen


def append_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerows(rows)


def discover(args: argparse.Namespace) -> int:
    rows = read_rows(args.input)
    if args.category:
        allowed = set(args.category.split(","))
        rows = [row for row in rows if row.get("review_category") in allowed]
    if args.max_rows:
        rows = rows[: args.max_rows]

    seen = load_existing(args.output)
    out_rows: list[dict[str, str]] = []
    discovered_at = utc_now()
    errors = 0

    for index, row in enumerate(rows, 1):
        for query in build_queries(row, args.max_queries):
            try:
                html_text = fetch_bing(query, args.sleep, args.force)
                results = parse_bing_results(html_text, args.max_results)
            except (HTTPError, URLError, TimeoutError) as exc:
                errors += 1
                print(f"[warn] search failed: {query} ({exc})", file=sys.stderr)
                continue

            for rank, result in enumerate(results, 1):
                if not is_relevant(row, result):
                    continue
                source_class, score = classify_source(result["url"], result["title"], result["snippet"])
                if score < args.min_score:
                    continue
                key = (row["place_id"], query, result["url"])
                if key in seen:
                    continue
                out_rows.append(
                    {
                        "discovered_at": discovered_at,
                        "place_id": row["place_id"],
                        "code": row["code"],
                        "name": row["name"],
                        "full_name": row["full_name"],
                        "province": row["province"],
                        "city": row["city"],
                        "review_category": row["review_category"],
                        "query": query,
                        "rank": str(rank),
                        "title": result["title"],
                        "url": result["url"],
                        "domain": domain_of(result["url"]),
                        "snippet": result["snippet"],
                        "source_class": source_class,
                        "source_score": str(score),
                    }
                )
                seen.add(key)

        if args.flush_each and out_rows:
            append_rows(args.output, out_rows)
            out_rows.clear()
        print(f"[progress] {index}/{len(rows)} {row['name']}")

    if out_rows:
        append_rows(args.output, out_rows)
    if errors:
        print(f"[done] completed with {errors} search errors")
    return 0 if errors == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover web source candidates for unresolved place-name origins.")
    parser.add_argument("--input", type=Path, default=INPUT_CSV)
    parser.add_argument("--output", type=Path, default=OUTPUT_CSV)
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--max-queries", type=int, default=2)
    parser.add_argument("--max-results", type=int, default=5)
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument("--category", default="")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--flush-each", action="store_true")
    parser.add_argument("--min-score", type=int, default=30, help="Skip weak/non-authoritative search hits")
    args = parser.parse_args()
    raise SystemExit(discover(args))


if __name__ == "__main__":
    main()
