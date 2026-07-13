# 数据源清单

| 优先级 | 数据源 | 地址 | 用途 | 备注 |
|---|---|---|---|---|
| P0 | 中国·国家地名信息库 | https://dmfw.mca.gov.cn/ | 标准地名、由来、含义、历史沿革、坐标 | 官方核心来源，建议按需查询和缓存 |
| P0 | 国家统计局统计用区划代码 | https://www.stats.gov.cn/sj/tjbz/tjyqhdmhcxhfdm/ | 村/居委会级基础底表 | 官方统计用途，公开页面更新到 2023 版 |
| P0 | 民政部行政区划代码栏目 | https://www.mca.gov.cn/n156/n186/index.html | 行政区划权威信息入口 | 2026 起提示转国家地名信息库查询 |
| P1 | modood 行政区划数据 | https://github.com/modood/Administrative-divisions-of-China | 五级行政区划 JSON/CSV/SQLite | 适合 MVP，更新至 2023 后停止维护 |
| P1 | AreaCity 数据 | https://github.com/xiangyuecn/AreaCity-JsSpider-StatsGov | 四级行政区划、拼音、坐标、边界 | 可补空间信息和拼音 |
| P2 | Geofabrik OSM China | https://download.geofabrik.de/asia/china.html | 道路街巷、POI、线面几何 | 遵守 ODbL，和行政/地名库分层使用 |
| P2 | 地方政府/地方志/地名志 | 分散网页/PDF/图书 | 补充地名由来和历史沿革 | 需要证据抽取和版权控制 |

## 首批落地数据

第一批先拉取 `modood/Administrative-divisions-of-China` 作为五级行政区划基础底表，并保留原始文件到 `data/raw/`。

后续再按需接入国家地名信息库详情，逐步补齐 `place_knowledge`。
