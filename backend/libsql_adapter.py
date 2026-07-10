import asyncio
from typing import Any
import httpx


def _infer_turso_type(value: Any) -> tuple[str, Any]:
    if value is None:
        return "null", None
    if isinstance(value, bool):
        return "integer", str(int(value))
    if isinstance(value, int):
        return "integer", str(value)
    if isinstance(value, float):
        return "float", value
    return "text", str(value)


class LibSQLRow:
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
    def __init__(self, columns: list[dict] = None, rows: list[list] = None, lastrowid=None):
        self._columns = columns or []
        self._rows = []
        self.lastrowid = lastrowid
        self.row_factory = None

        if rows:
            for row in rows:
                vals = []
                for v in row:
                    if isinstance(v, dict):
                        value_type = v.get("type")
                        value = v.get("value")
                        if value_type == "integer":
                            value = int(value)
                        elif value_type == "float":
                            value = float(value)
                        elif value_type == "null":
                            value = None
                        vals.append(value)
                    else:
                        vals.append(v)
                self._rows.append(LibSQLRow(self._columns, vals))

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
    def __init__(self, url: str, auth_token: str):
        clean = url.strip()
        for prefix in ("libsql://", "https://", "http://"):
            if clean.startswith(prefix):
                clean = clean[len(prefix):]
        clean = clean.rstrip("/")
        self._host = clean
        self._url = f"https://{clean}/v2/pipeline"
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
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self._url,
                headers={
                    "Authorization": f"Bearer {self._auth_token}",
                    "Content-Type": "application/json",
                },
                json={"requests": requests},
            )
            response.raise_for_status()
            data = response.json()
            return data

    def _build_stmt(self, sql: str, parameters) -> dict:
        stmt = {"sql": sql}
        if parameters:
            args = []
            for p in parameters:
                t, v = _infer_turso_type(p)
                if t == "null":
                    args.append({"type": "null"})
                else:
                    args.append({"type": t, "value": v})
            stmt["args"] = args
        return stmt

    @staticmethod
    def _sanitize_sql(sql: str) -> str:
        import re
        sql = re.sub(r'=\s*True\b', '= 1', sql, flags=re.IGNORECASE)
        sql = re.sub(r'=\s*False\b', '= 0', sql, flags=re.IGNORECASE)
        sql = re.sub(r'IS\s+True\b', '= 1', sql, flags=re.IGNORECASE)
        sql = re.sub(r'IS\s+False\b', '= 0', sql, flags=re.IGNORECASE)
        sql = re.sub(r'IS\s+NOT\s+True\b', '!= 1', sql, flags=re.IGNORECASE)
        sql = re.sub(r'IS\s+NOT\s+False\b', '!= 0', sql, flags=re.IGNORECASE)
        return sql

    async def execute(self, sql: str, parameters: tuple | list | None = None):
        if parameters is None:
            parameters = ()

        sql = self._sanitize_sql(sql)
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
        if requests:
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
