"""LangGraph pipeline definition — one thread per signal."""
from contextlib import asynccontextmanager
from typing import AsyncIterator

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from pipeline.state import PipelineState
from pipeline.nodes.draft import draft_node
from pipeline.nodes.qa import qa_node, route_after_qa
from pipeline.nodes.telegram_send import telegram_send_node, route_after_approval
from pipeline.nodes.publish import publish_node
from pipeline.settings import get_settings


def build_graph(checkpointer: AsyncPostgresSaver) -> object:
    builder = StateGraph(PipelineState)

    builder.add_node("draft", draft_node)
    builder.add_node("qa", qa_node)
    builder.add_node("telegram_send", telegram_send_node)
    builder.add_node("publish", publish_node)

    builder.add_edge(START, "draft")
    builder.add_edge("draft", "qa")

    builder.add_conditional_edges(
        "qa",
        route_after_qa,
        {"telegram_send": "telegram_send", "draft": "draft", END: END},
    )

    # After interrupt() in telegram_send resolves, route on approval_status
    builder.add_conditional_edges(
        "telegram_send",
        route_after_approval,
        {"publish": "publish", "draft": "draft", END: END},
    )

    builder.add_edge("publish", END)

    return builder.compile(checkpointer=checkpointer)


@asynccontextmanager
async def get_graph() -> AsyncIterator[object]:
    """Async context manager yielding a compiled graph (short-lived, e.g. runner.py)."""
    settings = get_settings()
    async with AsyncPostgresSaver.from_conn_string(settings.database_url) as checkpointer:
        await checkpointer.setup()
        yield build_graph(checkpointer)


@asynccontextmanager
async def get_persistent_graph() -> AsyncIterator[object]:
    """Async context manager yielding a compiled graph backed by a connection pool (long-lived processes)."""
    settings = get_settings()
    # setup() runs CREATE INDEX CONCURRENTLY which requires autocommit;
    # from_conn_string uses autocommit=True so it's safe here.
    async with AsyncPostgresSaver.from_conn_string(settings.database_url) as tmp:
        await tmp.setup()
    pool = AsyncConnectionPool(conninfo=settings.database_url, open=False)
    await pool.open()
    try:
        checkpointer = AsyncPostgresSaver(pool)
        yield build_graph(checkpointer)
    finally:
        await pool.close()
