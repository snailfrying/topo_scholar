import csv
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from topo_scholar.bootstrap import ensure_database


DB_PATH = ROOT / "data" / "processed" / "topo_scholar.sqlite"
QUEUE_CSV = ROOT / "data" / "processed" / "collection_queue.csv"

FIELDS = [
    "id",
    "place_id",
    "code",
    "name",
    "full_name",
    "level",
    "province",
    "city",
    "county",
    "priority",
    "status",
    "source_strategy",
    "attempt_count",
    "last_attempt_at",
    "error",
    "created_at",
    "updated_at",
]


PRIORITY_BY_LEVEL = {
    "province": 10,
    "city": 20,
    "county": 30,
    "town": 60,
    "village": 90,
}

EXCLUDED_COLLECTION_NAMES = {
    "市辖区",
    "县",
    "省直辖县级行政区划",
    "自治区直辖县级行政区划",
}

EXCLUDED_COLLECTION_KEYWORDS = {
    "开发区",
    "管理区",
    "园区",
    "示范区",
}


def should_collect_name(name: str) -> bool:
    if name in EXCLUDED_COLLECTION_NAMES:
        return False
    return not any(keyword in name for keyword in EXCLUDED_COLLECTION_KEYWORDS)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def queue_id(place_id: str) -> str:
    return f"origin:{place_id}"


def build_queue(levels: list[str], overwrite: bool = False) -> list[dict[str, str]]:
    ensure_database(DB_PATH)
    now = utc_now()
    level_placeholders = ",".join("?" for _ in levels)
    sql = f"""
        SELECT id, code, name, full_name, level, province, city, county
        FROM places
        WHERE level IN ({level_placeholders})
        ORDER BY
          CASE level
            WHEN 'province' THEN 1
            WHEN 'city' THEN 2
            WHEN 'county' THEN 3
            WHEN 'town' THEN 4
            WHEN 'village' THEN 5
            ELSE 9
          END,
          code
    """

    existing: dict[str, dict[str, str]] = {}
    if QUEUE_CSV.exists():
        with QUEUE_CSV.open("r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                existing[row["id"]] = row

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(sql, levels).fetchall()

    queue_rows: dict[str, dict[str, str]] = {} if overwrite else dict(existing)
    for place_id, code, name, full_name, level, province, city, county in rows:
        if not should_collect_name(name):
            continue
        qid = queue_id(place_id)
        if qid in queue_rows and not overwrite:
            continue
        if qid in existing:
            preserved = dict(existing[qid])
            preserved.update(
                {
                    "place_id": place_id,
                    "code": code,
                    "name": name,
                    "full_name": full_name,
                    "level": level,
                    "province": province,
                    "city": city,
                    "county": county,
                    "priority": str(PRIORITY_BY_LEVEL.get(level, 100)),
                    "updated_at": now,
                }
            )
            queue_rows[qid] = preserved
            continue
        queue_rows[qid] = {
            "id": qid,
            "place_id": place_id,
            "code": code,
            "name": name,
            "full_name": full_name,
            "level": level,
            "province": province,
            "city": city,
            "county": county,
            "priority": str(PRIORITY_BY_LEVEL.get(level, 100)),
            "status": "pending",
            "source_strategy": "mca_geonames",
            "attempt_count": "0",
            "last_attempt_at": "",
            "error": "",
            "created_at": now,
            "updated_at": now,
        }

    queue = sorted(
        queue_rows.values(),
        key=lambda row: (int(row["priority"]), row["level"], row["code"]),
    )
    QUEUE_CSV.parent.mkdir(parents=True, exist_ok=True)
    with QUEUE_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(queue)
    return queue


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Build origin collection queue from local places.")
    parser.add_argument(
        "--levels",
        default="province,city,county",
        help="Comma-separated levels, e.g. province,city,county,town,village",
    )
    parser.add_argument("--overwrite", action="store_true", help="Replace existing queue rows")
    args = parser.parse_args()

    levels = [level.strip() for level in args.levels.split(",") if level.strip()]
    queue = build_queue(levels, overwrite=args.overwrite)
    print(f"Wrote {len(queue)} queue rows to {QUEUE_CSV}")


if __name__ == "__main__":
    main()
