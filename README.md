# 华夏地名谱（TopoScholar）

面向 Agent 的中国地名知识库与 MCP/RAG 项目。

目标：先建设全国省、市、县、乡镇/街道、村/社区基础底表，再通过国家地名信息库、地方志、政府网站和联网搜索能力持续补齐地名由来、含义和历史沿革。

## 当前进展

- 已完成需求文档：`docs/requirements.md`
- 已完成数据建设方案：`docs/data_plan.md`
- 已完成数据源清单：`docs/dataset_sources.md`
- 已拉取首批基础数据集到 `data/raw/`
- 可从仓库内原始 CSV 自动生成五级基础地名表、行政父子关系表和本地 SQLite 查询库
- 本地 SQLite 会生成 `place_aliases` 表，支持村委会/居委会/社区等名称归一
- 已实现国家地名信息库按需补齐脚本：`scripts/origin_fetcher_mca.py`
- 已生成地名由来知识表：`data/processed/place_knowledge.csv`
- 已封装本地查询包：`topo_scholar/db.py`
- 已提供 JSON CLI：`topo_scholar_cli.py`
- 已提供 MCP Server 骨架：`topo_scholar/mcp_server.py`

## 快速查询

首次运行 CLI 时，如果 `data/processed/topo_scholar.sqlite` 不存在，会自动执行本地构建。构建产物较大，不提交到 Git。

```powershell
python scripts\query_places.py 武汉市
python scripts\query_places.py 南高乡 --level town
python scripts\query_knowledge.py 武汉市 --province 湖北省 --city 武汉市
python topo_scholar_cli.py resolve 武汉市 --province 湖北省 --city 武汉市 --limit 1
python topo_scholar_cli.py alias 南高村 --province 山东省 --city 东营市 --county 广饶县 --level village
python topo_scholar_cli.py search-alias 南高 --province 山东省 --city 东营市 --county 广饶县 --level village
python topo_scholar_cli.py code 4201
python topo_scholar_cli.py children 4201 --limit 3
python topo_scholar_cli.py same-name 武汉市 --limit 5
python topo_scholar_cli.py origin 武汉市 --province 湖北省 --city 武汉市 --limit 1
python topo_scholar_cli.py search-knowledge 洪洞 --limit 5
python topo_scholar_cli.py fetch-origin 武汉市 --province 湖北省 --city 武汉市 --place-type 地级行政区 --limit 1
```

## 按需补齐地名由来

```powershell
python scripts\origin_fetcher_mca.py 武汉市 --province 湖北省 --city 武汉市 --place-type 地级行政区 --limit 1
python scripts\origin_fetcher_mca.py 南高村 --province 山东省 --city 东营市 --county 广饶县 --place-type 行政村 --limit 1
```

## 重建数据

```powershell
python scripts\catalog_raw_data.py
python scripts\build_places.py
python scripts\build_sqlite.py
python scripts\validate_data.py
```

## 启动 MCP Server

当前 MCP SDK 是可选依赖：

```powershell
pip install -r requirements.txt
python -m topo_scholar.mcp_server
```
