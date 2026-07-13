import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT / "data" / "processed" / "topo_scholar.sqlite"
PLACES_CSV = ROOT / "data" / "processed" / "places.csv"
EDGES_CSV = ROOT / "data" / "processed" / "admin_edges.csv"


def ensure_database(db_path: Path | str = DEFAULT_DB_PATH) -> None:
    db_path = Path(db_path)
    if db_path.exists():
        return

    build_places = ROOT / "scripts" / "build_places.py"
    build_sqlite = ROOT / "scripts" / "build_sqlite.py"
    if not PLACES_CSV.exists() or not EDGES_CSV.exists():
        subprocess.check_call([sys.executable, str(build_places)], cwd=str(ROOT))
    subprocess.check_call([sys.executable, str(build_sqlite)], cwd=str(ROOT))
