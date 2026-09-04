import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    operation_id TEXT NOT NULL,
    input_path TEXT NOT NULL,
    output_path TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT NOT NULL
);
"""

class HistoryDatabase:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _initialize(self):
        with sqlite3.connect(self.path) as db:
            db.executescript(SCHEMA)

    def record(self, created_at, operation_id, input_path, output_path, status, message):
        with sqlite3.connect(self.path) as db:
            db.execute(
                "INSERT INTO history(created_at, operation_id, input_path, output_path, status, message) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (created_at, operation_id, str(input_path), str(output_path), status, message),
            )
            db.commit()
