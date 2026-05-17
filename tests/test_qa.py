"""Tests for QA node routing logic."""
import pytest
from pipeline.nodes.qa import route_after_qa


def _state(overall: str, retries: int = 0) -> dict:
    return {
        "qa_result": {
            "style_score": 4,
            "style_issues": [],
            "factuality_pass": True,
            "factuality_issues": [],
            "format_pass": True,
            "format_issues": [],
            "overall": overall,
        },
        "qa_retries": retries,
        "active_signal": {},
        "draft": "some draft",
        "run_id": "test",
        "qa_feedback": None,
        "approval_status": None,
        "edit_instruction": None,
        "published_post_id": None,
        "error": None,
    }


def test_route_pass_goes_to_telegram():
    assert route_after_qa(_state("pass")) == "telegram_send"


def test_route_warn_goes_to_telegram():
    assert route_after_qa(_state("warn")) == "telegram_send"


def test_route_fail_retries_draft():
    assert route_after_qa(_state("fail", retries=0)) == "draft"
    assert route_after_qa(_state("fail", retries=1)) == "draft"


def test_route_fail_exhausted_ends():
    from langgraph.graph import END
    assert route_after_qa(_state("fail", retries=2)) == END
