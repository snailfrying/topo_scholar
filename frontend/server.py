"""Small dependency-free web server for the TopoScholar browser UI."""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = Path(__file__).resolve().parent / "static"
DB_PATH = ROOT / "data" / "processed" / "topo_scholar.sqlite"
QUALITY_REPORT = ROOT / "data" / "metadata" / "quality_report.json"
NEXT_QUEUE = ROOT / "data" / "processed" / "collection_queue_next_stage.csv"
SUMMARY_CACHE: dict[str, Any] | None = None
MAP_CACHE: dict[str, Any] | None = None
KNOWLEDGE_CACHE: list[dict[str, Any]] | None = None

LEVEL_LABELS = {
    "province": "省级",
    "city": "地级",
    "county": "县级",
    "town": "乡镇/街道",
    "village": "村/社区",
}

PROVINCE_POINTS = {
    "北京市": (116.4074, 39.9042),
    "天津市": (117.2000, 39.1333),
    "河北省": (114.5149, 38.0428),
    "山西省": (112.5492, 37.8570),
    "内蒙古自治区": (111.6708, 40.8183),
    "辽宁省": (123.4291, 41.7968),
    "吉林省": (125.3245, 43.8868),
    "黑龙江省": (126.6425, 45.7567),
    "上海市": (121.4737, 31.2304),
    "江苏省": (118.7969, 32.0603),
    "浙江省": (120.1551, 30.2741),
    "安徽省": (117.2272, 31.8206),
    "福建省": (119.2965, 26.0745),
    "江西省": (115.8582, 28.6829),
    "山东省": (117.1201, 36.6512),
    "河南省": (113.6254, 34.7466),
    "湖北省": (114.3054, 30.5931),
    "湖南省": (112.9388, 28.2282),
    "广东省": (113.2644, 23.1291),
    "广西壮族自治区": (108.3669, 22.8170),
    "海南省": (110.3312, 20.0310),
    "重庆市": (106.5516, 29.5630),
    "四川省": (104.0665, 30.5728),
    "贵州省": (106.6302, 26.6470),
    "云南省": (102.8329, 24.8801),
    "西藏自治区": (91.1172, 29.6469),
    "陕西省": (108.9398, 34.3416),
    "甘肃省": (103.8343, 36.0611),
    "青海省": (101.7782, 36.6171),
    "宁夏回族自治区": (106.2309, 38.4872),
    "新疆维吾尔自治区": (87.6168, 43.8256),
}


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [{key: row[key] for key in row.keys()} for row in rows]


def int_param(params: dict[str, list[str]], name: str, default: int, max_value: int) -> int:
    raw = (params.get(name) or [str(default)])[0]
    try:
        value = int(raw)
    except ValueError:
        value = default
    return max(0, min(value, max_value))


def str_param(params: dict[str, list[str]], name: str) -> str:
    return (params.get(name) or [""])[0].strip()


def load_quality_report() -> dict[str, Any]:
    if not QUALITY_REPORT.exists():
        return {}
    return json.loads(QUALITY_REPORT.read_text(encoding="utf-8"))


def read_next_queue_status() -> dict[str, int]:
    status: dict[str, int] = {}
    if not NEXT_QUEUE.exists():
        return status
    with NEXT_QUEUE.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            key = row.get("status") or "unknown"
            status[key] = status.get(key, 0) + 1
    return status


def load_knowledge_cache() -> list[dict[str, Any]]:
    global KNOWLEDGE_CACHE
    if KNOWLEDGE_CACHE is not None:
        return KNOWLEDGE_CACHE
    with connect() as conn:
        KNOWLEDGE_CACHE = rows_to_dicts(
            conn.execute(
                """
                SELECT k.id, k.place_id, k.standard_name, k.province, k.city, k.county, k.place_type,
                       k.origin, k.meaning, k.history, k.old_names, k.confidence, k.source_type,
                       k.evidence_title, k.evidence_url, k.updated_at,
                       p.code AS local_code, p.name AS local_name, p.full_name AS local_full_name,
                       p.level AS local_level
                FROM place_knowledge AS k
                LEFT JOIN places AS p ON p.id = k.place_id
                """
            ).fetchall()
        )
    return KNOWLEDGE_CACHE


