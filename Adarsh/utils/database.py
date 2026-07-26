"""Small MySQL repository used only for bot user IDs and broadcast recipients."""

import asyncio
import re

import aiomysql


class Database:
    """Lazy MySQL repository replacing the old MongoDB/Motor implementation."""

    _TABLES = {
        "users": "telegram_bot_users",
        "passwords": "telegram_bot_passwords",
    }

    def __init__(self, config, purpose: str = "users"):
        self._config = config
        self._table = self._TABLES[purpose]
        self._pool = None
        self._schema_ready = False
        self._schema_lock = asyncio.Lock()

    async def _connection_pool(self):
        if self._pool is None:
            self._pool = await aiomysql.create_pool(
                **self._config,
                minsize=1,
                maxsize=5,
                autocommit=True,
                cursorclass=aiomysql.DictCursor,
                charset="utf8mb4",
            )
        await self._ensure_schema()
        return self._pool

    async def _ensure_schema(self):
        if self._schema_ready:
            return
        async with self._schema_lock:
            if self._schema_ready:
                return
            # Table names are selected from the fixed mapping above, never user input.
            async with self._pool.acquire() as connection:
                async with connection.cursor() as cursor:
                    await cursor.execute(
                        f"""CREATE TABLE IF NOT EXISTS `{self._table}` (
                            `id` BIGINT UNSIGNED NOT NULL,
                            `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            PRIMARY KEY (`id`)
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"""
                    )
            self._schema_ready = True

    async def add_user(self, user_id):
        pool = await self._connection_pool()
        async with pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    f"INSERT IGNORE INTO `{self._table}` (`id`) VALUES (%s)",
                    (int(user_id),),
                )

    async def add_user_pass(self, user_id, _unused_password=None):
        # A successful login is tracked, but the shared login password is never stored.
        await self.add_user(user_id)

    async def get_user_pass(self, user_id):
        # Kept for compatibility with the existing handlers: True means verified.
        return await self.is_user_exist(user_id)

    async def is_user_exist(self, user_id):
        pool = await self._connection_pool()
        async with pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    f"SELECT 1 FROM `{self._table}` WHERE `id` = %s LIMIT 1",
                    (int(user_id),),
                )
                return await cursor.fetchone() is not None

    async def total_users_count(self):
        pool = await self._connection_pool()
        async with pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(f"SELECT COUNT(*) AS `count` FROM `{self._table}`")
                row = await cursor.fetchone()
                return int(row["count"])

    async def get_all_users(self):
        pool = await self._connection_pool()
        async with pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(f"SELECT `id` FROM `{self._table}` ORDER BY `id`")
                return await cursor.fetchall()

    async def delete_user(self, user_id):
        pool = await self._connection_pool()
        async with pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    f"DELETE FROM `{self._table}` WHERE `id` = %s",
                    (int(user_id),),
                )
