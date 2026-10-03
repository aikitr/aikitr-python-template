from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass
class FakeMeta:
    changes: int = 0
    last_row_id: int = 0


@dataclass
class FakeResult:
    results: list[dict[str, object]]
    meta: FakeMeta


class FakeD1:
    """Small SQLite-backed double with the D1 prepared-statement interface."""

    def __init__(self) -> None:
        self.connection = sqlite3.connect(":memory:", check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(
            "CREATE TABLE tasks ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "title VARCHAR(200) NOT NULL, "
            "completed INTEGER NOT NULL DEFAULT 0)"
        )
        self.fail_next_write = False

    def prepare(self, query: str) -> FakePreparedStatement:
        return FakePreparedStatement(self, query)


class FakePreparedStatement:
    def __init__(self, database: FakeD1, query: str, values: tuple[object, ...] = ()) -> None:
        self.database = database
        self.query = query
        self.values = values

    def bind(self, *values: object) -> FakePreparedStatement:
        return FakePreparedStatement(self.database, self.query, values)

    async def first(self) -> dict[str, object] | None:
        row = self.database.connection.execute(self.query, self.values).fetchone()
        return dict(row) if row is not None else None

    async def all(self) -> FakeResult:
        rows = self.database.connection.execute(self.query, self.values).fetchall()
        return FakeResult([dict(row) for row in rows], FakeMeta(changes=len(rows)))

    async def run(self) -> FakeResult:
        if self.database.fail_next_write and self.query.lstrip().upper().startswith(
            ("INSERT", "UPDATE", "DELETE")
        ):
            self.database.fail_next_write = False
            raise RuntimeError("simulated D1 write failure")

        cursor = self.database.connection.execute(self.query, self.values)
        self.database.connection.commit()
        return FakeResult(
            [],
            FakeMeta(changes=cursor.rowcount, last_row_id=cursor.lastrowid or 0),
        )
