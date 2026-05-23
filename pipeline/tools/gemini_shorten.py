"""Shorten arbitrary text to fit X's 280-char limit using Gemini flash-lite."""
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_vertexai import ChatVertexAI

from pipeline.nodes import extract_text
from pipeline.settings import get_settings

_SYSTEM = (
    "You are a social media editor. Shorten the given text to fit within "
    "{limit} characters for X (Twitter) while preserving the core message, "
    "tone, and any URLs. Return ONLY the shortened text — no explanation, "
    "no quotes, no markdown."
)


async def shorten_for_x(text: str, limit: int = 280) -> str:
    """Return text shortened to ≤ limit chars. Calls LLM only when needed."""
    if len(text) <= limit:
        return text

    s = get_settings()
    llm = ChatVertexAI(
        model_name=s.model_fast,
        project=s.gcp_project,
        location=s.vertex_ai_location,
        temperature=0.3,
    )
    response = await llm.ainvoke([
        SystemMessage(_SYSTEM.format(limit=limit)),
        HumanMessage(text),
    ])
    shortened = extract_text(response.content).strip()
    # Hard fallback: truncate if LLM still returns too long
    if len(shortened) > limit:
        shortened = shortened[: limit - 1] + "…"
    return shortened
