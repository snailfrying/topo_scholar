from scripts.origin_fetcher_mca import fetch_and_save
from topo_scholar.db import (
    compare_same_name,
    get_admin_children,
    get_place_by_code,
    get_place_origin,
    resolve_place_alias,
    resolve_place_name,
    search_aliases,
    search_knowledge,
    search_places,
)


try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "MCP SDK is not installed. Install it first, for example: pip install mcp"
    ) from exc


mcp = FastMCP("topo-scholar-mcp")


@mcp.tool()
def resolve_place_name_tool(
    name: str,
    province: str = "",
    city: str = "",
    county: str = "",
    level: str = "",
    limit: int = 20,
) -> dict:
    """Resolve an exact Chinese place name and return local candidates."""
    return resolve_place_name(
        name,
        province=province,
        city=city,
        county=county,
        level=level,
        limit=limit,
    )


@mcp.tool()
def search_toponyms_tool(
    keyword: str,
    province: str = "",
    city: str = "",
    county: str = "",
    level: str = "",
    limit: int = 20,
) -> dict:
    """Search local place names by keyword."""
    return search_places(
        keyword,
        province=province,
        city=city,
        county=county,
        level=level,
        limit=limit,
    )


@mcp.tool()
def resolve_place_alias_tool(
    name: str,
    province: str = "",
    city: str = "",
    county: str = "",
    level: str = "",
    limit: int = 20,
) -> dict:
    """Resolve a Chinese place name through generated aliases."""
    return resolve_place_alias(
        name,
        province=province,
        city=city,
        county=county,
        level=level,
        limit=limit,
    )


@mcp.tool()
def search_aliases_tool(
    keyword: str,
    province: str = "",
    city: str = "",
    county: str = "",
    level: str = "",
    limit: int = 20,
) -> dict:
    """Search generated aliases by keyword."""
    return search_aliases(
        keyword,
        province=province,
        city=city,
        county=county,
        level=level,
        limit=limit,
    )


@mcp.tool()
def get_admin_children_tool(code: str, limit: int = 200) -> dict:
    """Return child administrative units for a place code."""
    return get_admin_children(code, limit=limit)


@mcp.tool()
def get_place_by_code_tool(code: str) -> dict:
    """Return one local place by code."""
    return get_place_by_code(code)


@mcp.tool()
def compare_same_name_tool(name: str, limit: int = 100) -> dict:
    """Return same-name place candidates and distribution summaries."""
    return compare_same_name(name, limit=limit)


@mcp.tool()
def get_place_origin_tool(
    name: str,
    province: str = "",
    city: str = "",
    county: str = "",
    limit: int = 5,
) -> dict:
    """Return locally cached origin, meaning, and history for a place."""
    return get_place_origin(name, province=province, city=city, county=county, limit=limit)


@mcp.tool()
def search_knowledge_tool(
    keyword: str,
    province: str = "",
    city: str = "",
    county: str = "",
    limit: int = 20,
) -> dict:
    """Search locally cached origin knowledge by keyword."""
    return search_knowledge(keyword, province=province, city=city, county=county, limit=limit)


@mcp.tool()
def fetch_place_origin_tool(
    name: str,
    province: str = "",
    city: str = "",
    county: str = "",
    place_type: str = "",
    limit: int = 1,
) -> dict:
    """Fetch and cache origin knowledge from China National Geographical Names DB."""
    return fetch_and_save(
        name,
        province=province,
        city=city,
        county=county,
        place_type=place_type,
        limit=limit,
    )


if __name__ == "__main__":
    mcp.run()
