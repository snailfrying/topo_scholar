import argparse
import csv
import hashlib
import json
import sqlite3
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from topo_scholar.normalize import generate_aliases

DB_PATH = ROOT / "data" / "processed" / "topo_scholar.sqlite"
CACHE_DIR = ROOT / "data" / "cache" / "mca_geonames"
PROCESSED_DIR = ROOT / "data" / "processed"
KNOWLEDGE_CSV = PROCESSED_DIR / "place_knowledge.csv"

CACHE_LOCK = threading.Lock()
KNOWLEDGE_WRITE_LOCK = threading.Lock()
AUDIT_WRITE_LOCK = threading.Lock()

BASE_URL = "https://dmfw.mca.gov.cn/9095"
SOURCE = "中国·国家地名信息库"
SOURCE_TYPE = "official"
SOURCE_URL = "https://dmfw.mca.gov.cn/"


KNOWLEDGE_FIELDS = [
    "id",
    "place_id",
    "source_place_id",
    "standard_name",
    "province",
    "city",
    "county",
    "place_type",
    "origin",
    "meaning",
    "history",
    "old_names",
    "evidence_url",
    "evidence_title",
    "evidence_quote",
    "confidence",
    "source",
    "source_type",
    "raw_hash",
    "fetched_at",
    "updated_at",
]

