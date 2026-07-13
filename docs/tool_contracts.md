# Agent 工具接口契约

## 1. 通用返回格式

所有本地工具统一返回 JSON：

```json
{
  "ok": true,
  "data": {},
  "source": "local:places",
  "warnings": []
}
```

- `ok`：工具调用是否成功。
- `data`：结构化结果。
- `source`：数据来源，例如 `local:places`、`local:place_knowledge`、`中国·国家地名信息库`。
- `warnings`：同名、缺失、截断、未补齐等提示。

## 2. 当前 CLI 工具

### 2.1 精确消歧

```powershell
python topo_scholar_cli.py resolve 武汉市 --province 湖北省 --city 武汉市 --limit 1
```

用途：查标准地名候选，解决同名歧义。

### 2.2 代码查询

```powershell
python topo_scholar_cli.py code 4201
```

用途：按行政/统计代码返回单个地名。

### 2.3 别名消歧

```powershell
python topo_scholar_cli.py alias 南高村 --province 山东省 --city 东营市 --county 广饶县 --level village
python topo_scholar_cli.py search-alias 南高 --province 山东省 --city 东营市 --county 广饶县 --level village
```

用途：处理 `村委会`/`村民委员会`/`社区居委会`/`社区居民委员会` 等后缀差异。例如 `南高村` 可以命中基础库中的 `南高村委会`。

### 2.4 下级行政单位

```powershell
python topo_scholar_cli.py children 4201 --limit 20
```

用途：返回某个代码对应地名的下级行政单位。

### 2.5 同名分布

```powershell
python topo_scholar_cli.py same-name 南高村 --limit 100
```

用途：返回全国同名候选、按层级统计、按省份统计。

### 2.6 本地由来查询

```powershell
python topo_scholar_cli.py origin 武汉市 --province 湖北省 --city 武汉市 --limit 1
```

用途：查询已缓存的地名由来、含义、历史沿革。

### 2.7 主题知识搜索

```powershell
python topo_scholar_cli.py search-knowledge 洪洞 --limit 10
```

用途：搜索由来/含义/沿革中包含某关键词的地名。

### 2.8 按需补齐由来

```powershell
python topo_scholar_cli.py fetch-origin 武汉市 --province 湖北省 --city 武汉市 --place-type 地级行政区 --limit 1
```

用途：从中国·国家地名信息库拉取详情，写入缓存、CSV 和 SQLite。

## 3. Agent 使用策略

1. 用户只给地名时，先调用 `same-name` 或 `resolve`，不要直接回答。
2. 用户给出村/社区简称时，优先调用 `alias`，处理后缀差异。
3. 用户给出省市县路径时，调用 `resolve` 或 `alias` 精确定位。
4. 定位后调用 `origin` 查询本地由来。
5. 本地没有由来时，再调用 `fetch-origin` 补齐。
6. 主题研究类问题先调用 `search-knowledge`，结果不足时再联网搜索或批量补齐。
