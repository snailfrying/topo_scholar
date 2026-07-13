from __future__ import annotations


SUFFIX_REPLACEMENTS = [
    ("社区居民委员会", "社区"),
    ("社区居委会", "社区"),
    ("村民委员会", "村"),
    ("村委会", "村"),
    ("居民委员会", "社区"),
    ("居委会", "社区"),
]

REMOVABLE_SUFFIXES = [
    "办事处",
    "街道办事处",
]


def normalize_place_name(name: str) -> str:
    return "".join((name or "").split())


def generate_aliases(name: str) -> list[str]:
    base = normalize_place_name(name)
    if not base:
        return []

    aliases = {base}
    for old, new in SUFFIX_REPLACEMENTS:
        if base.endswith(old):
            aliases.add(base[: -len(old)] + new)
            aliases.add(base[: -len(old)])

    for suffix in REMOVABLE_SUFFIXES:
        if base.endswith(suffix):
            aliases.add(base[: -len(suffix)])

    # If any source uses short village/community names, keep common long forms available too.
    expanded = set(aliases)
    for alias in aliases:
        if alias.endswith("村") and not alias.endswith("行政村"):
            expanded.add(alias + "民委员会")
            expanded.add(alias + "委会")
        if alias.endswith("社区"):
            expanded.add(alias + "居民委员会")
            expanded.add(alias + "居委会")
    aliases = expanded

    return sorted(alias for alias in aliases if alias)
