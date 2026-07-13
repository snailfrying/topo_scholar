import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "administrative-divisions-of-china" / "dist"
PROCESSED_DIR = ROOT / "data" / "processed"
METADATA_DIR = ROOT / "data" / "metadata"
SOURCE = "modood/Administrative-divisions-of-China"
SOURCE_VERSION = "2023-statistical-division"


def stable_id(*parts: str) -> str:
    key = "|".join(parts)
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(name: str) -> list[dict[str, str]]:
    with (RAW_DIR / name).open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    fetched_at = datetime.now(timezone.utc).isoformat()

    provinces = read_csv("provinces.csv")
    cities = read_csv("cities.csv")
    areas = read_csv("areas.csv")
    streets = read_csv("streets.csv")
    villages = read_csv("villages.csv")

    province_by_code = {r["code"]: r for r in provinces}
    city_by_code = {r["code"]: r for r in cities}
    area_by_code = {r["code"]: r for r in areas}
    street_by_code = {r["code"]: r for r in streets}

    rows: list[dict[str, str]] = []
    edges: list[dict[str, str]] = []

    def add_place(
        *,
        code: str,
        name: str,
        level: str,
        type_name: str,
        parent_code: str,
        province: str = "",
        city: str = "",
        county: str = "",
        town: str = "",
        full_name: str = "",
    ) -> str:
        place_id = stable_id(SOURCE, code, level, name)
        parent_id = ""
        if parent_code:
            parent_level = {
                "city": "province",
                "county": "city",
                "town": "county",
                "village": "town",
            }.get(level, "")
            parent_name = {
                "province": province,
                "city": province,
                "county": city,
                "town": county,
                "village": town,
            }.get(level, "")
            parent_id = stable_id(SOURCE, parent_code, parent_level, parent_name)
            edges.append(
                {
                    "parent_id": parent_id,
                    "child_id": place_id,
                    "parent_code": parent_code,
                    "child_code": code,
                    "relation": "contains",
                    "source": SOURCE,
                }
            )

        rows.append(
            {
                "id": place_id,
                "source_id": code,
                "code": code,
                "name": name,
                "full_name": full_name,
                "level": level,
                "type": type_name,
                "parent_id": parent_id,
                "parent_code": parent_code,
                "province": province,
                "city": city,
                "county": county,
                "town": town,
                "lon": "",
                "lat": "",
                "source": SOURCE,
                "source_version": SOURCE_VERSION,
                "fetched_at": fetched_at,
            }
        )
        return place_id

    for p in provinces:
        add_place(
            code=p["code"],
            name=p["name"],
            level="province",
            type_name="province",
            parent_code="",
            province=p["name"],
            full_name=p["name"],
        )

    for c in cities:
        p = province_by_code[c["provinceCode"]]
        add_place(
            code=c["code"],
            name=c["name"],
            level="city",
            type_name="city",
            parent_code=c["provinceCode"],
            province=p["name"],
            city=c["name"],
            full_name=f'{p["name"]}/{c["name"]}',
        )

    for a in areas:
        p = province_by_code[a["provinceCode"]]
        c = city_by_code[a["cityCode"]]
        add_place(
            code=a["code"],
            name=a["name"],
            level="county",
            type_name="county",
            parent_code=a["cityCode"],
            province=p["name"],
            city=c["name"],
            county=a["name"],
            full_name=f'{p["name"]}/{c["name"]}/{a["name"]}',
        )

    for s in streets:
        p = province_by_code[s["provinceCode"]]
        c = city_by_code[s["cityCode"]]
        a = area_by_code[s["areaCode"]]
        add_place(
            code=s["code"],
            name=s["name"],
            level="town",
            type_name="town_or_street",
            parent_code=s["areaCode"],
            province=p["name"],
            city=c["name"],
            county=a["name"],
            town=s["name"],
            full_name=f'{p["name"]}/{c["name"]}/{a["name"]}/{s["name"]}',
        )

    for v in villages:
        p = province_by_code[v["provinceCode"]]
        c = city_by_code[v["cityCode"]]
        a = area_by_code[v["areaCode"]]
        s = street_by_code[v["streetCode"]]
        add_place(
            code=v["code"],
            name=v["name"],
            level="village",
            type_name="village_or_community",
            parent_code=v["streetCode"],
            province=p["name"],
            city=c["name"],
            county=a["name"],
            town=s["name"],
            full_name=f'{p["name"]}/{c["name"]}/{a["name"]}/{s["name"]}/{v["name"]}',
        )

    place_fields = [
        "id",
        "source_id",
        "code",
        "name",
        "full_name",
        "level",
        "type",
        "parent_id",
        "parent_code",
        "province",
        "city",
        "county",
        "town",
        "lon",
        "lat",
        "source",
        "source_version",
        "fetched_at",
    ]
    edge_fields = ["parent_id", "child_id", "parent_code", "child_code", "relation", "source"]

    write_csv(PROCESSED_DIR / "places.csv", rows, place_fields)
    write_csv(PROCESSED_DIR / "admin_edges.csv", edges, edge_fields)

    catalog_rows = []
    for file_name in [
        "provinces.csv",
        "cities.csv",
        "areas.csv",
        "streets.csv",
        "villages.csv",
        "data.sqlite",
    ]:
        path = RAW_DIR / file_name
        catalog_rows.append(
            {
                "source": SOURCE,
                "source_version": SOURCE_VERSION,
                "file": str(path.relative_to(ROOT)).replace("\\", "/"),
                "bytes": str(path.stat().st_size),
                "sha256": sha256_file(path),
                "license": "WTFPL",
                "url": "https://github.com/modood/Administrative-divisions-of-China",
                "fetched_at": fetched_at,
            }
        )

    write_csv(
        METADATA_DIR / "source_catalog.csv",
        catalog_rows,
        ["source", "source_version", "file", "bytes", "sha256", "license", "url", "fetched_at"],
    )

    summary_rows = [
        {"level": "province", "count": str(len(provinces))},
        {"level": "city", "count": str(len(cities))},
        {"level": "county", "count": str(len(areas))},
        {"level": "town", "count": str(len(streets))},
        {"level": "village", "count": str(len(villages))},
        {"level": "all", "count": str(len(rows))},
    ]
    write_csv(METADATA_DIR / "build_summary.csv", summary_rows, ["level", "count"])

    print(f"Wrote {len(rows)} places to {PROCESSED_DIR / 'places.csv'}")
    print(f"Wrote {len(edges)} edges to {PROCESSED_DIR / 'admin_edges.csv'}")


if __name__ == "__main__":
    main()
