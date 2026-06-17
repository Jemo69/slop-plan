import asyncio
from typing import Any
import httpx


class LibSQLRow:
    """sqlite3.Row-compatible row object from Turso HTTP API."""

    def __init__(self, columns: list[dict], values: list):
        self._columns = [c["name"] for c in columns]
        self._values = values
        self._map = dict(zip(self._columns, values))

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return self._map[key]

    def __contains__(self, key):
        return key in self._map

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def keys(self):
        return self._columns

    def dict(self):
        return self._map


class LibSQLCursor:
    """sqlite3.Cursor-compatible cursor from Turso HTTP API."""

    def __init__(self, columns: list[dict] = None, rows: list[list] = None, lastrowid=None):
        self._columns = columns or []
        self._rows = []
        self.lastrowid = lastrowid
        self.row_factory = None

        if rows:
            for row in rows:
                self._rows.append(LibSQLRow(self._columns, [v.get("value") for v in row]))

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class LibSQLConnection:
    """Async wrapper around Turso HTTP API for Tortoise ORM compatibility."""

    def __init__(self, url: str, auth_token: str):
        self._url = f"https://{url}/v2/pipeline"
        self._auth_token = auth_token
        self.row_factory = None
        self.total_changes = 0

    @property
    def autocommit(self):
        return True

    @property
    def isolation_level(self):
        return None

    @isolation_level.setter
    def isolation_level(self, value):
        pass

    async def _execute_pipeline(self, requests: list[dict]) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self._url,
                headers={
                    "Authorization": f"Bearer {self._auth_token}",
                    "Content-Type": "application/json",
                },
                json={"requests": requests},
            )
            response.raise_for_status()
            return response.json()

    def _build_stmt(self, sql: str, parameters) -> dict:
        stmt = {"sql": sql}
        if parameters:
            stmt["args"] = [
                {"type": "text", "value": str(p)}
                for p in parameters
            ]
        return stmt

    async def execute(self, sql: str, parameters: tuple | list | None = None):
        if parameters is None:
            parameters = ()

        stmt = self._build_stmt(sql, parameters)
        result = await self._execute_pipeline([{"type": "execute", "stmt": stmt}])

        resp = result["results"][0]
        if resp.get("type") == "error":
            raise Exception(resp["error"])

        exec_result = resp["response"]["result"]
        columns = exec_result.get("cols", [])
        rows = exec_result.get("rows", [])
        last_insert = exec_result.get("last_insert_rowid")

        return LibSQLCursor(columns, rows, last_insert)

    async def executemany(self, sql: str, parameters: list[tuple] | list[list]):
        requests = []
        for params in parameters:
            stmt = self._build_stmt(sql, params)
            requests.append({"type": "execute", "stmt": stmt})
        await self._execute_pipeline(requests)

    async def executescript(self, sql: str):
        for statement in sql.split(";"):
            statement = statement.strip()
            if statement:
                await self._execute_pipeline([{"type": "execute", "stmt": {"sql": statement}}])

    async def execute_insert(self, sql: str, parameters: tuple | list | None = None):
        cursor = await self.execute(sql, parameters)
        return (cursor.lastrowid, cursor.fetchall())

    async def execute_fetchall(self, sql: str, parameters: tuple | list | None = None):
        cursor = await self.execute(sql, parameters)
        return cursor.fetchall()

    async def commit(self):
        pass

    async def rollback(self):
        pass

    async def close(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
