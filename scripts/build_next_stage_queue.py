import argparse
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
DEFAULT_QUEUE = ROOT / "data" / "processed" / "collection_queue_next_stage.csv"

FIELDS = [
    "id",
    "place_id",
    "code",
    "name",
    "normalized_query_name",
    "full_name",
    "level",
    "province",
    "city",
    "county",
    "town",
    "collection_phase",
    "priority",
    "status",
    "source_strategy",
    "risk_flag",
    "attempt_count",
    "last_attempt_at",
    "error",
    "created_at",
    "updated_at",
]

EXCLUDED_KEYWORDS = {
    "开发区",
    "管理区",
    "园区",
    "示范区",
}

VILLAGE_SUFFIXES = [
    "社区居民委员会",
    "村民委员会",
    "社区居委会",
    "居民委员会",
    "村委会",
    "居委会",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def queue_id(phase: str, place_id: str) -> str:
    return f"next_origin:{phase}:{place_id}"


def normalize_query_name(name: str, level: str) -> str:
    if level != "village":
        return name
    for suffix in VILLAGE_SUFFIXES:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def phase_where(phase: str) -> tuple[str, list[str]]:
    if phase == "admin_street_pilot":
        return "level = ? AND name LIKE ?", ["town", "%街道"]
    if phase == "town_fast":
        return "level = ?", ["town"]
    if phase == "village_seed":
        return "level = ? AND (name LIKE ? OR name LIKE ? OR name LIKE ?)", [
            "village",
            "%村委会",
            "%村民委员会",
            "%嘎查",
        ]
    raise ValueError(f"Unsupported phase: {phase}")


def infer_risk_flag(name: str, level: str) -> str:
    if level == "town" and any(keyword in name for keyword in EXCLUDED_KEYWORDS):
        return "nonstandard_area"
    if level == "village" and ("社区" in name or "居委会" in name):
        return "community_new_name"
    return ""


def already_has_knowledge(conn: sqlite3.Connection, place_id: str) -> bool:
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM place_knowledge WHERE place_id = ?",
            [place_id],
        ).fetchone()[0]
    except sqlite3.OperationalError:
        return False
    return count > 0


def build_queue(phase: str, output: Path, limit: int = 0, overwrite: bool = False) -> list[dict[str, str]]:
    ensure_database(DB_PATH)
    now = utc_now()
    where, params = phase_where(phase)
    sql = f"""
        SELECT id, code, name, full_name, level, province, city, county, town
        FROM places
        WHERE {where}
        ORDER BY code
    """
    if limit > 0:
        sql += " LIMIT ?"
        params.append(str(limit))

    existing: dict[str, dict[str, str]] = {}
    if output.exists() and not overwrite:
        with output.open("r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                existing[row["id"]] = row

    queue_rows: dict[str, dict[str, str]] = {} if overwrite else dict(existing)
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(sql, params).fetchall()
        for place_id, code, name, full_name, level, province, city, county, town in rows:
            qid = queue_id(phase, place_id)
            status = "done" if already_has_knowledge(conn, place_id) else "pending"
            row = dict(existing.get(qid, {}))
            row.update(
                {
                    "id": qid,
                    "place_id": place_id,
                    "code": code,
                    "name": name,
                    "normalized_query_name": normalize_query_name(name, level),
                    "full_name": full_name,
                    "level": level,
                    "province": province,
                    "city": city,
                    "county": county,
                    "town": town,
                    "collection_phase": phase,
                    "priority": "40" if phase == "admin_street_pilot" else "60",
                    "status": row.get("status") if row.get("status") not in {"", None} else status,
                    "source_strategy": "mca_geonames_fast;official_first",
                    "risk_flag": infer_risk_flag(name, level),
                    "attempt_count": row.get("attempt_count", "0"),
                    "last_attempt_at": row.get("last_attempt_at", ""),
                    "error": row.get("error", ""),
                    "created_at": row.get("created_at", now),
                    "updated_at": now,
                }
            )
            if status == "done" and row.get("status") != "done":
                row["status"] = "done"
                row["error"] = "already_has_knowledge"
            queue_rows[qid] = row

    queue = sorted(queue_rows.values(), key=lambda row: (int(row["priority"]), row["code"]))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(queue)
    return queue


def main() -> None:
    parser = argparse.ArgumentParser(description="Build next-stage origin queues for town/village collection.")
    parser.add_argument("--phase", default="admin_street_pilot", choices=["admin_street_pilot", "town_fast", "village_seed"])
    parser.add_argument("--output", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    queue = build_queue(args.phase, args.output, limit=args.limit, overwrite=args.overwrite)
    print(f"Wrote {len(queue)} queue rows to {args.output}")


if __name__ == "__main__":
    main()
