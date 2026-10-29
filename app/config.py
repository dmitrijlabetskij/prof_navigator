"""
Конфигурация приложения «Профессиональный навигатор».
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
GRAPH_DATA_PATH = DATA_DIR / "sverdlovsk_graph.json"
DATABASE_PATH = BASE_DIR / "navigator.sqlite3"

HOST = "0.0.0.0"
PORT = 8000
DEBUG = True