def summary_payload() -> dict[str, Any]:
    global SUMMARY_CACHE
    if SUMMARY_CACHE is not None:
        return SUMMARY_CACHE
    quality = load_quality_report()
    with connect() as conn:
        levels = rows_to_dicts(
            conn.execute(
                "SELECT level, COUNT(*) AS count FROM places GROUP BY level ORDER BY count DESC"
            ).fetchall()
        )
        source_types = rows_to_dicts(
            conn.execute(
                "SELECT source_type, COUNT(*) AS count FROM place_knowledge GROUP BY source_type ORDER BY count DESC"
            ).fetchall()
        )
        confidence = rows_to_dicts(
            conn.execute(
                "SELECT confidence, COUNT(*) AS count FROM place_knowledge GROUP BY confidence ORDER BY count DESC"
            ).fetchall()
        )
        knowledge_types = rows_to_dicts(
            conn.execute(
                "SELECT place_type, COUNT(*) AS count FROM place_knowledge GROUP BY place_type ORDER BY count DESC"
            ).fetchall()
        )
        provinces = rows_to_dicts(
            conn.execute("SELECT province, COUNT(*) AS count FROM places GROUP BY province ORDER BY province").fetchall()
        )
    SUMMARY_CACHE = {
        "counts": quality.get("counts", {}),
        "levels": levels,
        "levelLabels": LEVEL_LABELS,
        "sourceTypes": source_types,
        "confidence": confidence,
        "knowledgeTypes": knowledge_types,
        "queueStatus": read_next_queue_status(),
        "provinces": provinces,
    }
    return SUMMARY_CACHE


def build_where(params: dict[str, list[str]], table_alias: str = "p") -> tuple[list[str], list[Any]]:
    clauses: list[str] = []
    values: list[Any] = []
    for key in ("province", "city", "county", "level"):
        value = str_param(params, key)
        if value:
            column = "place_type" if key == "level" and table_alias == "k" else key
            clauses.append(f"{table_alias}.{column} = ?")
            values.append(value)
    return clauses, values


def search_places(params: dict[str, list[str]]) -> dict[str, Any]:
    q = str_param(params, "q")
    limit = int_param(params, "limit", 10, 500)
    offset = int_param(params, "offset", 0, 1_000_000)
    clauses, values = build_where(params, "p")
    order_values: list[Any] = []
    if q:
        clauses.append("(p.name LIKE ? OR p.full_name LIKE ? OR p.code LIKE ?)")
        values.extend([f"%{q}%", f"%{q}%", f"%{q}%"])
        order_values = [q, f"{q}%", f"{q}%", f"{q}%", f"{q}%", f"%{q}%"]
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    relevance_order = (
        "CASE "
        "WHEN p.name = ? THEN 0 "
        "WHEN p.province LIKE ? THEN 1 "
        "WHEN p.city LIKE ? THEN 2 "
        "WHEN p.county LIKE ? THEN 3 "
        "WHEN p.name LIKE ? THEN 4 "
        "WHEN p.full_name LIKE ? THEN 5 "
        "ELSE 9 END,"
        if q
        else ""
    )
    level_order = (
        "CASE p.level "
        "WHEN 'province' THEN 0 "
        "WHEN 'city' THEN 1 "
        "WHEN 'county' THEN 2 "
        "WHEN 'town' THEN 3 "
        "WHEN 'village' THEN 4 "
        "ELSE 9 END"
    )
    with connect() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM places AS p {where}", values).fetchone()[0]
        rows = rows_to_dicts(
            conn.execute(
                f"""
                SELECT p.id, p.code, p.name, p.full_name, p.level, p.type, p.parent_code,
                       p.province, p.city, p.county, p.town
                FROM places AS p
                {where}
                ORDER BY {relevance_order} {level_order}, p.code
                LIMIT ? OFFSET ?
                """,
                [*values, *order_values, limit, offset],
            ).fetchall()
        )
    return {"items": rows, "total": total, "limit": limit, "offset": offset}


def search_knowledge(params: dict[str, list[str]]) -> dict[str, Any]:
    q = str_param(params, "q")
    limit = int_param(params, "limit", 10, 500)
    offset = int_param(params, "offset", 0, 1_000_000)
    filters = {
        "province": str_param(params, "province"),
        "city": str_param(params, "city"),
        "county": str_param(params, "county"),
        "source_type": str_param(params, "source_type"),
        "confidence": str_param(params, "confidence"),
        "place_type": str_param(params, "place_type"),
    }
    rows = []
    for row in load_knowledge_cache():
        if any(value and row.get(key) != value for key, value in filters.items()):
            continue
        if q:
            haystack = "|".join(
                str(row.get(key) or "")
                for key in (
                    "standard_name",
                    "origin",
                    "meaning",
                    "history",
                    "old_names",
                    "province",
                    "city",
                    "county",
                    "local_name",
                    "local_full_name",
                    "local_code",
                )
            )
            if q not in haystack:
                continue
        rows.append(row)

    rows.sort(key=lambda row: knowledge_sort_key(row, q))
    return {"items": rows[offset : offset + limit], "total": len(rows), "limit": limit, "offset": offset}


