# MCP 接入计划

## 1. 第一版 MCP 目标

第一版 MCP 不直接做复杂 RAG，先把本地 SQLite 能力稳定暴露给 Agent：

- 地名消歧：给定名称返回候选地名。
- 行政下钻：给定代码或名称返回下级行政单位。
- 由来查询：给定地名返回本地已有由来；本地没有时提示可触发补齐。
- 补齐触发：调用国家地名信息库按需查询并写入缓存。

## 2. MCP 工具映射

| MCP 工具 | 对应能力 | 当前本地基础 |
|---|---|---|
| `resolve_place_name` | 同名消歧、行政路径查询 | `places` 表 |
| `resolve_place_alias` | 村/社区/居委会等别名消歧 | `place_aliases` 表 |
| `search_aliases` | 按别名关键词检索 | `place_aliases` 表 |
| `get_place_by_code` | 按行政/统计代码查询单个地名 | `places` 表 |
| `get_admin_children` | 查询下级行政单位 | `admin_edges` + `places` 表 |
| `compare_same_name` | 全国同名地名分布和候选列表 | `places` 表 |
| `get_place_origin` | 查询地名由来、含义、沿革 | `place_knowledge` 表 |
| `fetch_place_origin` | 按需调用国家地名信息库补齐 | `scripts/origin_fetcher_mca.py` |
| `search_toponyms` | 地名关键词检索 | `places` 表 |
| `search_knowledge` | 由来/含义/沿革主题检索 | `place_knowledge` 表 |

## 3. 第一版返回规范

每个工具返回 JSON，至少包含：

- `ok`：是否成功。
- `data`：结构化结果。
- `source`：数据来源。
- `warnings`：缺失、同名、低置信度、来源限制等提示。

## 4. 由来查询策略

```text
Agent 调用 get_place_origin
  -> 查 place_knowledge
  -> 命中：返回 origin/meaning/history/source/confidence
  -> 未命中：返回 missing，并建议调用 fetch_place_origin
Agent 调用 fetch_place_origin
  -> 查询国家地名信息库
  -> 写入 cache、CSV、SQLite
  -> 再返回标准化知识记录
```

## 5. 下一步实现

- 已建立 `topo_scholar/` Python 包。
- 已把 SQLite 查询封装到 `topo_scholar/db.py`。
- 已加入 JSON CLI：`topo_scholar_cli.py`。
- 已加入 MCP Server 入口：`topo_scholar/mcp_server.py`。
- 给 Codex/Claude/ChatGPT 写 Skill 使用说明。

## 6. 本地 JSON CLI 验证

```powershell
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

## 7. MCP Server 启动

当前环境未预装 MCP SDK，先保留骨架。安装依赖后可启动：

```powershell
pip install -r requirements.txt
python -m topo_scholar.mcp_server
```
