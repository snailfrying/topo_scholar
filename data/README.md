# 数据目录说明

- `raw/`：原始数据集，保持上游结构，不直接修改。
- `interim/`：清洗中间产物。
- `processed/`：标准化后的可查询数据。
- `cache/`：后续国家地名信息库和搜索补齐的响应缓存。
- `metadata/`：数据来源、许可证、哈希、构建统计。

当前已经生成五级基础地名底表：

- `processed/places.csv`
- `processed/admin_edges.csv`
- `processed/topo_scholar.sqlite`

这些文件是本地生成物，体积较大，不提交到普通 Git。仓库提交的是必要原始 CSV、脚本和小型知识表；首次运行 `topo_scholar_cli.py` 时会自动构建本地 SQLite。

重建命令：

```powershell
python scripts\catalog_raw_data.py
python scripts\build_places.py
python scripts\build_sqlite.py
python scripts\query_places.py 武汉市
python scripts\validate_data.py
```
