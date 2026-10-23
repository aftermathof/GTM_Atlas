import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def data_dir():
    path = Path(os.getenv("DATA_DIR", str(ROOT / ".data"))).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_url():
    return os.getenv("DATABASE_URL", "sqlite:///" + (data_dir() / "atlas.db").as_posix())
