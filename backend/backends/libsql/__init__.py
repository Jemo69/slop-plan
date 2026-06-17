import asyncio
import os
import sqlite3
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any, TypeVar

from pypika_tortoise import SQLLiteQuery

from tortoise.backends.base.client import (
    BaseDBAsyncClient,
    Capabilities,
    ConnectionWrapper,
    NestedTransactionContext,
    TransactionContext,
)
from tortoise.backends.sqlite.executor import SqliteExecutor
from tortoise.backends.sqlite.schema_generator import SqliteSchemaGenerator
from tortoise.connection import get_connections
from tortoise.exceptions import (
    IntegrityError,
    OperationalError,
    TransactionManagementError,
)

from libsql_adapter import LibSQLConnection

T = TypeVar("T")
FuncType = Callable[..., Coroutine[None, None, T]]


def translate_exceptions(func: FuncType) -> FuncType:
    @wraps(func)
    async def translate_exceptions_(self, query, *args) -> T:
        try:
            return await func(self, query, *args)
        except sqlite3.OperationalError as exc:
            raise OperationalError(exc)
        except sqlite3.IntegrityError as exc:
            raise IntegrityError(exc)
    return translate_exceptions_


class LibSQLClient(BaseDBAsyncClient):
    executor_class = SqliteExecutor
    query_class = SQLLiteQuery
    schema_generator = SqliteSchemaGenerator
    capabilities = Capabilities(
        "sqlite",
        daemon=False,
        requires_limit=True,
        inline_comment=True,
        support_for_update=False,
        support_update_limit_order_by=False,
        can_rollback_ddl=True,
        support_returning=True,
    )

    def __init__(self, file_path: str, auth_token: str = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.filename = file_path
        self.auth_token = auth_token

        self.pragmas = kwargs.copy()
        self.pragmas.pop("connection_name", None)
        self.pragmas.pop("fetch_inserted", None)
        self.pragmas.pop("auth_token", None)
        self.pragmas.setdefault("journal_mode", "WAL")
        self.pragmas.setdefault("journal_size_limit", 16384)
        self.pragmas.setdefault("foreign_keys", "ON")

        self._connection: LibSQLConnection | None = None
        self._lock = asyncio.Lock()

    async def create_connection(self, with_db: bool) -> None:
        if not self._connection:
            self._connection = LibSQLConnection(self.filename, self.auth_token)
            self.log.debug("Connected to Turso via HTTP: %s", self.filename)

            await self._post_connect()

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()
            self.log.debug("Closed libsql connection with params: filename=%s", self.filename)
            self._connection = None

    async def db_create(self) -> None:
        pass

    async def db_delete(self) -> None:
        await self.close()
        try:
            os.remove(self.filename)
        except FileNotFoundError:
            pass
        except OSError as e:
            if e.errno != 22:
                raise e

    def acquire_connection(self) -> ConnectionWrapper:
        return ConnectionWrapper(self._lock, self)

    def _in_transaction(self) -> TransactionContext:
        return LibSQLTransactionContext(LibSQLTransactionWrapper(self), self._lock)

    @translate_exceptions
    async def execute_insert(self, query: str, values: list) -> int:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            return (await connection.execute_insert(query, values))[0]

    @translate_exceptions
    async def execute_many(self, query: str, values: list[list]) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            await connection.execute("BEGIN")
            try:
                await connection.executemany(query, values)
            except Exception:
                await connection.rollback()
                raise
            else:
                await connection.commit()

    @translate_exceptions
    async def execute_query(
        self, query: str, values: list | None = None
    ) -> tuple[int, Any]:
        query = query.replace("\x00", "'||CHAR(0)||'")
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            rows = await connection.execute_fetchall(query, values)
            return len(rows) or 0, rows

    @translate_exceptions
    async def execute_query_dict(self, query: str, values: list | None = None) -> list[dict]:
        query = query.replace("\x00", "'||CHAR(0)||'")
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            rows = await connection.execute_fetchall(query, values)
            return [dict(row) for row in rows]

    @translate_exceptions
    async def execute_script(self, query: str) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug(query)
            await connection.executescript(query)


class LibSQLTransactionContext(TransactionContext):
    __slots__ = ("connection", "connection_name", "token", "_trxlock")

    def __init__(self, connection: Any, trxlock: asyncio.Lock) -> None:
        self.connection = connection
        self.connection_name = connection.connection_name
        self._trxlock = trxlock

    async def ensure_connection(self) -> None:
        if not self.connection._connection:
            await self.connection._parent.create_connection(with_db=True)
            self.connection._connection = self.connection._parent._connection

    async def __aenter__(self):
        await self._trxlock.acquire()
        await self.ensure_connection()
        self.token = get_connections().set(self.connection_name, self.connection)
        await self.connection.begin()
        return self.connection

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            if not self.connection._finalized:
                if exc_type:
                    if exc_type is not TransactionManagementError:
                        await self.connection.rollback()
                else:
                    await self.connection.commit()
        finally:
            get_connections().reset(self.token)
            self._trxlock.release()


class LibSQLTransactionWrapper(LibSQLClient):
    def __init__(self, connection: LibSQLClient) -> None:
        self.capabilities = connection.capabilities
        self.connection_name = connection.connection_name
        self._connection = connection._connection
        self._lock = asyncio.Lock()
        self._savepoint = None
        self.log = connection.log
        self._finalized = False
        self.fetch_inserted = connection.fetch_inserted
        self._parent = connection

    def _in_transaction(self) -> TransactionContext:
        return NestedTransactionContext(LibSQLTransactionWrapper(self))

    @translate_exceptions
    async def execute_many(self, query: str, values: list[list]) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            await connection.executemany(query, values)

    async def begin(self) -> None:
        try:
            await self._connection.commit()
            await self._connection.execute("BEGIN")
        except sqlite3.OperationalError as exc:
            raise TransactionManagementError(exc)

    async def rollback(self) -> None:
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        await self._connection.rollback()
        self._finalized = True

    async def commit(self) -> None:
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        await self._connection.commit()
        self._finalized = True

    async def savepoint(self) -> None:
        from itertools import count
        self._savepoint = f"tortoise_savepoint_{next(count())}"
        await self._connection.execute(f"SAVEPOINT {self._savepoint}")

    async def savepoint_rollback(self) -> None:
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        if self._savepoint is None:
            raise TransactionManagementError("No savepoint to rollback to")
        await self._connection.execute(f"ROLLBACK TO {self._savepoint}")
        self._savepoint = None

    async def release_savepoint(self) -> None:
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        if self._savepoint is None:
            raise TransactionManagementError("No savepoint to rollback to")
        await self._connection.execute(f"RELEASE {self._savepoint}")


client_class = LibSQLClient
