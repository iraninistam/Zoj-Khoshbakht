import asyncpg
from config import DATABASE_URL


_pool = None


async def init_database():

    global _pool

    _pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=1,
        max_size=10
    )


async def close_database():

    global _pool

    if _pool:
        await _pool.close()



async def fetch(query, *args):

    async with _pool.acquire() as conn:
        return await conn.fetch(
            query,
            *args
        )



async def fetchrow(query, *args):

    async with _pool.acquire() as conn:
        return await conn.fetchrow(
            query,
            *args
        )



async def execute(query, *args):

    async with _pool.acquire() as conn:
        return await conn.execute(
            query,
            *args
        )



# -------------------------
# Users
# -------------------------

async def save_user(
    telegram_id,
    username,
    first_name
):

    await execute(
        """
        INSERT INTO users
        (
            telegram_id,
            username,
            first_name,
            last_seen
        )

        VALUES
        ($1,$2,$3,NOW())

        ON CONFLICT
        (telegram_id)

        DO UPDATE SET

        username=$2,
        first_name=$3,
        last_seen=NOW()
        """,

        telegram_id,
        username,
        first_name
    )



async def get_user(
    telegram_id
):

    return await fetchrow(
        """
        SELECT *
        FROM users
        WHERE telegram_id=$1
        """,

        telegram_id
    )



async def get_user_by_username(
    username
):

    return await fetchrow(
        """
        SELECT *
        FROM users
        WHERE username=$1
        """,

        username.replace("@","")
    )



# -------------------------
# Logs
# -------------------------

async def add_log(
    service,
    status,
    message
):

    await execute(
        """
        INSERT INTO logs
        (
            service,
            status,
            message
        )

        VALUES
        ($1,$2,$3)
        """,

        service,
        status,
        message
    )



async def get_logs(limit=10):

    return await fetch(
        """
        SELECT *
        FROM logs

        ORDER BY created_at DESC

        LIMIT $1
        """,

        limit
    )