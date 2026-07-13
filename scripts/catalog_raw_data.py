import csv
import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "metadata" / "raw_dataset_catalog.csv"


DATASETS = [
    {
        "source": "modood/Administrative-divisions-of-China",
        "path": ROOT / "data" / "raw" / "administrative-divisions-of-china",
        "license": "WTFPL",
        "url": "https://github.com/modood/Administrative-divisions-of-China",
        "files": [
            "dist/provinces.csv",
            "dist/cities.csv",
            "dist/areas.csv",
            "dist/streets.csv",
            "dist/villages.csv",
            "dist/data.sqlite",
        ],
    },
    {
        "source": "xiangyuecn/AreaCity-JsSpider-StatsGov",
        "path": ROOT / "data" / "raw" / "AreaCity-JsSpider-StatsGov",
        "license": "MIT",
        "url": "https://github.com/xiangyuecn/AreaCity-JsSpider-StatsGov",
        "files": [
            "src/采集到的数据/ok_data_level3.csv",
            "src/采集到的数据/ok_data_level4.csv",
            "LICENSE",
            "README.md",
        ],
    },
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit(path: Path) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return ""


def main() -> None:
    fetched_at = datetime.now(timezone.utc).isoformat()
    rows = []
    for dataset in DATASETS:
        base = dataset["path"]
        commit = git_commit(base)
        for rel in dataset["files"]:
            path = base / rel
            if not path.exists():
                continue
            rows.append(
                {
                    "source": dataset["source"],
                    "commit": commit,
                    "file": str(path.relative_to(ROOT)).replace("\\", "/"),
                    "bytes": str(path.stat().st_size),
                    "sha256": sha256_file(path),
                    "license": dataset["license"],
                    "url": dataset["url"],
                    "cataloged_at": fetched_at,
                }
            )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["source", "commit", "file", "bytes", "sha256", "license", "url", "cataloged_at"],
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} catalog rows to {OUT}")


if __name__ == "__main__":
    main()
