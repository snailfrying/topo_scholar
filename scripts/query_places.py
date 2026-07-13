import argparse
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "processed" / "topo_scholar.sqlite"


def main() -> None:
    parser = argparse.ArgumentParser(description="Query local TopoScholar places.")
    parser.add_argument("name", help="Place name to search")
    parser.add_argument("--level", choices=["province", "city", "county", "town", "village"])
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    where = ["name = ?"]
    params: list[object] = [args.name]
    if args.level:
        where.append("level = ?")
        params.append(args.level)
    params.append(args.limit)

    sql = f"""
        SELECT code, name, level, full_name
        FROM places
        WHERE {" AND ".join(where)}
        ORDER BY level, code
        LIMIT ?
    """
    with sqlite3.connect(DB_PATH) as conn:
        for code, name, level, full_name in conn.execute(sql, params):
            print(f"{code}\t{level}\t{name}\t{full_name}")


if __name__ == "__main__":
    main()
