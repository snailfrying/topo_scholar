import csv
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from topo_scholar.normalize import generate_aliases, normalize_place_name

PROCESSED_DIR = ROOT / "data" / "processed"
DB_PATH = PROCESSED_DIR / "topo_scholar.sqlite"


def load_csv(conn: sqlite3.Connection, table: str, path: Path) -> None:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        quoted_columns = ", ".join(f'"{c}" TEXT' for c in columns)
        conn.execute(f'DROP TABLE IF EXISTS "{table}"')
        conn.execute(f'CREATE TABLE "{table}" ({quoted_columns})')

        placeholders = ", ".join("?" for _ in columns)
        insert_sql = f'INSERT INTO "{table}" ({", ".join(columns)}) VALUES ({placeholders})'
        batch = []
        for row in reader:
            batch.append([row.get(c, "") for c in columns])
            if len(batch) >= 10000:
                conn.executemany(insert_sql, batch)
                batch.clear()
        if batch:
                conn.executemany(insert_sql, batch)


def build_aliases(conn: sqlite3.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS place_aliases")
    conn.execute(
        """
        CREATE TABLE place_aliases (
            alias TEXT,
            normalized_alias TEXT,
            place_id TEXT,
            code TEXT,
            name TEXT,
            full_name TEXT,
            level TEXT,
            source TEXT
        )
        """
    )

    rows = conn.execute(
        """
        SELECT id, code, name, full_name, level, source
        FROM places
        """
    )
    batch = []
    for row in rows:
        place_id, code, name, full_name, level, source = row
        for alias in generate_aliases(name):
            batch.append(
                (
                    alias,
                    normalize_place_name(alias),
                    place_id,
                    code,
                    name,
                    full_name,
                    level,
                    source,
                )
            )
            if len(batch) >= 10000:
                conn.executemany(
                    "INSERT INTO place_aliases VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    batch,
                )
                batch.clear()
    if batch:
        conn.executemany("INSERT INTO place_aliases VALUES (?, ?, ?, ?, ?, ?, ?, ?)", batch)


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        load_csv(conn, "places", PROCESSED_DIR / "places.csv")
        load_csv(conn, "admin_edges", PROCESSED_DIR / "admin_edges.csv")
        knowledge_csv = PROCESSED_DIR / "place_knowledge.csv"
        if knowledge_csv.exists():
            load_csv(conn, "place_knowledge", knowledge_csv)
        build_aliases(conn)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_places_code ON places(code)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_places_name ON places(name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_places_full_name ON places(full_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_places_level ON places(level)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_places_parent_code ON places(parent_code)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_places_name_scope ON places(name, province, city, county)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_places_scope_level ON places(province, city, county, level)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_parent_code ON admin_edges(parent_code)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_child_code ON admin_edges(child_code)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_aliases_alias ON place_aliases(alias)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_aliases_normalized ON place_aliases(normalized_alias)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_aliases_place_id ON place_aliases(place_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_aliases_code ON place_aliases(code)")
        if knowledge_csv.exists():
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_id ON place_knowledge(id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_name ON place_knowledge(standard_name)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_knowledge_name_scope "
                "ON place_knowledge(standard_name, province, city, county)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_place_id ON place_knowledge(place_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_source_place_id ON place_knowledge(source_place_id)")
        conn.commit()

        count = conn.execute("SELECT COUNT(*) FROM places").fetchone()[0]
        print(f"Wrote {count} places to {DB_PATH}")
        alias_count = conn.execute("SELECT COUNT(*) FROM place_aliases").fetchone()[0]
        print(f"Wrote {alias_count} aliases to {DB_PATH}")
        if knowledge_csv.exists():
            knowledge_count = conn.execute("SELECT COUNT(*) FROM place_knowledge").fetchone()[0]
            print(f"Wrote {knowledge_count} knowledge rows to {DB_PATH}")


if __name__ == "__main__":
    main()