CANDIDATE_AUDIT_CSV = ROOT / "data" / "metadata" / "mca_candidate_audit.csv"
CANDIDATE_AUDIT_FIELDS = [
    "fetched_at",
    "query_name",
    "filter_province",
    "filter_city",
    "filter_county",
    "filter_place_type",
    "source_place_id",
    "standard_name",
    "place_type",
    "province",
    "city",
    "county",
    "score",
    "selected",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_id(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def cache_key(prefix: str, params: dict[str, Any]) -> Path:
    encoded = json.dumps(params, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha1(encoded.encode("utf-8")).hexdigest()
    return CACHE_DIR / prefix / f"{digest}.json"


def request_json(
    path: str,
    params: dict[str, Any],
    referer: str,
    sleep_seconds: float,
    retries: int = 3,
) -> dict[str, Any]:
    cache_path = cache_key(path.strip("/").replace("/", "_"), params)
    with CACHE_LOCK:
        if cache_path.exists():
            return json.loads(cache_path.read_text(encoding="utf-8"))

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"{BASE_URL}{path}?{urlencode(params)}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
        ),
        "Referer": referer,
        "Accept": "application/json, text/plain, */*",
    }
    req = Request(url, headers=headers)
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
            break
        except HTTPError as exc:
            last_error = exc
            if attempt >= retries:
                raise RuntimeError(f"HTTP {exc.code} from MCA endpoint: {url}") from exc
        except URLError as exc:
            last_error = exc
            if attempt >= retries:
                raise RuntimeError(f"Network error from MCA endpoint: {url}: {exc}") from exc
        if sleep_seconds > 0:
            time.sleep(max(sleep_seconds, 1.0) * attempt)
    else:
        raise RuntimeError(f"Network error from MCA endpoint: {url}: {last_error}")

    with CACHE_LOCK:
        tmp_path = cache_path.with_suffix(f".{threading.get_ident()}.tmp")
        tmp_path.write_text(raw, encoding="utf-8")
        tmp_path.replace(cache_path)
    if sleep_seconds > 0:
        time.sleep(sleep_seconds)
    return json.loads(raw)


def search_mca(name: str, page: int, size: int, sleep_seconds: float) -> dict[str, Any]:
    return request_json(
        "/stname/listPub",
        {"stName": name, "searchType": "模糊", "page": page, "size": size},
        "https://dmfw.mca.gov.cn/search.html",
        sleep_seconds,
    )


def search_mca_pages(name: str, max_pages: int, size: int, sleep_seconds: float) -> tuple[list[dict[str, Any]], int]:
    records: list[dict[str, Any]] = []
    total = 0
    for page in range(1, max_pages + 1):
        result = search_mca(name, page=page, size=size, sleep_seconds=sleep_seconds)
        page_records = result.get("records") or []
        total = int(result.get("total") or len(page_records) or total)
        records.extend(page_records)
        if not page_records or len(records) >= total:
            break
    return records, total


def details_mca(source_place_id: str, sleep_seconds: float) -> dict[str, Any]:
    # The public web page uses placeType=2 for details queries.
    return request_json(
        "/stname/detailsPub",
        {"placeType": "2", "id": source_place_id},
        "https://dmfw.mca.gov.cn/search.html",
        sleep_seconds,
    )


def ensure_knowledge_table(conn: sqlite3.Connection) -> None:
    columns = ", ".join(f"{field} TEXT" for field in KNOWLEDGE_FIELDS)
    conn.execute(f"CREATE TABLE IF NOT EXISTS place_knowledge ({columns}, PRIMARY KEY(id))")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_place_knowledge_id ON place_knowledge(id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_place_knowledge_place_id ON place_knowledge(place_id)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_place_knowledge_source_place_id "
        "ON place_knowledge(source_place_id)"
    )
    conn.commit()


def local_candidates(
    conn: sqlite3.Connection,
    name: str,
    province: str = "",
    city: str = "",
    county: str = "",
    limit: int = 50,
) -> list[dict[str, str]]:
    clauses = ["name = ?"]
    params: list[Any] = [name]
    if province:
        clauses.append("province = ?")
        params.append(province)
    if city:
        clauses.append("city = ?")
        params.append(city)
    if county:
        clauses.append("county = ?")
        params.append(county)
    params.append(limit)
    sql = f"""
        SELECT id, code, name, full_name, level, province, city, county, town
        FROM places
        WHERE {" AND ".join(clauses)}
        ORDER BY level, code
        LIMIT ?
    """
    rows = []
    for row in conn.execute(sql, params):
        rows.append(
            {
                "id": row[0],
                "code": row[1],
                "name": row[2],
                "full_name": row[3],
                "level": row[4],
                "province": row[5],
                "city": row[6],
                "county": row[7],
                "town": row[8],
            }
        )
    return rows


def match_local_place(conn: sqlite3.Connection, detail: dict[str, Any]) -> str:
    name = detail.get("standard_name") or ""
    province = detail.get("province_name") or ""
    city = detail.get("city_name") or ""
    county = detail.get("area_name") or ""

    candidates = local_candidates(conn, name, province=province, city=city, county=county, limit=5)
    if candidates:
        return candidates[0]["id"]

    candidates = local_candidates(conn, name, province=province, city=city, limit=5)
    if candidates:
        return candidates[0]["id"]

    candidates = local_candidates(conn, name, province=province, limit=5)
    if candidates:
        return candidates[0]["id"]

    # Fall back to generated aliases, e.g. "南高村" vs "南高村村民委员会".
    try:
        for alias in generate_aliases(name):
            rows = conn.execute(
                """
                SELECT p.id
                FROM place_aliases a
                JOIN places p ON p.id = a.place_id
                WHERE a.alias = ?
                  AND (? = '' OR p.province = ?)
                  AND (? = '' OR p.city = ?)
                  AND (? = '' OR p.county = ?)
                ORDER BY p.level, p.code
                LIMIT 1
                """,
                [alias, province, province, city, city, county, county],
            ).fetchall()
            if rows:
                return rows[0][0]
    except sqlite3.OperationalError:
        pass

    return ""


def confidence_for(detail: dict[str, Any]) -> str:
    if detail.get("place_origin") or detail.get("place_meaning") or detail.get("place_history"):
        return "high"
    return "low"


def evidence_quote(detail: dict[str, Any]) -> str:
    for key in ("place_origin", "place_meaning", "place_history"):
        value = (detail.get(key) or "").strip()
        if value:
            return value[:180]
    return ""


def normalize_knowledge(conn: sqlite3.Connection, detail: dict[str, Any]) -> dict[str, str]:
    fetched_at = utc_now()
    raw_text = json.dumps(detail, ensure_ascii=False, sort_keys=True)
    source_place_id = detail.get("id") or ""
    standard_name = detail.get("standard_name") or ""
    row_id = stable_id(SOURCE, source_place_id, standard_name)
    return {
        "id": row_id,
        "place_id": match_local_place(conn, detail),
        "source_place_id": source_place_id,
        "standard_name": standard_name,
        "province": detail.get("province_name") or "",
        "city": detail.get("city_name") or "",
        "county": detail.get("area_name") or "",
        "place_type": detail.get("place_type") or "",
        "origin": detail.get("place_origin") or "",
        "meaning": detail.get("place_meaning") or "",
        "history": detail.get("place_history") or "",
        "old_names": detail.get("old_name") or "",
        "evidence_url": SOURCE_URL,
        "evidence_title": SOURCE,
        "evidence_quote": evidence_quote(detail),
        "confidence": confidence_for(detail),
        "source": SOURCE,
        "source_type": SOURCE_TYPE,
        "raw_hash": sha256_text(raw_text),
        "fetched_at": fetched_at,
        "updated_at": fetched_at,
    }


def upsert_knowledge(conn: sqlite3.Connection, row: dict[str, str]) -> None:
    ensure_knowledge_table(conn)
    placeholders = ", ".join("?" for _ in KNOWLEDGE_FIELDS)
    columns = ", ".join(KNOWLEDGE_FIELDS)
    updates = ", ".join(f"{field}=excluded.{field}" for field in KNOWLEDGE_FIELDS if field != "id")
    sql = f"""
        INSERT INTO place_knowledge ({columns})
        VALUES ({placeholders})
        ON CONFLICT(id) DO UPDATE SET {updates}
    """
    conn.execute(sql, [row.get(field, "") for field in KNOWLEDGE_FIELDS])
    conn.commit()


def append_or_update_csv(row: dict[str, str]) -> None:
    with KNOWLEDGE_WRITE_LOCK:
        existing: dict[str, dict[str, str]] = {}
        if KNOWLEDGE_CSV.exists():
            with KNOWLEDGE_CSV.open("r", encoding="utf-8", newline="") as f:
                for item in csv.DictReader(f):
                    existing[item["id"]] = item
        existing[row["id"]] = row
        with KNOWLEDGE_CSV.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=KNOWLEDGE_FIELDS)
            writer.writeheader()
            writer.writerows(existing.values())


