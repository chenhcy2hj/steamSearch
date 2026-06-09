from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Optional

from app.core.errors import DatabaseError


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._connection: Optional[sqlite3.Connection] = None

    @property
    def connection(self) -> sqlite3.Connection:
        if self._connection is None:
            raise DatabaseError("Database is not connected")
        return self._connection

    def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")

    def execute_script(self, script: str) -> None:
        self.connection.executescript(script)
        self.connection.commit()

    def execute(self, sql: str, params: Iterable[object] = ()) -> sqlite3.Cursor:
        cursor = self.connection.execute(sql, tuple(params))
        self.connection.commit()
        return cursor

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

