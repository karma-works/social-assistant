"""Database helpers — thin wrapper over psycopg3. No ORM."""
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from pipeline.settings import get_settings


@asynccontextmanager
async def get_conn() -> AsyncGenerator[psycopg.AsyncConnection, None]:
    settings = get_settings()
    async with await psycopg.AsyncConnection.connect(
        settings.database_url, row_factory=dict_row
    ) as conn:
        yield conn


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------

async def save_signal(signal: dict) -> None:
    async with get_conn() as conn:
        await conn.execute(
            """
            INSERT INTO signals (id, source, repo, topic_summary, raw_data, detected_at, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'pending')
            ON CONFLICT (id) DO NOTHING
            """,
            (
                signal["id"],
                signal["source"],
                signal["repo"],
                signal.get("topic_summary"),
                json.dumps(signal["raw_data"]),
                signal["detected_at"],
            ),
        )
        await conn.commit()


async def update_signal_status(signal_id: str, status: str) -> None:
    async with get_conn() as conn:
        await conn.execute(
            "UPDATE signals SET status = %s WHERE id = %s",
            (status, signal_id),
        )
        await conn.commit()


async def get_last_release_id(repo: str) -> str | None:
    async with get_conn() as conn:
        row = await conn.execute(
            """
            SELECT raw_data->>'release_id' AS release_id
            FROM signals
            WHERE repo = %s AND source = 'github_release'
            ORDER BY detected_at DESC
            LIMIT 1
            """,
            (repo,),
        )
        result = await row.fetchone()
        return result["release_id"] if result else None


async def get_last_star_count(repo: str) -> dict | None:
    """Returns {count, checked_at} or None."""
    async with get_conn() as conn:
        row = await conn.execute(
            """
            SELECT raw_data->>'stars' AS stars,
                   raw_data->>'checked_at' AS checked_at
            FROM signals
            WHERE repo = %s AND source = 'github_stars'
            ORDER BY detected_at DESC
            LIMIT 1
            """,
            (repo,),
        )
        result = await row.fetchone()
        if result and result["stars"]:
            return {"count": int(result["stars"]), "checked_at": result["checked_at"]}
        return None


async def get_days_since_last_star_post(repo: str) -> int | None:
    async with get_conn() as conn:
        row = await conn.execute(
            """
            SELECT detected_at FROM signals
            WHERE repo = %s AND source = 'github_stars' AND status = 'approved'
            ORDER BY detected_at DESC
            LIMIT 1
            """,
            (repo,),
        )
        result = await row.fetchone()
        if not result:
            return None
        last = datetime.fromisoformat(result["detected_at"])
        return (datetime.now(timezone.utc) - last).days


async def known_repos(user: str) -> set[str]:
    async with get_conn() as conn:
        rows = await conn.execute(
            "SELECT repo FROM signals WHERE repo LIKE %s",
            (f"{user}/%",),
        )
        return {r["repo"] async for r in rows}


# ---------------------------------------------------------------------------
# Posts (dedup source of truth)
# ---------------------------------------------------------------------------

async def save_post(
    *,
    signal_id: str,
    platform: str,
    topic_summary: str,
    content: str,
    platform_post_id: str,
    metadata: dict | None = None,
) -> None:
    from uuid import uuid4
    async with get_conn() as conn:
        await conn.execute(
            """
            INSERT INTO posts
                (id, signal_id, platform, topic_summary, content, published_at, platform_post_id, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                str(uuid4()),
                signal_id,
                platform,
                topic_summary,
                content,
                datetime.now(timezone.utc).isoformat(),
                platform_post_id,
                json.dumps(metadata or {}),
            ),
        )
        await conn.commit()


async def get_recent_posts(lookback_days: int) -> list[dict]:
    async with get_conn() as conn:
        rows = await conn.execute(
            """
            SELECT topic_summary, content, platform, published_at
            FROM posts
            WHERE published_at > NOW() - INTERVAL '%s days'
            ORDER BY published_at DESC
            """,
            (lookback_days,),
        )
        return [dict(r) async for r in rows]


# ---------------------------------------------------------------------------
# Thread tracking (LangGraph thread_id → signal_id)
# ---------------------------------------------------------------------------

async def save_thread(thread_id: str, signal_id: str) -> None:
    async with get_conn() as conn:
        await conn.execute(
            """
            INSERT INTO threads (thread_id, signal_id, created_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (thread_id) DO NOTHING
            """,
            (thread_id, signal_id, datetime.now(timezone.utc).isoformat()),
        )
        await conn.commit()


async def get_signal_id_for_thread(thread_id: str) -> str | None:
    async with get_conn() as conn:
        row = await conn.execute(
            "SELECT signal_id FROM threads WHERE thread_id = %s",
            (thread_id,),
        )
        result = await row.fetchone()
        return result["signal_id"] if result else None
