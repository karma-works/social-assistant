"""LangGraph pipeline definition — one thread per signal."""
from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

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


async def get_graph():
    """Return a compiled graph with a PostgresSaver checkpointer."""
    settings = get_settings()
    checkpointer = AsyncPostgresSaver.from_conn_string(settings.database_url)
    await checkpointer.setup()
    return build_graph(checkpointer)
