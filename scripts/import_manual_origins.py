import argparse
import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT_CSV = ROOT / "data" / "metadata" / "manual_origin_records.csv"
QUEUE_CSV = ROOT / "data" / "processed" / "collection_queue.csv"
KNOWLEDGE_CSV = ROOT / "data" / "processed" / "place_knowledge.csv"
REVIEW_CSV = ROOT / "data" / "metadata" / "origin_failed_review.csv"


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


MANUAL_FIELDS = [
    "code",
    "name",
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
    "collected_at",
    "review_note",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_queue_index(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row["code"]: row for row in rows if row.get("code")}


def knowledge_row(manual: dict[str, str], queue_row: dict[str, str] | None, now: str) -> dict[str, str]:
    raw_text = json.dumps(manual, ensure_ascii=False, sort_keys=True)
    code = manual["code"]
    name = manual["name"]
    row_id = sha1_text(f"manual_origin|{code}|{name}|{manual.get('evidence_url', '')}")
    return {
        "id": row_id,
        "place_id": (queue_row or {}).get("place_id", ""),
        "source_place_id": f"manual:{code}",
        "standard_name": name,
        "province": manual.get("province") or (queue_row or {}).get("province", ""),
        "city": manual.get("city") or (queue_row or {}).get("city", ""),
        "county": manual.get("county") or (queue_row or {}).get("county", ""),
        "place_type": manual.get("place_type") or "县级行政区",
        "origin": manual.get("origin", ""),
        "meaning": manual.get("meaning", ""),
        "history": manual.get("history", ""),
        "old_names": manual.get("old_names", ""),
        "evidence_url": manual.get("evidence_url", ""),
        "evidence_title": manual.get("evidence_title", ""),
        "evidence_quote": manual.get("evidence_quote", "")[:180],
        "confidence": manual.get("confidence") or "medium",
        "source": manual.get("source") or "manual verified source",
        "source_type": manual.get("source_type") or "local_government",
        "raw_hash": sha256_text(raw_text),
        "fetched_at": manual.get("collected_at") or now,
        "updated_at": now,
    }


def upsert_knowledge(rows: list[dict[str, str]]) -> None:
    incoming_ids = {row["id"] for row in rows}
    incoming_source_ids = {row["source_place_id"] for row in rows if row.get("source_place_id")}
    existing = [
        row
        for row in read_csv(KNOWLEDGE_CSV)
        if row.get("id") not in incoming_ids and row.get("source_place_id") not in incoming_source_ids
    ]
    write_csv(KNOWLEDGE_CSV, existing + rows, KNOWLEDGE_FIELDS)


def update_queue(manual_rows: list[dict[str, str]], queue_rows: list[dict[str, str]], now: str) -> None:
    imported_codes = {row["code"] for row in manual_rows}
    for row in queue_rows:
        if row.get("code") not in imported_codes:
            continue
        row["status"] = "done"
        row["source_strategy"] = "manual_review;local_government"
        row["last_attempt_at"] = now
        row["error"] = ""
        row["updated_at"] = now
    write_csv(QUEUE_CSV, queue_rows, list(queue_rows[0].keys()))


def update_failed_review(manual_rows: list[dict[str, str]], now: str) -> None:
    if not REVIEW_CSV.exists():
        return
    review_rows = read_csv(REVIEW_CSV)
    if not review_rows:
        return

    manual_by_code = {row["code"]: row for row in manual_rows}
    fields = list(review_rows[0].keys())
    for field in ["resolution_status", "resolved_at", "resolution_source_url", "resolution_note"]:
        if field not in fields:
            fields.append(field)

    for row in review_rows:
        manual = manual_by_code.get(row.get("code", ""))
        if not manual:
            if not row.get("resolution_status"):
                row["resolution_status"] = "unresolved_needs_review"
            continue
        row["resolution_status"] = "manual_source_imported"
        row["resolved_at"] = now
        row["resolution_source_url"] = manual.get("evidence_url", "")
        row["resolution_note"] = "Imported into place_knowledge.csv from manually verified source."
    write_csv(REVIEW_CSV, review_rows, fields)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import manually verified origin records into place_knowledge.csv.")
    parser.add_argument("--input", type=Path, default=INPUT_CSV)
    parser.add_argument("--no-rebuild", action="store_true")
    args = parser.parse_args()

    manual_rows = read_csv(args.input)
    queue_rows = read_csv(QUEUE_CSV)
    queue_by_code = load_queue_index(queue_rows)
    now = utc_now()

    missing = [row["code"] for row in manual_rows if row["code"] not in queue_by_code]
    if missing:
        raise SystemExit(f"Manual records not found in collection_queue.csv: {', '.join(missing)}")

    knowledge_rows = [knowledge_row(row, queue_by_code[row["code"]], now) for row in manual_rows]
    upsert_knowledge(knowledge_rows)
    update_queue(manual_rows, queue_rows, now)
    update_failed_review(manual_rows, now)

    if not args.no_rebuild:
        subprocess.check_call([sys.executable, str(ROOT / "scripts" / "build_sqlite.py")], cwd=str(ROOT))
    print(f"Imported {len(knowledge_rows)} manual origin records")


if __name__ == "__main__":
    main()
