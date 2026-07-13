import json
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from topo_scholar.bootstrap import ensure_database


DB_PATH = ROOT / "data" / "processed" / "topo_scholar.sqlite"
OUT_PATH = ROOT / "data" / "metadata" / "quality_report.json"


def rows(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict]:
    return [dict(row) for row in conn.execute(sql, params)]


def scalar(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> int:
    return conn.execute(sql, params).fetchone()[0]


def main() -> None:
    ensure_database(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    counts = {
        "places": scalar(conn, "select count(*) from places"),
        "admin_edges": scalar(conn, "select count(*) from admin_edges"),
        "place_aliases": scalar(conn, "select count(*) from place_aliases"),
        "place_knowledge": scalar(conn, "select count(*) from place_knowledge"),
    }
    try:
        counts["collection_queue"] = scalar(conn, "select count(*) from collection_queue")
    except sqlite3.OperationalError:
        counts["collection_queue"] = 0

    report = {
        "database": str(DB_PATH.relative_to(ROOT)).replace("\\", "/"),
        "counts": counts,
        "places_by_level": rows(
            conn,
            "select level, count(*) as count from places group by level order by level",
        ),
        "integrity": {
            "empty_names": scalar(conn, "select count(*) from places where name is null or trim(name) = ''"),
            "duplicate_ids": scalar(
                conn,
                "select count(*) from (select id from places group by id having count(*) > 1)",
            ),
            "duplicate_codes": scalar(
                conn,
                "select count(*) from (select code from places group by code having count(*) > 1)",
            ),
            "edges_with_missing_child": scalar(
                conn,
                "select count(*) from admin_edges e left join places p on p.id = e.child_id where p.id is null",
            ),
            "edges_with_missing_parent": scalar(
                conn,
                "select count(*) from admin_edges e left join places p on p.id = e.parent_id where p.id is null",
            ),
            "non_province_without_parent": scalar(
                conn,
                "select count(*) from places where level != 'province' and (parent_id is null or parent_id = '')",
            ),
            "province_with_parent": scalar(
                conn,
                "select count(*) from places where level = 'province' and parent_id != ''",
            ),
            "alias_orphans": scalar(
                conn,
                "select count(*) from place_aliases a left join places p on p.id = a.place_id where p.id is null",
            ),
            "alias_duplicate_pairs": scalar(
                conn,
                "select count(*) from (select alias, place_id from place_aliases group by alias, place_id having count(*) > 1)",
            ),
            "knowledge_unlinked": scalar(
                conn,
                "select count(*) from place_knowledge where place_id is null or place_id = ''",
            ),
            "knowledge_link_missing": scalar(
                conn,
                "select count(*) from place_knowledge k left join places p on p.id = k.place_id "
                "where k.place_id != '' and p.id is null",
            ),
        },
        "top_same_names": rows(
            conn,
            "select name, count(*) as count from places group by name having count(*) > 1 order by count desc limit 10",
        ),
        "samples": {
            "wuhan": rows(
                conn,
                "select code, name, full_name, level from places where name = ? limit 5",
                ("\u6b66\u6c49\u5e02",),
            ),
            "nangao_alias": rows(
                conn,
                """
                select p.code, p.name, p.full_name, p.level, a.alias
                from place_aliases a
                join places p on p.id = a.place_id
                where a.alias = ? and p.province = ? and p.city = ? and p.county = ?
                limit 5
                """,
                ("\u5357\u9ad8\u6751", "\u5c71\u4e1c\u7701", "\u4e1c\u8425\u5e02", "\u5e7f\u9976\u53bf"),
            ),
            "nangao_knowledge": rows(
                conn,
                """
                select k.standard_name, k.origin, p.code as local_code, p.full_name as local_full_name
                from place_knowledge k
                left join places p on p.id = k.place_id
                where k.standard_name = ? and k.province = ? and k.city = ? and k.county = ?
                limit 5
                """,
                ("\u5357\u9ad8\u6751", "\u5c71\u4e1c\u7701", "\u4e1c\u8425\u5e02", "\u5e7f\u9976\u53bf"),
            ),
        },
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