def passes_filters(record: dict[str, Any], province: str, city: str, county: str, place_type: str) -> bool:
    if province and record.get("province_name") != province:
        return False
    # In statistical data, districts of municipalities often have city="市辖区";
    # in the geonames DB, the same county-level entity may appear as city_name=标准名.
    if city and city != "市辖区" and record.get("city_name") != city:
        return False
    if county and county not in {
        record.get("area_name"),
        record.get("city_name"),
        record.get("standard_name"),
    }:
        return False
    if place_type and record.get("place_type") != place_type:
        return False
    return True


def score_candidate(
    record: dict[str, Any],
    *,
    name: str,
    province: str = "",
    city: str = "",
    county: str = "",
    place_type: str = "",
) -> int:
    score = 0
    standard_name = record.get("standard_name") or ""
    if standard_name == name:
        score += 100
    elif name and name in standard_name:
        score += 20
    else:
        score -= 100

    if place_type:
        score += 60 if record.get("place_type") == place_type else -80
    if province:
        score += 40 if record.get("province_name") == province else -80
    if city and city != "市辖区":
        score += 25 if record.get("city_name") == city else -50
    if county:
        score += 25 if county in {
            record.get("area_name"),
            record.get("city_name"),
            record.get("standard_name"),
        } else -50

    # Prefer administrative entities when caller is collecting administrative levels.
    if place_type and "行政区" in place_type and "行政区" in (record.get("place_type") or ""):
        score += 10
    return score


def rank_candidates(
    records: list[dict[str, Any]],
    *,
    name: str,
    province: str = "",
    city: str = "",
    county: str = "",
    place_type: str = "",
    strict: bool = True,
) -> list[dict[str, Any]]:
    ranked = []
    for record in records:
        score = score_candidate(
            record,
            name=name,
            province=province,
            city=city,
            county=county,
            place_type=place_type,
        )
        item = dict(record)
        item["_score"] = score
        if strict and not passes_filters(record, province, city, county, place_type):
            continue
        if strict and record.get("standard_name") != name:
            continue
        ranked.append(item)
    ranked.sort(key=lambda row: row.get("_score", 0), reverse=True)
    return ranked


def append_candidate_audit(
    *,
    query_name: str,
    province: str,
    city: str,
    county: str,
    place_type: str,
    candidates: list[dict[str, Any]],
    selected_ids: set[str],
) -> None:
    with AUDIT_WRITE_LOCK:
        existing: list[dict[str, str]] = []
        if CANDIDATE_AUDIT_CSV.exists():
            with CANDIDATE_AUDIT_CSV.open("r", encoding="utf-8", newline="") as f:
                existing = list(csv.DictReader(f))

        now = utc_now()
        for record in candidates:
            source_place_id = record.get("id") or ""
            existing.append(
                {
                    "fetched_at": now,
                    "query_name": query_name,
                    "filter_province": province,
                    "filter_city": city,
                    "filter_county": county,
                    "filter_place_type": place_type,
                    "source_place_id": source_place_id,
                    "standard_name": record.get("standard_name") or "",
                    "place_type": record.get("place_type") or "",
                    "province": record.get("province_name") or "",
                    "city": record.get("city_name") or "",
                    "county": record.get("area_name") or "",
                    "score": str(record.get("_score", "")),
                    "selected": "1" if source_place_id in selected_ids else "0",
                }
            )

        CANDIDATE_AUDIT_CSV.parent.mkdir(parents=True, exist_ok=True)
        with CANDIDATE_AUDIT_CSV.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CANDIDATE_AUDIT_FIELDS)
            writer.writeheader()
            writer.writerows(existing)


def print_candidates(records: list[dict[str, Any]]) -> None:
    for index, record in enumerate(records, start=1):
        path = "/".join(
            part
            for part in [
                record.get("province_name"),
                record.get("city_name"),
                record.get("area_name"),
                record.get("standard_name"),
            ]
            if part
        )
        print(f"{index}. {record.get('standard_name')} [{record.get('place_type')}] {path} id={record.get('id')}")


