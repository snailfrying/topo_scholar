import argparse
import json

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


def print_json(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="TopoScholar JSON CLI for local Agent tooling.")
    sub = parser.add_subparsers(dest="command", required=True)

    resolve = sub.add_parser("resolve", help="Resolve an exact place name")
    resolve.add_argument("name")
    resolve.add_argument("--province", default="")
    resolve.add_argument("--city", default="")
    resolve.add_argument("--county", default="")
    resolve.add_argument("--level", default="")
    resolve.add_argument("--limit", type=int, default=20)

    search = sub.add_parser("search", help="Search places by keyword")
    search.add_argument("keyword")
    search.add_argument("--province", default="")
    search.add_argument("--city", default="")
    search.add_argument("--county", default="")
    search.add_argument("--level", default="")
    search.add_argument("--limit", type=int, default=20)

    alias = sub.add_parser("alias", help="Resolve a place name through generated aliases")
    alias.add_argument("name")
    alias.add_argument("--province", default="")
    alias.add_argument("--city", default="")
    alias.add_argument("--county", default="")
    alias.add_argument("--level", default="")
    alias.add_argument("--limit", type=int, default=20)

    alias_search = sub.add_parser("search-alias", help="Search generated aliases by keyword")
    alias_search.add_argument("keyword")
    alias_search.add_argument("--province", default="")
    alias_search.add_argument("--city", default="")
    alias_search.add_argument("--county", default="")
    alias_search.add_argument("--level", default="")
    alias_search.add_argument("--limit", type=int, default=20)

    children = sub.add_parser("children", help="Get admin children by code")
    children.add_argument("code")
    children.add_argument("--limit", type=int, default=200)

    code = sub.add_parser("code", help="Get a place by code")
    code.add_argument("code")

    same = sub.add_parser("same-name", help="Compare same-name places")
    same.add_argument("name")
    same.add_argument("--limit", type=int, default=100)

    origin = sub.add_parser("origin", help="Get local place origin knowledge")
    origin.add_argument("name")
    origin.add_argument("--province", default="")
    origin.add_argument("--city", default="")
    origin.add_argument("--county", default="")
    origin.add_argument("--limit", type=int, default=5)

    know = sub.add_parser("search-knowledge", help="Search local origin knowledge by keyword")
    know.add_argument("keyword")
    know.add_argument("--province", default="")
    know.add_argument("--city", default="")
    know.add_argument("--county", default="")
    know.add_argument("--limit", type=int, default=20)

    fetch = sub.add_parser("fetch-origin", help="Fetch origin knowledge from China National Geographical Names DB")
    fetch.add_argument("name")
    fetch.add_argument("--province", default="")
    fetch.add_argument("--city", default="")
    fetch.add_argument("--county", default="")
    fetch.add_argument("--place-type", default="")
    fetch.add_argument("--limit", type=int, default=1)
    fetch.add_argument("--page-size", type=int, default=20)
    fetch.add_argument("--max-pages", type=int, default=3)
    fetch.add_argument("--sleep", type=float, default=0.8)

    args = parser.parse_args()
    if args.command == "resolve":
        print_json(
            resolve_place_name(
                args.name,
                province=args.province,
                city=args.city,
                county=args.county,
                level=args.level,
                limit=args.limit,
            )
        )
    elif args.command == "search":
        print_json(
            search_places(
                args.keyword,
                province=args.province,
                city=args.city,
                county=args.county,
                level=args.level,
                limit=args.limit,
            )
        )
    elif args.command == "alias":
        print_json(
            resolve_place_alias(
                args.name,
                province=args.province,
                city=args.city,
                county=args.county,
                level=args.level,
                limit=args.limit,
            )
        )
    elif args.command == "search-alias":
        print_json(
            search_aliases(
                args.keyword,
                province=args.province,
                city=args.city,
                county=args.county,
                level=args.level,
                limit=args.limit,
            )
        )
    elif args.command == "children":
        print_json(get_admin_children(args.code, limit=args.limit))
    elif args.command == "code":
        print_json(get_place_by_code(args.code))
    elif args.command == "same-name":
        print_json(compare_same_name(args.name, limit=args.limit))
    elif args.command == "origin":
        print_json(
            get_place_origin(
                args.name,
                province=args.province,
                city=args.city,
                county=args.county,
                limit=args.limit,
            )
        )
    elif args.command == "search-knowledge":
        print_json(
            search_knowledge(
                args.keyword,
                province=args.province,
                city=args.city,
                county=args.county,
                limit=args.limit,
            )
        )
    elif args.command == "fetch-origin":
        print_json(
            fetch_and_save(
                args.name,
                province=args.province,
                city=args.city,
                county=args.county,
                place_type=args.place_type,
                limit=args.limit,
                page_size=args.page_size,
                max_pages=args.max_pages,
                sleep_seconds=args.sleep,
            )
        )


if __name__ == "__main__":
    main()
