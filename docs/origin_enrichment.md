# 地名由来持续补齐方案

## 1. 目标

基础地名底表先稳定下来，地名由来、含义、历史沿革采用“按需查询、持续缓存、可回溯修订”的方式逐步补齐。

## 2. 补齐优先级

1. 官方地名详情：优先使用中国·国家地名信息库中的 `place_origin`、`place_meaning`、`place_history`。
2. 地方政府资料：民政局、文旅局、区县政府、乡镇政府公开页面。
3. 地方志/地名志：县志、地名志、村志、文史资料。
4. 开放地图与百科类资料：只作线索，不作为高置信度最终证据。

## 3. 按需补齐流程

```text
用户问题 -> 本地 places 消歧 -> 查 place_knowledge
  -> 命中：返回由来 + 来源
  -> 未命中：查国家地名信息库
      -> 命中：写入缓存和知识表
      -> 未命中：联网搜索地方资料
          -> LLM 抽取候选由来/含义/沿革
          -> 记录证据 URL、标题、摘录、置信度
          -> 等待人工或规则校验
```

## 4. 置信度规则

- `high`：国家地名信息库、民政/政府官网、地方志原文明确说明。
- `medium`：多个可信网页交叉验证，但非一手资料。
- `low`：只有百科、论坛、游记、传说类资料，必须提示“说法之一”。

## 5. Agent 回答约束

- 不允许无来源编造地名由来。
- 同名地名必须先消歧。
- 来源冲突时并列展示不同说法。
- 没有资料时回答“当前基础库已收录该地名，但暂无可靠由来资料”。

## 6. 后续实现模块

- `scripts/origin_fetcher_mca.py`：国家地名信息库按需查询、详情拉取、缓存、入库。
- `origin_searcher.py`：联网搜索地方资料。
- `origin_extractor.py`：从网页/PDF 文本抽取由来、含义、沿革、证据句。
- `origin_reviewer.py`：规则校验和置信度判断。

## 7. 当前已实现命令

### 7.1 拉取并缓存地名由来

```powershell
python scripts\origin_fetcher_mca.py 武汉市 --province 湖北省 --city 武汉市 --place-type 地级行政区 --limit 1
python scripts\origin_fetcher_mca.py 南高村 --province 山东省 --city 东营市 --county 广饶县 --place-type 行政村 --limit 1
```

脚本会同时写入：

- `data/cache/mca_geonames/`：原始查询和详情响应缓存。
- `data/processed/place_knowledge.csv`：标准化地名知识表。
- `data/processed/topo_scholar.sqlite` 的 `place_knowledge` 表。

### 7.2 查询本地地名由来

```powershell
python scripts\query_knowledge.py 武汉市 --province 湖北省 --city 武汉市
```

如果本地没有知识记录，先用 `origin_fetcher_mca.py` 按需补齐，再查询。
