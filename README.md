# 华夏地名谱 TopoScholar

[English](README_EN.md) · 中文

![Data](https://img.shields.io/badge/base_places-665%2C276-2f6f4e)
![Knowledge](https://img.shields.io/badge/origin_records-3%2C526-b36b2c)
![Python](https://img.shields.io/badge/Python-3.10%2B-315c96)
![License](https://img.shields.io/badge/license-MIT-8a5cf6)
![Agent Ready](https://img.shields.io/badge/Agent%20Ready-CLI%20%7C%20MCP-4b5563)

**华夏地名谱**是一个面向 Agent、RAG 和地名研究的中国地名知识底座：它不只保存“有哪些地名”，还要持续回答“这个地名为什么这么叫”。

项目当前已经建立省、市、县、乡镇/街道、村/社区五级基础库，并开始系统化补齐每个地名的由来、含义、历史沿革、旧称和证据来源。目标是形成一个可查询、可消歧、可溯源、可扩展的中文地名知识系统。

## 为什么做这个项目

中国地名包含大量历史、迁徙、山川、水系、方位、姓氏、屯垦、民族语言和行政沿革信息。普通行政区划表只能告诉我们“它在哪”，但很难告诉我们：

- `武汉` 为什么叫武汉，和武昌、汉口、汉阳是什么关系？
- `南高村` 的“南”是相对谁而言？
- 全国有多少个 `和平村`、`团结村`，它们分别在哪些地方？
- 一个地名经历过哪些合并、更名、撤销和重设？
- Agent 在回答地名问题时，如何避免同名误判和编造由来？

TopoScholar 试图把这些问题变成结构化数据、可复现流水线和 Agent 可调用工具。

## 当前进度

最近一次校验结果见 `data/metadata/quality_report.json` 和 `docs/quality_assessment.md`。

| 模块 | 当前规模 |
|---|---:|
| 基础地名 `places` | 665,276 |
| 行政层级边 `admin_edges` | 665,245 |
| 别名索引 `place_aliases` | 2,981,225 |
| 地名由来知识 `place_knowledge` | 3,526 |
| 由来采集队列 `collection_queue` | 3,227 |

| 基础层级 | 数量 |
|---|---:|
| 省级 | 31 |
| 地级 | 342 |
| 县级 | 2,978 |
| 乡镇/街道级 | 41,352 |
| 村/社区级 | 620,573 |

地名由来采集进度：

- 省级行政区：31/31 已补齐。
- 可采集地级行政区：333/333 已补齐。
- 县级及特殊区域：国家地名信息库可采集队列已跑完，已补齐 2,793 条；另从地方政府、民政、地方志及待复核参考来源人工补入 70 条，当前县级/特殊区域 `needs_review` 为 0。
- 手工补充来源质量：高置信 49 条、中置信 21 条；`reference_only` 已清零，后续重点把媒体来源继续替换为官方史志/地方志原文。
- 行政街道试点：已生成 9,112 条独立下一阶段队列，先快速采集 297 条官方来源记录，4 条进入 `needs_review` 慢慢复核。
- 村级样例：保留 `南高村`，用于验证村级别名与由来关联。

## 核心能力

### 1. 五级地名底座

以公开行政区划数据为基础，生成统一的 `places`、`admin_edges` 和 `place_aliases`：

- 省、市、县、乡镇/街道、村/社区五级结构。
- 可按行政代码下钻或回溯上级。
- 可处理大量同名村、同名社区和同名区县。

### 2. 别名与消歧

地名查询不要求用户输入完全标准名：

- `南高村` 可以命中 `南高村委会`。
- `社区`、`居委会`、`村委会` 等常见后缀会进入别名索引。
- 支持通过省、市、县、层级约束缩小同名结果。

### 3. 地名由来知识表

`place_knowledge` 保存结构化地名知识：

- 地名由来 `origin`
- 名称含义 `meaning`
- 历史沿革 `history`
- 旧称 `old_names`
- 来源标题、来源 URL、证据摘要、置信度

当前优先从中国·国家地名信息库按需拉取，并保留候选审计记录，避免错配。

### 4. Agent / MCP 友好

项目提供 JSON CLI，并预留 MCP Server 工具：

- 地名解析
- 别名解析
- 行政下级查询
- 同名地名对比
- 本地地名由来查询
- 地名由来按需补齐
- 已缓存知识全文检索

## 快速开始

### 克隆项目

```powershell
git clone https://github.com/snailfrying/topo_scholar.git
cd topo_scholar
```

### 直接查询

首次运行时，如果 `data/processed/topo_scholar.sqlite` 不存在，项目会自动从仓库内的原始 CSV 和小型知识表构建本地数据库。

```powershell
python topo_scholar_cli.py resolve 武汉市 --province 湖北省 --city 武汉市 --limit 1
```

### 常用命令

```powershell
# 精确消歧
python topo_scholar_cli.py resolve 武汉市 --province 湖北省 --city 武汉市 --limit 1

# 别名消歧：南高村 -> 南高村委会
python topo_scholar_cli.py alias 南高村 --province 山东省 --city 东营市 --county 广饶县 --level village

# 查询下级行政单位
python topo_scholar_cli.py children 4201 --limit 10

# 查询同名地名分布
python topo_scholar_cli.py same-name 和平村委会 --limit 20

# 查询本地已缓存地名由来
python topo_scholar_cli.py origin 南高村 --province 山东省 --city 东营市 --county 广饶县 --limit 1

# 按需补齐地名由来
python topo_scholar_cli.py fetch-origin 武汉市 --province 湖北省 --city 武汉市 --place-type 地级行政区 --limit 1

# 搜索已缓存的由来知识
python topo_scholar_cli.py search-knowledge 洪洞 --limit 10
```

## 地名由来采集

项目内置保守的采集流水线：先生成队列，再限速补齐，再写入知识表和 SQLite。这样可以持续完善数据，也避免对来源站点造成压力。

```powershell
# 构建省/市/县三级采集队列
python scripts\build_collection_queue.py --levels province,city,county

# 预览将要采集的前 3 条，不访问网络
python scripts\batch_fetch_origins.py --max-items 3 --dry-run

# 小批量补齐县级地名由来；建议 workers 保持 2 左右，避免对来源站点造成压力
python scripts\batch_fetch_origins.py --max-items 100 --levels county --sleep 0.6 --max-pages 3 --max-attempts 3 --workers 2

# 导入人工复核的地方政府/民政来源记录
python scripts\import_manual_origins.py

# 为未命中项生成候选来源线索；候选需复核后再入库
python scripts\discover_origin_sources.py --max-rows 20 --max-queries 3 --max-results 5 --sleep 1.0 --flush-each
```

采集结果会写入：

- `data/processed/place_knowledge.csv`
- `data/processed/collection_queue.csv`
- `data/metadata/mca_candidate_audit.csv`
- `data/metadata/origin_failed_review.csv`
- `data/metadata/manual_origin_records.csv`
- `data/metadata/origin_source_candidates.csv`
- `data/processed/topo_scholar.sqlite` 中的 `place_knowledge` 和 `place_knowledge_fts`

## 本地构建与校验

如果你想显式重建数据库：

```powershell
python scripts\build_places.py
python scripts\build_collection_queue.py --levels province,city,county
python scripts\build_sqlite.py
python scripts\validate_data.py
```

构建后会生成：

- `data/processed/places.csv`
- `data/processed/admin_edges.csv`
- `data/processed/topo_scholar.sqlite`

这些文件体积较大，不作为普通 Git 文件提交；仓库提交必要原始数据、小型知识表、采集队列、审计表、脚本和文档，确保 clone 后可以复现构建。详见 `docs/release_data_policy.md`。

## MCP Server

MCP SDK 是可选依赖。安装后可以启动 MCP Server：

```powershell
pip install -r requirements.txt
python -m topo_scholar.mcp_server
```

当前规划/实现的 MCP 工具包括：

| 工具 | 用途 |
|---|---|
| `resolve_place_name_tool` | 标准地名解析 |
| `resolve_place_alias_tool` | 别名解析 |
| `search_toponyms_tool` | 地名搜索 |
| `search_aliases_tool` | 别名搜索 |
| `get_place_by_code_tool` | 按行政代码查询 |
| `get_admin_children_tool` | 查询下级行政单位 |
| `compare_same_name_tool` | 对比同名地名 |
| `get_place_origin_tool` | 查询本地地名由来 |
| `search_knowledge_tool` | 搜索由来知识 |
| `fetch_place_origin_tool` | 按需补齐由来知识 |

## 数据目录

```text
data/
  raw/          # 必要原始 CSV 数据，提交到仓库
  processed/    # 本地生成数据；提交小型 place_knowledge.csv、collection_queue.csv 和 .gitkeep
  cache/        # API 响应缓存，不提交
  metadata/     # 数据源、哈希、质量报告、候选审计
scripts/        # 数据构建、采集和校验脚本
topo_scholar/   # Python 查询库与 MCP Server
docs/           # 需求、数据方案、质量评估和发布策略
```

## 数据来源

当前已接入或规划接入的数据源：

- `modood/Administrative-divisions-of-China`：五级行政区划基础 CSV。
- `xiangyuecn/AreaCity-JsSpider-StatsGov`：四级行政区划补充数据。
- 中国·国家地名信息库：地名由来、含义、历史沿革的按需补齐来源。
- 地方政府网站、地方志、地名志：已用于补齐特殊区域和国家地名信息库未命中的记录，后续继续扩展地名文化和历史资料。
- OpenStreetMap/Geofabrik：后续道路街巷和空间数据候选来源。

具体来源、许可和用途见 `docs/dataset_sources.md`。

## 路线图

- [x] 建立五级基础地名库。
- [x] 建立别名索引和基础消歧能力。
- [x] 建立地名由来采集器、队列和候选审计。
- [x] 补齐省级、可采集地级地名由来。
- [x] 完成标准县级与特殊/功能区 `needs_review` 清零。
- [ ] 继续提升特殊区域记录置信度，并启动乡镇/街道地名由来来源发现。
- [ ] 建立地名命名类型标签：姓氏、方位、水文、地形、迁徙、屯垦、历史人物等。
- [ ] 扩展 BM25/向量检索，支持“因水得名”“洪洞移民”等主题研究。
- [ ] 区分行政街道和道路街巷，接入道路地名数据。
- [ ] 加入行政区划版本差异表，记录撤销、合并、更名、代码变化。
- [ ] 完善 MCP Server 和 Agent Skill 使用说明。

## 当前限制

- 五级基础底表主要是 2023 年统计口径，不等于最新民政/地名库口径。
- 当前“街道”主要指行政街道办事处，不是道路街巷。
- 港澳台未纳入当前五级主表。
- 地名由来知识库仍在持续采集中，批量脚本默认限量、限速执行。
- 国家地名信息库适合按需查询和缓存，不建议高频抓取或无授权再分发。

## 文档

- `docs/requirements.md`：产品需求与能力规划。
- `docs/data_plan.md`：数据建设方案。
- `docs/origin_enrichment.md`：地名由来补齐方案。
- `docs/town_village_collection_plan.md`：乡镇/街道与村/社区下一阶段采集评估。
- `docs/tool_contracts.md`：CLI/MCP 工具接口契约。
- `docs/quality_assessment.md`：数据质量评估与优化路线。
- `docs/release_data_policy.md`：仓库数据提交策略。

## 许可证与合规

本项目代码和项目自有文档采用 MIT License，详见 `LICENSE`。数据文件、第三方来源内容和由其派生的知识记录不自动改用 MIT，仍保留其原始许可证、来源说明和使用边界；详见 `DATA_LICENSE.md` 与 `docs/dataset_sources.md`。使用、再分发或商用前，请自行确认对应数据源的许可条款。

对于地名由来资料，本项目强调来源记录、证据留存和置信度标注；没有可靠来源时，Agent 不应编造地名由来。

仓库默认不提交 API 响应缓存、原始 HTML/JSON、SQLite、本地数据库、坐标边界、Shapefile、GeoJSON、地图瓦片等文件；如需发布空间数据或大数据库，应单独进行许可证、体积和测绘/地理信息合规审查。
