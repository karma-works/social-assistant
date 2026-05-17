from typing import Literal, Optional
from typing_extensions import TypedDict


class Signal(TypedDict):
    id: str
    source: Literal["github_release", "github_stars", "github_new_repo"]
    repo: str                   # owner/repo
    topic_summary: Optional[str]
    raw_data: dict              # source-specific payload
    detected_at: str            # ISO 8601


class QAResult(TypedDict):
    style_score: int            # 1–5
    style_issues: list[str]
    factuality_pass: bool
    factuality_issues: list[str]
    format_pass: bool
    format_issues: list[str]
    overall: Literal["pass", "warn", "fail"]


class PipelineState(TypedDict):
    run_id: str                                         # == LangGraph thread_id
    active_signal: Signal
    draft: Optional[str]                                # Bluesky post text (≤300 chars)
    x_draft: Optional[str]                              # X/Twitter post text (≤280 chars)
    qa_result: Optional[QAResult]
    qa_retries: int
    qa_feedback: Optional[str]                          # injected into draft node on retry
    approval_status: Optional[Literal["approved", "rejected", "edit", "regenerate"]]
    edit_instruction: Optional[str]                     # free-text correction from user
    published_post_id: Optional[str]
    error: Optional[str]
