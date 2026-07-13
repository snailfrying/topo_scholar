import argparse
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "processed" / "topo_scholar.sqlite"


def main() -> None:
    parser = argparse.ArgumentParser(description="Query local TopoScholar origin knowledge.")
    parser.add_argument("name", help="Place name to search")
    parser.add_argument("--province", default="")
    parser.add_argument("--city", default="")
    parser.add_argument("--county", default="")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    clauses = ["standard_name = ?"]
    params: list[object] = [args.name]
    if args.province:
        clauses.append("province = ?")
        params.append(args.province)
    if args.city:
        clauses.append("city = ?")
        params.append(args.city)
    if args.county:
        clauses.append("county = ?")
        params.append(args.county)
    params.append(args.limit)

    sql = f"""
        SELECT standard_name, province, city, county, place_type, origin, meaning, history, source, confidence
        FROM place_knowledge
        WHERE {" AND ".join(clauses)}
        ORDER BY confidence, standard_name
        LIMIT ?
    """
    with sqlite3.connect(DB_PATH) as conn:
        try:
            rows = list(conn.execute(sql, params))
        except sqlite3.OperationalError:
            rows = []

    if not rows:
        print("No local origin knowledge found.")
        return

    for row in rows:
        standard_name, province, city, county, place_type, origin, meaning, history, source, confidence = row
        path = "/".join(part for part in [province, city, county, standard_name] if part)
        print(f"{path} [{place_type}] confidence={confidence} source={source}")
        if origin:
            print(f"由来：{origin}")
        if meaning:
            print(f"含义：{meaning}")
        if history:
            print(f"沿革：{history[:240]}{'...' if len(history) > 240 else ''}")
        print()


if __name__ == "__main__":
    main()
