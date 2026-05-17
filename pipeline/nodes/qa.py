"""QA node — factuality, style, and format checks (ADR-008)."""
import json
from pathlib import Path
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_vertexai import ChatVertexAI
from pydantic import BaseModel

from pipeline.settings import get_settings
from pipeline.state import PipelineState, QAResult


class _QAOutput(BaseModel):
    style_score: int
    style_issues: list[str]
    factuality_pass: bool
    factuality_issues: list[str]
    format_pass: bool
    format_issues: list[str]
    overall: Literal["pass", "warn", "fail"]


def _llm() -> ChatVertexAI:
    s = get_settings()
    return ChatVertexAI(
        model_name=s.model_default,
        project=s.gcp_project,
        location=s.vertex_ai_location,
        temperature=0,
    )


def _load_prompt(name: str) -> str:
    return Path(f"prompts/{name}").read_text()


def _format_signal(signal: dict) -> str:
    return (
        f"Signal type: {signal['source']}\n"
        f"Repository: {signal['repo']}\n"
        f"Data:\n{json.dumps(signal['raw_data'], indent=2)[:800]}"
    )


def _build_qa_feedback(result: QAResult) -> str:
    parts = []
    if result["style_issues"]:
        parts.append("Style issues:\n" + "\n".join(f"- {i}" for i in result["style_issues"]))
    if result["factuality_issues"]:
        parts.append("Factuality issues:\n" + "\n".join(f"- {i}" for i in result["factuality_issues"]))
    if result["format_issues"]:
        parts.append("Format issues:\n" + "\n".join(f"- {i}" for i in result["format_issues"]))
    return "\n\n".join(parts)


async def qa_node(state: PipelineState) -> dict:
    brand_voice = _load_prompt("brand_voice.md")
    system_prompt = _load_prompt("qa_check.md").replace("{brand_voice}", brand_voice)

    llm = _llm().with_structured_output(_QAOutput)

    response = await llm.ainvoke([
        SystemMessage(system_prompt),
        HumanMessage(
            f"Signal:\n{_format_signal(state['active_signal'])}\n\n"
            f"Draft:\n{state['draft']}"
        ),
    ])

    result: QAResult = response.model_dump()
    qa_feedback = _build_qa_feedback(result) if result["overall"] == "fail" else None

    return {
        "qa_result": result,
        "qa_feedback": qa_feedback,
        "qa_retries": state.get("qa_retries", 0),
    }


def route_after_qa(state: PipelineState) -> str:
    from langgraph.graph import END
    result = state["qa_result"]
    if result["overall"] in ("pass", "warn"):
        return "telegram_send"
    retries = state.get("qa_retries", 0)
    if retries < get_settings().max_qa_retries:
        return "draft"
    return END