def level_rank(level: str) -> int:
    return {"province": 0, "city": 1, "county": 2, "town": 3, "village": 4}.get(level or "", 9)


def knowledge_sort_key(row: dict[str, Any], q: str) -> tuple[Any, ...]:
    if not q:
        return (level_rank(str(row.get("local_level") or "")), str(row.get("local_code") or ""), str(row.get("standard_name") or ""))
    standard_name = str(row.get("standard_name") or "")
    local_name = str(row.get("local_name") or "")
    province = str(row.get("province") or "")
    city = str(row.get("city") or "")
    county = str(row.get("county") or "")
    full_name = str(row.get("local_full_name") or "")
    if standard_name == q or local_name == q:
        bucket = 0
    elif province.startswith(q):
        bucket = 1
    elif city.startswith(q):
        bucket = 2
    elif county.startswith(q):
        bucket = 3
    elif standard_name.startswith(q) or local_name.startswith(q):
        bucket = 4
    elif q in full_name:
        bucket = 5
    else:
        bucket = 9
    return (bucket, level_rank(str(row.get("local_level") or "")), str(row.get("local_code") or ""), standard_name)


def search_queue(params: dict[str, list[str]]) -> dict[str, Any]:
    q = str_param(params, "q")
    limit = int_param(params, "limit", 10, 500)
    offset = int_param(params, "offset", 0, 1_000_000)
    status = str_param(params, "status")
    province = str_param(params, "province")
    rows: list[dict[str, str]] = []
    if NEXT_QUEUE.exists():
        with NEXT_QUEUE.open("r", encoding="utf-8-sig", newline="") as file:
            for row in csv.DictReader(file):
                if status and row.get("status") != status:
                    continue
                if province and row.get("province") != province:
                    continue
                haystack = "|".join(row.get(key, "") for key in ("name", "full_name", "code", "error"))
                if q and q not in haystack:
                    continue
                rows.append(row)
    return {"items": rows[offset : offset + limit], "total": len(rows), "limit": limit, "offset": offset}


def map_payload() -> dict[str, Any]:
    global MAP_CACHE
    if MAP_CACHE is not None:
        return MAP_CACHE
    with connect() as conn:
        rows = rows_to_dicts(
            conn.execute(
                """
                SELECT p.province,
                       COUNT(DISTINCT p.id) AS places,
                       COUNT(DISTINCT k.id) AS knowledge
                FROM places AS p
                LEFT JOIN place_knowledge AS k ON k.place_id = p.id
                GROUP BY p.province
                ORDER BY p.province
                """
            ).fetchall()
        )
    items = []
    for row in rows:
        province = row.get("province") or ""
        if province not in PROVINCE_POINTS:
            continue
        lon, lat = PROVINCE_POINTS[province]
        items.append({**row, "lon": lon, "lat": lat})
    MAP_CACHE = {"items": items, "bounds": {"minLon": 73, "maxLon": 135, "minLat": 18, "maxLat": 54}}
    return MAP_CACHE


def api_payload(path: str, params: dict[str, list[str]]) -> dict[str, Any]:
    if path == "/api/summary":
        return summary_payload()
    if path == "/api/search":
        dataset = str_param(params, "dataset") or "places"
        if dataset == "knowledge":
            return search_knowledge(params)
        if dataset == "queue":
            return search_queue(params)
        return search_places(params)
    if path == "/api/map":
        return map_payload()
    return {"error": "not_found"}


class TopoScholarHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self) -> None:  # noqa: N802 - stdlib hook name
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self.send_json(api_payload(parsed.path, parse_qs(parsed.query)))
            return
        if parsed.path == "/":
            self.path = "/index.html"
        super().do_GET()

    def send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local TopoScholar frontend.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    host = args.host
    port = args.port
    server = ThreadingHTTPServer((host, port), TopoScholarHandler)
    print(f"TopoScholar frontend: http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
