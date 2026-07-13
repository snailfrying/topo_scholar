import sqlite3
from pathlib import Path
from typing import Any

from topo_scholar.bootstrap import ensure_database
from topo_scholar.normalize import normalize_place_name


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT / "data" / "processed" / "topo_scholar.sqlite"


def connect(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    ensure_database(db_path)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def resolve_place_name(
    name: str,
    *,
    province: str = "",
    city: str = "",
    county: str = "",
    level: str = "",
    limit: int = 20,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    clauses = ["name = ?"]
    params: list[Any] = [name]
    if province:
        clauses.append("province = ?")
        params.append(province)
    if city:
        clauses.append("city = ?")
        params.append(city)
    if county:
        clauses.append("county = ?")
        params.append(county)
    if level:
        clauses.append("level = ?")
        params.append(level)
    params.append(limit)

    sql = f"""
        SELECT id, code, name, full_name, level, type, parent_code, province, city, county, town
        FROM places
        WHERE {" AND ".join(clauses)}
        ORDER BY level, code
        LIMIT ?
    """
    with connect(db_path) as conn:
        rows = [row_to_dict(row) for row in conn.execute(sql, params)]

    return {
        "ok": True,
        "data": rows,
        "source": "local:places",
        "warnings": [] if rows else ["未在本地基础地名表中找到精确匹配"],
    }


def resolve_place_alias(
    name: str,
    *,
    province: str = "",
    city: str = "",
    county: str = "",
    level: str = "",
    limit: int = 20,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    clauses = ["a.normalized_alias = ?"]
    params: list[Any] = [normalize_place_name(name)]
    if province:
        clauses.append("p.province = ?")
        params.append(province)
    if city:
        clauses.append("p.city = ?")
        params.append(city)
    if county:
        clauses.append("p.county = ?")
        params.append(county)
    if level:
        clauses.append("p.level = ?")
        params.append(level)
    params.append(limit)

    sql = f"""
        SELECT p.id, p.code, p.name, p.full_name, p.level, p.type, p.parent_code,
               p.province, p.city, p.county, p.town, a.alias
        FROM place_aliases a
        JOIN places p ON p.id = a.place_id
        WHERE {" AND ".join(clauses)}
        ORDER BY p.level, p.code
        LIMIT ?
    """
    with connect(db_path) as conn:
        try:
            rows = [row_to_dict(row) for row in conn.execute(sql, params)]
        except sqlite3.OperationalError:
            rows = []

    return {
        "ok": True,
        "data": rows,
        "source": "local:place_aliases",
        "warnings": [] if rows else ["未在本地别名表中找到匹配"],
    }


def search_places(
    keyword: str,
    *,
    province: str = "",
    city: str = "",
    county: str = "",
    level: str = "",
    limit: int = 20,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    clauses = ["name LIKE ?"]
    params: list[Any] = [f"%{keyword}%"]
    if province:
        clauses.append("province = ?")
        params.append(province)
    if city:
        clauses.append("city = ?")
        params.append(city)
    if county:
        clauses.append("county = ?")
        params.append(county)
    if level:
        clauses.append("level = ?")
        params.append(level)
    params.append(limit)

    sql = f"""
        SELECT id, code, name, full_name, level, type, parent_code, province, city, county, town
        FROM places
        WHERE {" AND ".join(clauses)}
        ORDER BY level, code
        LIMIT ?
    """
    with connect(db_path) as conn:
        rows = [row_to_dict(row) for row in conn.execute(sql, params)]

    return {
        "ok": True,
        "data": rows,
        "source": "local:places",
        "warnings": [] if rows else ["未在本地基础地名表中找到模糊匹配"],
    }


def search_aliases(
    keyword: str,
    *,
    province: str = "",
    city: str = "",
    county: str = "",
    level: str = "",
    limit: int = 20,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    clauses = ["a.alias LIKE ?"]
    params: list[Any] = [f"%{keyword}%"]
    if province:
        clauses.append("p.province = ?")
        params.append(province)
    if city:
        clauses.append("p.city = ?")
        params.append(city)
    if county:
        clauses.append("p.county = ?")
        params.append(county)
    if level:
        clauses.append("p.level = ?")
        params.append(level)
    params.append(limit)

    sql = f"""
        SELECT p.id, p.code, p.name, p.full_name, p.level, p.type, p.parent_code,
               p.province, p.city, p.county, p.town, a.alias
        FROM place_aliases a
        JOIN places p ON p.id = a.place_id
        WHERE {" AND ".join(clauses)}
        ORDER BY p.level, p.code
        LIMIT ?
    """
    with connect(db_path) as conn:
        try:
            rows = [row_to_dict(row) for row in conn.execute(sql, params)]
        except sqlite3.OperationalError:
            rows = []

    return {
        "ok": True,
        "data": rows,
        "source": "local:place_aliases",
        "warnings": [] if rows else ["未在本地别名表中找到模糊匹配"],
    }


def get_place_by_code(code: str, *, db_path: Path | str = DEFAULT_DB_PATH) -> dict[str, Any]:
    sql = """
        SELECT id, code, name, full_name, level, type, parent_code, province, city, county, town
        FROM places
        WHERE code = ?
        LIMIT 1
    """
    with connect(db_path) as conn:
        row = conn.execute(sql, [code]).fetchone()
    data = row_to_dict(row) if row else None
    return {
        "ok": True,
        "data": data,
        "source": "local:places",
        "warnings": [] if data else ["未找到该代码对应的本地地名"],
    }


def get_admin_children(
    code: str,
    *,
    limit: int = 200,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    sql = """
        SELECT id, code, name, full_name, level, type, parent_code, province, city, county, town
        FROM places
        WHERE parent_code = ?
        ORDER BY code
        LIMIT ?
    """
    with connect(db_path) as conn:
        rows = [row_to_dict(row) for row in conn.execute(sql, [code, limit])]

    return {
        "ok": True,
        "data": rows,
        "source": "local:places",
        "warnings": [] if rows else ["未找到下级行政单位；可能已经是叶子节点或代码不存在"],
    }


def get_place_origin(
    name: str,
    *,
    province: str = "",
    city: str = "",
    county: str = "",
    limit: int = 5,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    clauses = ["k.standard_name = ?"]
    params: list[Any] = [name]
    if province:
        clauses.append("k.province = ?")
        params.append(province)
    if city:
        clauses.append("k.city = ?")
        params.append(city)
    if county:
        clauses.append("k.county = ?")
        params.append(county)
    params.append(limit)

    sql = f"""
        SELECT k.id, k.place_id, k.source_place_id, k.standard_name, k.province, k.city, k.county,
               k.place_type, k.origin, k.meaning, k.history, k.old_names, k.evidence_url,
               k.evidence_title, k.evidence_quote, k.confidence, k.source, k.source_type,
               k.fetched_at, k.updated_at,
               p.code AS local_code, p.name AS local_name, p.full_name AS local_full_name,
               p.level AS local_level, p.type AS local_type
        FROM place_knowledge
        AS k
        LEFT JOIN places AS p ON p.id = k.place_id
        WHERE {" AND ".join(clauses)}
        ORDER BY k.confidence, k.updated_at DESC
        LIMIT ?
    """
    with connect(db_path) as conn:
        try:
            rows = [row_to_dict(row) for row in conn.execute(sql, params)]
        except sqlite3.OperationalError:
            rows = []

    warnings = []
    if not rows:
        warnings.append("本地暂无地名由来记录，可调用 fetch_place_origin 或运行 scripts/origin_fetcher_mca.py 补齐")
    return {"ok": True, "data": rows, "source": "local:place_knowledge", "warnings": warnings}


def search_knowledge(
    keyword: str,
    *,
    province: str = "",
    city: str = "",
    county: str = "",
    limit: int = 20,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    clauses = ["(k.origin LIKE ? OR k.meaning LIKE ? OR k.history LIKE ? OR k.standard_name LIKE ?)"]
    like = f"%{keyword}%"
    params: list[Any] = [like, like, like, like]
    if province:
        clauses.append("k.province = ?")
        params.append(province)
    if city:
        clauses.append("k.city = ?")
        params.append(city)
    if county:
        clauses.append("k.county = ?")
        params.append(county)
    params.append(limit)

    sql = f"""
        SELECT k.id, k.place_id, k.source_place_id, k.standard_name, k.province, k.city, k.county,
               k.place_type, k.origin, k.meaning, k.history, k.old_names, k.evidence_url,
               k.evidence_title, k.confidence, k.source, k.source_type, k.updated_at,
               p.code AS local_code, p.name AS local_name, p.full_name AS local_full_name,
               p.level AS local_level, p.type AS local_type
        FROM place_knowledge AS k
        LEFT JOIN places AS p ON p.id = k.place_id
        WHERE {" AND ".join(clauses)}
        ORDER BY k.confidence, k.updated_at DESC
        LIMIT ?
    """
    with connect(db_path) as conn:
        try:
            rows = [row_to_dict(row) for row in conn.execute(sql, params)]
        except sqlite3.OperationalError:
            rows = []

    return {
        "ok": True,
        "data": rows,
        "source": "local:place_knowledge",
        "warnings": [] if rows else ["本地地名知识库暂无匹配内容；可先补齐更多地名由来"],
    }


def compare_same_name(
    name: str,
    *,
    limit: int = 100,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    candidates_sql = """
        SELECT id, code, name, full_name, level, type, parent_code, province, city, county, town
        FROM places
        WHERE name = ?
        ORDER BY level, province, city, county, code
        LIMIT ?
    """
    summary_sql = """
        SELECT level, COUNT(*) AS count
        FROM places
        WHERE name = ?
        GROUP BY level
        ORDER BY level
    """
    province_sql = """
        SELECT province, COUNT(*) AS count
        FROM places
        WHERE name = ?
        GROUP BY province
        ORDER BY count DESC, province
        LIMIT 50
    """
    with connect(db_path) as conn:
        candidates = [row_to_dict(row) for row in conn.execute(candidates_sql, [name, limit])]
        by_level = [row_to_dict(row) for row in conn.execute(summary_sql, [name])]
        by_province = [row_to_dict(row) for row in conn.execute(province_sql, [name])]

    warnings = []
    if len(candidates) >= limit:
        warnings.append(f"候选结果已截断到 {limit} 条，可增加 limit 或限定省市县")
    if not candidates:
        warnings.append("未找到同名地名")
    return {
        "ok": True,
        "data": {
            "name": name,
            "candidates": candidates,
            "summary": {"by_level": by_level, "by_province": by_province},
        },
        "source": "local:places",
        "warnings": warnings,
    }
