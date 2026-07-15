# Data License and Source Notice

TopoScholar separates project-owned code/documentation from third-party data.

## Project-Owned Code and Documentation

The project-owned code, scripts, and documentation are licensed under the MIT License. See `LICENSE`.

## Third-Party and Public Data

Third-party data files, derived datasets, and source excerpts are not relicensed as MIT by this repository. They remain subject to their original source licenses, terms, and attribution requirements.

Currently committed data includes:

- `data/raw/administrative-divisions-of-china/`: sourced from `modood/Administrative-divisions-of-China`; see the bundled `LICENSE`.
- `data/raw/AreaCity-JsSpider-StatsGov/`: sourced from `xiangyuecn/AreaCity-JsSpider-StatsGov`; see the bundled `LICENSE`.
- `data/processed/place_knowledge.csv`: normalized place-name origin records collected from public official pages and a small number of reviewed reference sources. Records keep source URL, title, evidence quote, confidence, and source type.
- `data/processed/collection_queue.csv` and `data/metadata/*.csv|*.json`: project metadata, audit tables, and validation reports used to reproduce and review the dataset.

Public availability does not automatically grant unrestricted redistribution rights. Before commercial redistribution or large-scale republication, users should review the source terms listed in `docs/dataset_sources.md` and the source URL recorded on each knowledge row.

## Submission Boundary

The normal Git repository intentionally does not include:

- API response caches under `data/cache/`.
- Raw scraped HTML pages or raw endpoint JSON.
- Local SQLite/database outputs such as `data/processed/topo_scholar.sqlite`.
- Generated full normalized CSVs such as `places.csv` and `admin_edges.csv`.
- Coordinate, boundary, shapefile, GeoJSON, map tile, or other geospatial geometry outputs.

These files may be rebuilt locally or released separately only after a dedicated license, size, and geospatial compliance review.

## Sensitive Information

Committed data should contain public place names, administrative codes, hierarchy metadata, source links, and short evidence excerpts only. Do not commit credentials, tokens, private notes, personal data, non-public records, raw caches, or restricted geospatial data.
