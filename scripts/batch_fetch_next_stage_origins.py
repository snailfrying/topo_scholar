import argparse
import csv
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_next_stage_queue import DEFAULT_QUEUE, FIELDS, build_queue
from scripts.origin_fetcher_mca import fetch_and_save
from topo_scholar.bootstrap import ensure_database


DB_PATH = ROOT / "data" / "processed" / "topo_scholar.sqlite"
QUEUE_WRITE_LOCK = threading.Lock()

PLACE_TYPE_BY_LEVEL = {
    "town": "乡级行政区",
    "village": "行政村",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_queue(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        build_queue("admin_street_pilot", path)
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_queue(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with QUEUE_WRITE_LOCK:
        fd, tmp_name = tempfile.mkstemp(
            prefix=f"{path.stem}.",
            suffix=f".{os.getpid()}.tmp",
            dir=str(path.parent),
            text=True,
        )
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerows(rows)
            last_error: PermissionError | None = None
            for attempt in range(12):
                try:
                    tmp_path.replace(path)
                    last_error = None
                    break
                except PermissionError as exc:
                    last_error = exc
                    time.sleep(0.25 * (attempt + 1))
            if last_error is not None:
                raise last_error
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise


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


def normalized_filters(row: dict[str, str]) -> tuple[str, str, str]:
    province = row.get("province", "")
    city = row.get("city", "")
    county = row.get("county", "")
    if city in {"市辖区", "省直辖县级行政区划", "自治区直辖县级行政区划"}:
        city = ""
    return province, city, county


def fetch_row(row: dict[str, str], sleep_seconds: float, dry_run: bool, max_pages: int) -> tuple[str, str]:
    if already_has_knowledge(row["place_id"]):
        return "done", "already_has_knowledge"
    if row.get("risk_flag") == "nonstandard_area":
        return "needs_review", "nonstandard_area_manual_review"
    if dry_run:
        return "pending", "dry_run"

    province, city, county = normalized_filters(row)
    payload = fetch_and_save(
        row.get("normalized_query_name") or row["name"],
        province=province,
        city=city,
        county=county,
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
    return "needs_review", warnings or "no_saved_record"


def should_process(row: dict[str, str], phases: set[str], max_attempts: int, include_review: bool) -> bool:
    if phases and row.get("collection_phase") not in phases:
        return False
    if row["status"] == "needs_review" and not include_review:
        return False
    if row["status"] not in {"pending", "failed", "needs_review"}:
        return False
    if row["status"] in {"failed", "needs_review"} and max_attempts > 0:
        attempts = int(row.get("attempt_count") or "0")
        return attempts < max_attempts
    return True


def update_row(row: dict[str, str], status: str, error: str, now: str, dry_run: bool) -> None:
    row["status"] = status
    row["error"] = error
    row["attempt_count"] = str(int(row.get("attempt_count") or "0") + (0 if dry_run else 1))
    row["last_attempt_at"] = now if not dry_run else row.get("last_attempt_at", "")
    row["updated_at"] = now


def fetch_row_safe(row: dict[str, str], sleep_seconds: float, dry_run: bool, max_pages: int) -> tuple[dict[str, str], str, str]:
    try:
        status, error = fetch_row(row, sleep_seconds, dry_run, max_pages)
    except Exception as exc:
        status, error = "failed", str(exc)
    return row, status, error


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch fetch next-stage town/village origin records.")
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--phase", default="admin_street_pilot", help="Comma-separated phases; empty means all")
    parser.add_argument("--max-items", type=int, default=20)
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument("--max-pages", type=int, default=2)
    parser.add_argument("--max-attempts", type=int, default=2)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--flush-every", type=int, default=50, help="Write queue progress every N completed rows.")
    parser.add_argument("--include-review", action="store_true", help="Retry rows marked needs_review; default keeps them for manual review later.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--rebuild-queue", action="store_true")
    args = parser.parse_args()

    phases = {phase.strip() for phase in args.phase.split(",") if phase.strip()}
    if args.rebuild_queue or not args.queue.exists():
        build_queue(next(iter(phases or {"admin_street_pilot"})), args.queue)

    queue = read_queue(args.queue)
    selected = [row for row in queue if should_process(row, phases, args.max_attempts, args.include_review)][: args.max_items]
    now = utc_now()
    processed = 0
    flush_every = max(1, args.flush_every)

    if args.workers <= 1 or args.dry_run:
        for row in selected:
            print(f"{row['status']} -> {row['name']} {row['full_name']} phase={row['collection_phase']}")
            row, status, error = fetch_row_safe(row, args.sleep, args.dry_run, args.max_pages)
            update_row(row, status, error, now, args.dry_run)
            processed += 1
            print(f"  result={status} error={error}")
            if not args.dry_run and processed % flush_every == 0:
                write_queue(args.queue, queue)
        if selected and not args.dry_run:
            write_queue(args.queue, queue)
    else:
        workers = max(1, args.workers)
        print(f"Processing {len(selected)} rows with {workers} workers")
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(fetch_row_safe, row, args.sleep, False, args.max_pages) for row in selected]
            for future in as_completed(futures):
                row, status, error = future.result()
                update_row(row, status, error, now, False)
                processed += 1
                print(f"  result={status} {row['name']} error={error}")
                if processed % flush_every == 0:
                    write_queue(args.queue, queue)
        if selected:
            write_queue(args.queue, queue)

    if not args.dry_run:
        subprocess.check_call([sys.executable, str(ROOT / "scripts" / "build_sqlite.py")], cwd=str(ROOT))
    print(f"Processed {processed} queue rows")


if __name__ == "__main__":
    main()
