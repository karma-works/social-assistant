"""Draft generation node — produces platform-specific drafts for Bluesky and X."""
import json
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_vertexai import ChatVertexAI

from pipeline.nodes import extract_text
from pipeline.settings import get_settings
from pipeline.state import PipelineState, Signal

_SEPARATOR = "---X---"


def _load_prompt(name: str) -> str:
    return Path(f"prompts/{name}").read_text()


def _llm() -> ChatVertexAI:
    s = get_settings()
    return ChatVertexAI(
        model_name=s.model_default,
        project=s.gcp_project,
        location=s.vertex_ai_location,
        temperature=0.4,
    )


def _format_signal(signal: Signal) -> str:
    return (
        f"Signal type: {signal['source']}\n"
        f"Repository: {signal['repo']}\n"
        f"Data:\n{json.dumps(signal['raw_data'], indent=2)[:1200]}"
    )


def _parse_drafts(raw: str) -> tuple[str, str]:
    """Split LLM output into (bluesky_draft, x_draft)."""
    parts = raw.split(_SEPARATOR, 1)
    bluesky = parts[0].strip()
    x = parts[1].strip() if len(parts) > 1 else bluesky[:280]
    return bluesky, x


async def draft_node(state: PipelineState) -> dict:
    brand_voice = _load_prompt("brand_voice.md")
    system_prompt = _load_prompt("draft_generation.md").replace("{brand_voice}", brand_voice)
    llm = _llm()

    signal = state["active_signal"]
    edit_instruction = state.get("edit_instruction")
    qa_feedback = state.get("qa_feedback")
    previous_draft = state.get("draft")

    if edit_instruction:
        user_msg = (
            f"Bluesky draft:\n{previous_draft}\n\n"
            f"X draft:\n{state.get('x_draft', '')}\n\n"
            f"User correction: {edit_instruction}\n\n"
            f"Signal:\n{_format_signal(signal)}"
        )
    elif qa_feedback and previous_draft:
        user_msg = (
            f"Bluesky draft (failed QA):\n{previous_draft}\n\n"
            f"X draft:\n{state.get('x_draft', '')}\n\n"
            f"QA feedback to fix:\n{qa_feedback}\n\n"
            f"Signal:\n{_format_signal(signal)}"
        )
    else:
        user_msg = f"Signal:\n{_format_signal(signal)}"

    response = await llm.ainvoke([
        SystemMessage(system_prompt),
        HumanMessage(user_msg),
    ])

    bluesky_draft, x_draft = _parse_drafts(extract_text(response.content))

    return {
        "draft": bluesky_draft,
        "x_draft": x_draft,
        "edit_instruction": None,
        "qa_feedback": None,
    }