def fetch_and_save(
    name: str,
    *,
    province: str = "",
    city: str = "",
    county: str = "",
    place_type: str = "",
    limit: int = 5,
    page_size: int = 20,
    max_pages: int = 3,
    sleep_seconds: float = 0.8,
    list_only: bool = False,
    strict: bool = True,
) -> dict[str, Any]:
    records, total = search_mca_pages(name, max_pages=max_pages, size=page_size, sleep_seconds=sleep_seconds)
    filtered = rank_candidates(
        records,
        name=name,
        province=province,
        city=city,
        county=county,
        place_type=place_type,
        strict=strict,
    )

    candidates = []
    for record in filtered[:limit]:
        path = "/".join(
            part
            for part in [
                record.get("province_name"),
                record.get("city_name"),
                record.get("area_name"),
                record.get("standard_name"),
            ]
            if part
        )
        candidates.append(
            {
                "source_place_id": record.get("id") or "",
                "standard_name": record.get("standard_name") or "",
                "place_type": record.get("place_type") or "",
                "province": record.get("province_name") or "",
                "city": record.get("city_name") or "",
                "county": record.get("area_name") or "",
                "path": path,
                "score": record.get("_score", 0),
            }
        )

    saved = []
    if not list_only and candidates:
        with sqlite3.connect(DB_PATH) as conn:
            for candidate in candidates:
                detail = details_mca(candidate["source_place_id"], sleep_seconds=sleep_seconds)
                row = normalize_knowledge(conn, detail)
                with KNOWLEDGE_WRITE_LOCK:
                    upsert_knowledge(conn, row)
                append_or_update_csv(row)
                saved.append(row)

    append_candidate_audit(
        query_name=name,
        province=province,
        city=city,
        county=county,
        place_type=place_type,
        candidates=filtered[: max(limit, 5)],
        selected_ids={candidate["source_place_id"] for candidate in candidates},
    )

    warnings = []
    if not filtered:
        warnings.append("国家地名信息库未找到符合过滤条件的候选")
    if len(filtered) > limit:
        warnings.append(f"候选结果已截断到 {limit} 条，可提高 limit 或增加省市县/类型过滤")

    return {
        "ok": True,
        "data": {
            "search_total": total,
            "page_records": len(records),
            "filtered": len(filtered),
            "candidates": candidates,
            "saved": saved,
        },
        "source": SOURCE,
        "warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch place origin from China National Geographical Names DB.")
    parser.add_argument("name", help="Place name to search")
    parser.add_argument("--province", default="", help="Filter by province name, e.g. 湖北省")
    parser.add_argument("--city", default="", help="Filter by city name, e.g. 武汉市")
    parser.add_argument("--county", default="", help="Filter by county/district name, e.g. 江岸区")
    parser.add_argument("--place-type", default="", help="Filter by MCA place type, e.g. 地级行政区")
    parser.add_argument("--limit", type=int, default=5, help="Max details to fetch")
    parser.add_argument("--page-size", type=int, default=20, help="Search page size")
    parser.add_argument("--max-pages", type=int, default=3, help="Max search pages to inspect")
    parser.add_argument("--sleep", type=float, default=0.8, help="Delay after uncached network requests")
    parser.add_argument("--list-only", action="store_true", help="Only list candidates, do not fetch details")
    parser.add_argument("--loose", action="store_true", help="Allow non-exact candidates")
    args = parser.parse_args()

    payload = fetch_and_save(
        args.name,
        province=args.province,
        city=args.city,
        county=args.county,
        place_type=args.place_type,
        limit=args.limit,
        page_size=args.page_size,
        max_pages=args.max_pages,
        sleep_seconds=args.sleep,
        list_only=args.list_only,
        strict=not args.loose,
    )

    data = payload["data"]
    print(
        f"MCA search total={data['search_total']}, "
        f"page_records={data['page_records']}, filtered={data['filtered']}"
    )

    for index, candidate in enumerate(data["candidates"], start=1):
        print(
            f"{index}. {candidate['standard_name']} [{candidate['place_type']}] "
            f"{candidate['path']} id={candidate['source_place_id']}"
        )
    for row in data["saved"]:
        print(
            "saved",
            row["standard_name"],
            row["place_type"],
            f"origin={bool(row['origin'])}",
            f"meaning={bool(row['meaning'])}",
            f"history={bool(row['history'])}",
            f"place_id={row['place_id'] or 'unmatched'}",
        )
    if payload["warnings"]:
        for warning in payload["warnings"]:
            print("warning:", warning)


if __name__ == "__main__":
    main()
