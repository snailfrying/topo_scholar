# TopoScholar

English · [中文](README.md)

An Agent-oriented Chinese toponym knowledge base, origin collector, and MCP/RAG data foundation.

TopoScholar is not just another administrative-division table. It aims to build a searchable, disambiguated, source-traceable, and continuously enrichable Chinese place-name knowledge system. The project first establishes a five-level foundation covering provinces, prefecture-level cities, counties, townships/subdistricts, and villages/communities, then gradually enriches each place with name origins, meanings, historical evolution, aliases, and evidence sources.

## Highlights

- **Five-level place-name foundation**: province, city, county, township/subdistrict, and village/community; currently about 665k base records.
- **Alias-aware disambiguation**: maps short names such as `南高村` to local records such as `南高村委会`, handling common suffix variations around villages, neighborhood committees, and communities.
- **Origin enrichment**: fetches name origin, meaning, and history from the China National Geographical Names Database on demand and caches normalized results locally.
- **Agent-friendly interfaces**: provides a JSON CLI and an MCP Server skeleton for place resolution, hierarchy traversal, same-name comparison, and origin enrichment.
- **Reproducible data build**: commits minimal raw CSV data and build scripts; large SQLite and normalized CSV artifacts are generated locally.
- **Quality validation**: includes scripts to check empty names, duplicate codes, orphan edges, broken knowledge links, and other integrity issues.

## Current Data Size

Official origin, meaning, and history records have been collected for all 31 province-level administrative regions, 333 collectable prefecture-level administrative regions, 1,471 county-level administrative regions, and the Nangao Village example. See `data/metadata/quality_report.json` and `docs/quality_assessment.md` for the latest validation report.

| Table | Count |
|---|---:|
| `places` | 665,276 |
| `admin_edges` | 665,245 |
| `place_aliases` | 2,981,225 |
| `place_knowledge` | 1,837 |
| `collection_queue` | 3,227 |

By level:

| Level | Count |
|---|---:|
| Province | 31 |
| City | 342 |
| County | 2,978 |
| Township/Subdistrict | 41,352 |
| Village/Community | 620,573 |

> Note: the current five-level foundation is mainly based on 2023 statistical-division data. It is suitable as an initial Agent data foundation. Future versions will incorporate more authoritative and up-to-date sources such as the China National Geographical Names Database, civil-affairs data, road/street names, and local gazetteers.

## Quick Start

### 1. Clone

```powershell
git clone https://github.com/snailfrying/topo_scholar.git
cd topo_scholar
```

### 2. Query Directly

On first CLI use, if `data/processed/topo_scholar.sqlite` does not exist, the project will automatically build a local database from the raw CSV files committed in the repository.

```powershell
python topo_scholar_cli.py resolve 武汉市 --province 湖北省 --city 武汉市 --limit 1
```

### 3. Common Commands

```powershell
# Exact resolution
python topo_scholar_cli.py resolve 武汉市 --province 湖北省 --city 武汉市 --limit 1

# Alias resolution: 南高村 -> 南高村委会
python topo_scholar_cli.py alias 南高村 --province 山东省 --city 东营市 --county 广饶县 --level village

# Administrative children
python topo_scholar_cli.py children 4201 --limit 10

# Same-name distribution
python topo_scholar_cli.py same-name 和平村委会 --limit 20

# Locally cached origin knowledge
python topo_scholar_cli.py origin 南高村 --province 山东省 --city 东营市 --county 广饶县 --limit 1

# Fetch origin knowledge on demand
python topo_scholar_cli.py fetch-origin 武汉市 --province 湖北省 --city 武汉市 --place-type 地级行政区 --limit 1

# Search cached origin knowledge
python topo_scholar_cli.py search-knowledge 洪洞 --limit 10
```

## Manual Build and Validation

```powershell
python scripts\build_collection_queue.py --levels province,city,county
python scripts\build_places.py
python scripts\build_sqlite.py
python scripts\validate_data.py
```

Generated artifacts:

- `data/processed/places.csv`
- `data/processed/admin_edges.csv`
- `data/processed/topo_scholar.sqlite`

These files are large and are not committed to normal Git. See `docs/release_data_policy.md` for details.

## MCP Server

The MCP SDK is an optional dependency. Install it before running the server:

```powershell
pip install -r requirements.txt
python -m topo_scholar.mcp_server
```

Current/planned MCP tools include:

- `resolve_place_name_tool`
- `resolve_place_alias_tool`
- `search_toponyms_tool`
- `search_aliases_tool`
- `get_place_by_code_tool`
- `get_admin_children_tool`
- `compare_same_name_tool`
- `get_place_origin_tool`
- `search_knowledge_tool`
- `fetch_place_origin_tool`

## Repository Layout

```text
data/
  raw/          # Minimal raw CSV data committed to the repository
  processed/    # Local generated data; small place_knowledge.csv, collection_queue.csv, and .gitkeep are committed
  cache/        # API response cache, ignored by Git
  metadata/     # Source catalog, hashes, and quality reports
scripts/        # Build, collection, and validation scripts
topo_scholar/   # Python query package and MCP Server
docs/           # Requirements, data plan, quality assessment, and release policy
```

## Data Sources

Current or planned data sources include:

- `modood/Administrative-divisions-of-China`: five-level administrative-division CSV files.
- `xiangyuecn/AreaCity-JsSpider-StatsGov`: supplementary four-level administrative-division data.
- China National Geographical Names Database: on-demand source for name origins, meanings, and historical evolution.
- Local government websites, local gazetteers, and toponym gazetteers: future sources for cultural and historical enrichment.
- OpenStreetMap/Geofabrik: future candidates for road/street names and spatial data.

See `docs/dataset_sources.md` for source details, licenses, and usage notes.

## Current Limitations

- The five-level foundation is mainly based on 2023 statistical data and may not reflect the latest civil-affairs/geographical-name authority view.
- `street/subdistrict` currently refers mainly to administrative subdistricts, not road/street names.
- Hong Kong, Macao, and Taiwan are not included in the current five-level main table.
- `place_knowledge` now contains official origin records for all 31 province-level administrative regions, 333 collectable prefecture-level administrative regions, 1,471 county-level administrative regions, and the Nangao Village example; large-scale origin enrichment is still ongoing and batch scripts are intentionally rate-limited.
- The China National Geographical Names Database should be queried and cached responsibly. Avoid high-frequency scraping or unauthorized redistribution.

## Roadmap

- [ ] Batch enrich province, city, and county-level name origins.
- [x] Add initial SQLite FTS5 support for cached origin knowledge.
- [ ] Extend BM25/vector search for topic queries such as water-related names or Hongdong migration.
- [ ] Add naming-type labels: surname, direction, hydrology, terrain, migration, military colony, historical figures, and more.
- [ ] Separate administrative subdistricts from road/street names and ingest road-name data.
- [ ] Add administrative-version diffs for removals, merges, renames, and code changes.
- [ ] Complete MCP Server and Agent Skill documentation.

## Documentation

- `docs/requirements.md`: product requirements and capability planning.
- `docs/data_plan.md`: data construction plan.
- `docs/tool_contracts.md`: CLI/MCP tool contracts.
- `docs/quality_assessment.md`: data quality assessment and optimization roadmap.
- `docs/release_data_policy.md`: repository data release policy.

## License and Compliance

A dedicated license for the project code and documentation will be added later. Third-party data keeps its original license and source attribution. Please review the corresponding data-source license before redistribution or commercial use.

For name-origin knowledge, TopoScholar emphasizes source tracking, evidence retention, and confidence labels. Agents should not fabricate name origins when reliable sources are unavailable.
