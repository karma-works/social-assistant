"""Deduplication — LLM semantic check against local post store (ADR-002)."""
import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_vertexai import ChatVertexAI

from pipeline import db
from pipeline.settings import get_config, get_settings
from pipeline.state import Signal


_DEDUP_SYSTEM = """\
You are a deduplication assistant. Your job is to decide whether a new social media signal
describes a topic that has already been covered in recent posts.

Rules:
- Same project + same type of news (e.g. another star milestone for the same repo) = duplicate
- New release of the same project is NOT a duplicate of a previous star post
- A new repo is never a duplicate of anything
- Be conservative: if in doubt, treat as NOT a duplicate so nothing is missed

Respond with JSON only:
{"is_duplicate": true/false, "reason": "one sentence"}
"""


def _llm_fast() -> ChatVertexAI:
    s = get_settings()
    return ChatVertexAI(
        model_name=s.model_fast,
        project=s.gcp_project,
        location=s.vertex_ai_location,
        temperature=0,
    )


def _format_signal(signal: Signal) -> str:
    return (
        f"Source: {signal['source']}\n"
        f"Repo: {signal['repo']}\n"
        f"Data: {json.dumps(signal['raw_data'], indent=2)[:800]}"
    )


def _format_posts(posts: list[dict]) -> str:
    if not posts:
        return "(no recent posts)"
    lines = []
    for p in posts[:20]:  # cap context size
        lines.append(f"- [{p['platform']}] {p['topic_summary']} (published {p['published_at'][:10]})")
    return "\n".join(lines)


async def deduplicate_signals(signals: list[Signal]) -> list[Signal]:
    """
    Filter out signals whose topic was already covered.
    Also generates topic_summary for each surviving signal.
    """
    config = get_config()
    recent_posts = await db.get_recent_posts(config.pipeline.get("dedup_lookback_days", 90))
    llm = _llm_fast()

    kept: list[Signal] = []
    for signal in signals:
        if await _is_duplicate(signal, recent_posts, llm):
            await db.update_signal_status(signal["id"], "discarded")
            continue

        # Generate topic_summary for surviving signal
        summary = await _generate_topic_summary(signal, llm)
        signal = {**signal, "topic_summary": summary}
        await db.save_signal(signal)
        kept.append(signal)

    return kept


async def _is_duplicate(signal: Signal, recent_posts: list[dict], llm: ChatVertexAI) -> bool:
    if not recent_posts:
        return False

    response = await llm.ainvoke([
        SystemMessage(_DEDUP_SYSTEM),
        HumanMessage(
            f"Recent posts:\n{_format_posts(recent_posts)}\n\n"
            f"New signal:\n{_format_signal(signal)}"
        ),
    ])

    try:
        result = json.loads(response.content)
        return bool(result.get("is_duplicate", False))
    except (json.JSONDecodeError, AttributeError):
        return False  # parse error → keep the signal


async def _generate_topic_summary(signal: Signal, llm: ChatVertexAI) -> str:
    response = await llm.ainvoke([
        SystemMessage(
            "Generate a short (max 15 words) topic summary for this signal. "
            "Focus on the project name and what happened. "
            "Respond with only the summary, no quotes."
        ),
        HumanMessage(_format_signal(signal)),
    ])
    return str(response.content).strip()
