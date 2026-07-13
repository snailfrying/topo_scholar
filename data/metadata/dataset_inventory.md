# 数据集库存

生成时间：2026-07-10 15:24:44 +08:00

## 已下载数据集

### 1. modood/Administrative-divisions-of-China

- 本地路径：`data/raw/administrative-divisions-of-china`
- 上游地址：https://github.com/modood/Administrative-divisions-of-China
- 当前提交：`c49d495b40ac73eb1a66f6eeae5f8fd10696f035`
- 许可证：`WTFPL`
- 数据版本：2023 年统计用区划代码和城乡划分代码，截止 2023-06-30，发布时间 2023-09-11
- 覆盖层级：省、市、县、乡镇/街道、村/社区五级
- 当前用途：作为第一版 `places.csv` 和 `admin_edges.csv` 的基础底表

### 2. xiangyuecn/AreaCity-JsSpider-StatsGov

- 本地路径：`data/raw/AreaCity-JsSpider-StatsGov`
- 上游地址：https://github.com/xiangyuecn/AreaCity-JsSpider-StatsGov
- 当前提交：`c6c6e35bea3066d674efe2cded189dc57a86e7d8`
- 许可证：`MIT`
- README 标注版本：2025.251231.260403，更新于 2026-04-03
- 覆盖层级：省、市、区县、乡镇/街道四级，带拼音、外部标准名称/代码，部分数据带坐标和边界工具
- 当前用途：作为四级行政区划、拼音、坐标/边界能力的补充来源；暂不与五级底表强行合并

## 已生成标准化数据

- `data/processed/places.csv`：五级地名基础表
- `data/processed/admin_edges.csv`：行政父子关系表
- `data/processed/topo_scholar.sqlite`：带索引的本地查询数据库
- SQLite `place_aliases` 表：村委会/居委会/社区等后缀归一别名索引，当前约 2981225 条
- `data/metadata/source_catalog.csv`：首批原始文件哈希和来源清单
- `data/metadata/raw_dataset_catalog.csv`：已下载原始数据集文件哈希清单
- `data/metadata/build_summary.csv`：本次构建统计

## 当前统计

```csv
level,count
province,31
city,342
county,2978
town,41352
village,620573
all,665276
```

## 使用注意

- `modood` 数据适合作为 MVP 启动底表，但上游已说明不再更新，后续需要用国家地名信息库或其他官方来源持续核验。
- `AreaCity` 是较新的四级数据，适合补充拼音、坐标和边界，但村级仍需使用其他来源。
- 地名由来、含义、历史沿革不在当前基础底表中，后续通过国家地名信息库和搜索能力按需补齐。
