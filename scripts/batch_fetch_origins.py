import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_collection_queue import FIELDS, QUEUE_CSV, build_queue
from scripts.origin_fetcher_mca import fetch_and_save
from topo_scholar.bootstrap import ensure_database


DB_PATH = ROOT / "data" / "processed" / "topo_scholar.sqlite"


PLACE_TYPE_BY_LEVEL = {
    "province": "省级行政区",
    "city": "地级行政区",
    "county": "县级行政区",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_queue() -> list[dict[str, str]]:
    if not QUEUE_CSV.exists():
        build_queue(["province", "city", "county"])
    with QUEUE_CSV.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_queue(rows: list[dict[str, str]]) -> None:
    with QUEUE_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def already_has_knowledge(place_id: str) -> bool:
    ensure_database(DB_PATH)
    with sqlite3.connect(DB_PATH) as conn:
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM place_knowledge WHERE place_id = ?",
                [place_id],
            ).fetchone()[0]
        except sqlite3.OperationalError:
            return False
    return count > 0


def fetch_row(row: dict[str, str], sleep_seconds: float, dry_run: bool, max_pages: int) -> tuple[str, str]:
    if already_has_knowledge(row["place_id"]):
        return "done", "already_has_knowledge"
    if dry_run:
        return "pending", "dry_run"

    payload = fetch_and_save(
        row["name"],
        province=row["province"],
        city=row["city"],
        county=row["county"],
        place_type=PLACE_TYPE_BY_LEVEL.get(row["level"], ""),
        limit=1,
        page_size=20,
        max_pages=max_pages,
        sleep_seconds=sleep_seconds,
        strict=True,
    )
    saved = payload.get("data", {}).get("saved", [])
    if saved:
        return "done", ""
    warnings = "; ".join(payload.get("warnings", []))
    return "failed", warnings or "no_saved_record"


def should_process(row: dict[str, str], levels: set[str], max_attempts: int) -> bool:
    if row["level"] not in levels or row["status"] not in {"pending", "failed"}:
        return False
    if row["status"] == "failed" and max_attempts > 0:
        attempts = int(row.get("attempt_count") or "0")
        return attempts < max_attempts
    return True


def update_row_after_fetch(
    row: dict[str, str],
    status: str,
    error: str,
    now: str,
    dry_run: bool,
) -> None:
    row["status"] = status
    row["error"] = error
    row["attempt_count"] = str(int(row.get("attempt_count") or "0") + (0 if dry_run else 1))
    row["last_attempt_at"] = now if not dry_run else row.get("last_attempt_at", "")
    row["updated_at"] = now


def fetch_row_safe(
    row: dict[str, str],
    sleep_seconds: float,
    dry_run: bool,
    max_pages: int,
) -> tuple[dict[str, str], str, str]:
    try:
        status, error = fetch_row(row, sleep_seconds, dry_run, max_pages)
    except Exception as exc:
        status, error = "failed", str(exc)
    return row, status, error


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch fetch place origins from collection_queue.csv.")
    parser.add_argument("--max-items", type=int, default=5, help="Max pending rows to process")
    parser.add_argument("--levels", default="province,city,county", help="Comma-separated levels")
    parser.add_argument("--sleep", type=float, default=1.0, help="Delay after uncached network requests")
    parser.add_argument("--max-pages", type=int, default=3, help="Max MCA search pages to inspect per place")
    parser.add_argument("--max-attempts", type=int, default=3, help="Skip failed rows after this many attempts; use 0 to retry without limit")
    parser.add_argument("--workers", type=int, default=1, help="Concurrent fetch workers; keep low to avoid stressing upstream")
    parser.add_argument("--dry-run", action="store_true", help="Show items without fetching")
    parser.add_argument("--rebuild-queue", action="store_true", help="Rebuild queue before fetching")
    args = parser.parse_args()

    levels = [level.strip() for level in args.levels.split(",") if level.strip()]
    level_set = set(levels)
    if args.rebuild_queue or not QUEUE_CSV.exists():
        build_queue(levels)

    queue = read_queue()
    selected_rows = [row for row in queue if should_process(row, level_set, args.max_attempts)][: args.max_items]
    processed = 0
    now = utc_now()

    if args.workers <= 1 or args.dry_run:
        for row in selected_rows:
            print(f"{row['status']} -> {row['name']} {row['full_name']} level={row['level']}")
            row, status, error = fetch_row_safe(row, args.sleep, args.dry_run, args.max_pages)
            update_row_after_fetch(row, status, error, now, args.dry_run)
            processed += 1
            print(f"  result={status} error={error}")
            if not args.dry_run:
                write_queue(queue)
    else:
        workers = max(1, args.workers)
        print(f"Processing {len(selected_rows)} rows with {workers} workers")
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = []
            for row in selected_rows:
                print(f"{row['status']} -> {row['name']} {row['full_name']} level={row['level']}")
                futures.append(executor.submit(fetch_row_safe, row, args.sleep, False, args.max_pages))

            for future in as_completed(futures):
                row, status, error = future.result()
                update_row_after_fetch(row, status, error, now, False)
                processed += 1
                print(f"  result={status} {row['name']} error={error}")
                write_queue(queue)

    if not args.dry_run:
        # Rebuild SQLite indexes/tables so collection_queue and FTS stay in sync.
        import subprocess

        subprocess.check_call([sys.executable, str(ROOT / "scripts" / "build_sqlite.py")], cwd=str(ROOT))
    print(f"Processed {processed} queue rows")


if __name__ == "__main__":
    main()
