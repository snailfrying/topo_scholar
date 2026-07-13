# 仓库数据提交策略

## 1. 原则

华夏地名谱需要让其他用户 clone 后可复现、可使用，同时不能把超大生成物直接放进普通 Git。

因此仓库提交：

- 必要原始 CSV 数据。
- 小型已采集知识表。
- 构建脚本、查询工具、MCP 骨架。
- 数据源、校验报告和文档。

仓库不提交：

- 本地 SQLite 生成物。
- 巨大的标准化 CSV 生成物。
- API 响应缓存。
- 上游数据仓库的嵌套 `.git`。
- IDE 配置和 Python 缓存。

## 2. 会提交的数据

### 2.1 五级行政区划基础 CSV

路径：

- `data/raw/administrative-divisions-of-china/dist/provinces.csv`
- `data/raw/administrative-divisions-of-china/dist/cities.csv`
- `data/raw/administrative-divisions-of-china/dist/areas.csv`
- `data/raw/administrative-divisions-of-china/dist/streets.csv`
- `data/raw/administrative-divisions-of-china/dist/villages.csv`

用途：构建 `places`、`admin_edges` 和 `place_aliases`。

### 2.2 四级补充数据

路径：

- `data/raw/AreaCity-JsSpider-StatsGov/src/采集到的数据/ok_data_level3.csv`
- `data/raw/AreaCity-JsSpider-StatsGov/src/采集到的数据/ok_data_level4.csv`

用途：后续补充较新的四级行政区划、拼音和外部标准代码。

### 2.3 小型地名由来知识表

路径：

- `data/processed/place_knowledge.csv`
- `data/processed/collection_queue.csv`
- `data/metadata/mca_candidate_audit.csv`

用途：保存已经采集并标准化的地名由来样例，以及省/市/县三级优先采集队列。

## 3. 不会提交的数据

这些文件体积大或属于本地缓存：

- `data/processed/places.csv`
- `data/processed/admin_edges.csv`
- `data/processed/topo_scholar.sqlite`
- `data/cache/`
- `data/interim/`
- `data/raw/**/.git`

## 4. Clone 后如何使用

直接运行 CLI 即可。如果 SQLite 不存在，程序会自动构建：

```powershell
python topo_scholar_cli.py resolve 武汉市 --province 湖北省 --city 武汉市 --limit 1
```

也可以手动构建：

```powershell
python scripts\build_places.py
python scripts\build_sqlite.py
python scripts\validate_data.py
```

## 5. 为什么不直接提交 SQLite

当前生成的 `topo_scholar.sqlite` 超过 1GB，普通 Git/GitHub 不适合提交。后续如果要提供即下即用的大数据库，可以考虑：

- GitHub Release 附件。
- Git LFS。
- Hugging Face Dataset。
- 对 SQLite 分片压缩后发布。

当前仓库优先保证源码和基础数据可复现。
