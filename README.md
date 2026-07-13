# 华夏地名谱 TopoScholar

[English](README_EN.md) · 中文

面向 Agent 的中国地名知识库、地名由来采集器与 MCP/RAG 数据底座。

华夏地名谱的目标不是只做一张行政区划表，而是构建一个可查询、可消歧、可溯源、可持续补全的中国地名知识系统：先打牢省、市、县、乡镇/街道、村/社区五级基础数据，再逐步收集每个地名的由来、含义、历史沿革、旧称和证据来源。

## 项目亮点

- **五级基础地名库**：覆盖省、市、县、乡镇/街道、村/社区，当前基础表约 66.5 万条。
- **别名与消歧**：支持 `南高村` 命中 `南高村委会`，处理村委会、居委会、社区居民委员会等常见后缀差异。
- **地名由来补齐**：可按需从中国·国家地名信息库拉取地名由来、含义、历史沿革，并缓存到本地知识表。
- **Agent 友好接口**：提供 JSON CLI 和 MCP Server 骨架，方便 Agent 调用查询、消歧、下钻和补齐工具。
- **可复现数据构建**：仓库提交必要原始 CSV 和构建脚本，大型 SQLite/标准化 CSV 本地自动生成。
- **质量校验**：内置完整性校验脚本，检查空值、重复代码、孤儿行政边、知识断链等问题。

## 当前数据规模

最近一次校验结果见 `data/metadata/quality_report.json` 和 `docs/quality_assessment.md`。

| 数据表 | 数量 |
|---|---:|
| `places` | 665,276 |
| `admin_edges` | 665,245 |
| `place_aliases` | 2,981,225 |
| `place_knowledge` | 53 |
| `collection_queue` | 3,342 |

按层级统计：

| 层级 | 数量 |
|---|---:|
| 省级 | 31 |
| 地级 | 342 |
| 县级 | 2,978 |
| 乡镇/街道级 | 41,352 |
| 村/社区级 | 620,573 |

> 说明：基础底表主要来自 2023 年统计用区划数据，适合启动 Agent 地名底座；后续会继续接入国家地名信息库、民政口径、道路街巷和地方志资料。

## 快速开始

### 1. 克隆项目

```powershell
git clone https://github.com/snailfrying/topo_scholar.git
cd topo_scholar
```

### 2. 直接查询

首次运行 CLI 时，如果 `data/processed/topo_scholar.sqlite` 不存在，项目会自动从仓库内原始 CSV 构建本地数据库。

```powershell
python topo_scholar_cli.py resolve 武汉市 --province 湖北省 --city 武汉市 --limit 1
```

### 3. 常用命令

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

# 主题搜索已缓存的由来知识
python topo_scholar_cli.py search-knowledge 洪洞 --limit 10
```

## 地名由来采集队列

项目内置了一个保守的地名由来采集流水线：先生成队列，再限速批量补齐，避免对来源站点造成压力。

```powershell
# 构建省/市/县三级采集队列
python scripts\build_collection_queue.py --levels province,city,county

# 预览将要采集的前 3 条，不访问网络
python scripts\batch_fetch_origins.py --max-items 3 --dry-run

# 实际采集 1 条省级地名由来
python scripts\batch_fetch_origins.py --max-items 1 --levels province --sleep 1
```

采集结果会写入 `data/processed/place_knowledge.csv`，并在重建 SQLite 时同步生成全文检索表 `place_knowledge_fts`。

## 手动构建与校验

如果你想显式构建本地数据库：

```powershell
python scripts\build_collection_queue.py --levels province,city,county
python scripts\build_places.py
python scripts\build_sqlite.py
python scripts\validate_data.py
```

构建后会生成：

- `data/processed/places.csv`
- `data/processed/admin_edges.csv`
- `data/processed/topo_scholar.sqlite`

这些文件体积较大，不提交到普通 Git；详见 `docs/release_data_policy.md`。

## MCP Server

MCP SDK 是可选依赖。安装后可以启动 MCP Server：

```powershell
pip install -r requirements.txt
python -m topo_scholar.mcp_server
```

当前 MCP 工具规划包括：

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

## 数据目录

```text
data/
  raw/          # 必要原始 CSV 数据，提交到仓库
  processed/    # 本地生成数据；提交小型 place_knowledge.csv、collection_queue.csv 和 .gitkeep
  cache/        # API 响应缓存，不提交
  metadata/     # 数据源、哈希、质量报告
scripts/        # 数据构建、采集和校验脚本
topo_scholar/   # Python 查询库与 MCP Server
docs/           # 需求、数据方案、质量评估和发布策略
```

## 数据来源

当前已接入或规划接入的数据源：

- `modood/Administrative-divisions-of-China`：五级行政区划基础 CSV。
- `xiangyuecn/AreaCity-JsSpider-StatsGov`：四级行政区划补充数据。
- 中国·国家地名信息库：地名由来、含义、历史沿革的按需补齐来源。
- 地方政府网站、地方志、地名志：后续补充地名文化和历史资料。
- OpenStreetMap/Geofabrik：后续道路街巷和空间数据候选来源。

具体来源、许可和用途见 `docs/dataset_sources.md`。

## 当前限制

- 五级基础底表主要是 2023 年统计口径，不等于最新民政/地名库口径。
- 当前“街道”主要指行政街道办事处，不是道路街巷。
- 港澳台未纳入当前五级主表。
- `place_knowledge` 已补齐 31 个省级行政区、20 个地级行政区样本，以及武汉市、南高村样例；地名由来知识库仍处于持续采集阶段，批量脚本默认限量、限速执行。
- 国家地名信息库适合按需查询和缓存，不建议高频暴力抓取或无授权再分发。

## 路线图

- [ ] 批量补齐省、市、县三级地名由来。
- [x] 增加 SQLite FTS5 起步能力，支持已缓存由来知识的全文检索。
- [ ] 扩展 BM25/向量检索，支持“因水得名”“洪洞移民”等主题研究。
- [ ] 建立地名命名类型标签：姓氏、方位、水文、地形、迁徙、屯垦、历史人物等。
- [ ] 区分行政街道和道路街巷，接入道路地名数据。
- [ ] 加入行政区划版本差异表，记录撤销、合并、更名、代码变化。
- [ ] 完善 MCP Server 和 Agent Skill 使用说明。

## 文档

- `docs/requirements.md`：产品需求与能力规划。
- `docs/data_plan.md`：数据建设方案。
- `docs/tool_contracts.md`：CLI/MCP 工具接口契约。
- `docs/quality_assessment.md`：数据质量评估与优化路线。
- `docs/release_data_policy.md`：仓库数据提交策略。

## 许可证与合规

代码和本项目文档的许可证后续会单独声明。第三方数据保留其原始许可证和来源说明；使用、分发或商用前请自行确认对应数据源的许可条款。

对于地名由来资料，本项目强调来源记录、证据留存和置信度标注；没有可靠来源时，Agent 不应编造地名由来。
