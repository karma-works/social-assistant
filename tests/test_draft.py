"""Tests for draft node — validates prompt construction, not LLM output."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pipeline.nodes.draft import draft_node


@pytest.mark.asyncio
async def test_draft_node_fresh(sample_release_signal):
    mock_response = MagicMock()
    mock_response.content = "owner/repo v1.2.0 ships 2x faster inference. github.com/owner/repo"

    with (
        patch("pipeline.nodes.draft._llm") as mock_llm_factory,
        patch("pipeline.nodes.draft._load_prompt", return_value="mock prompt {brand_voice}"),
    ):
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        state = {
            "active_signal": sample_release_signal,
            "draft": None,
            "edit_instruction": None,
            "qa_feedback": None,
            "qa_retries": 0,
            "run_id": "test-thread",
            "qa_result": None,
            "approval_status": None,
            "published_post_id": None,
            "error": None,
        }
        result = await draft_node(state)

        assert "draft" in result
        assert result["draft"] == mock_response.content
        assert result["edit_instruction"] is None
        assert result["qa_feedback"] is None


@pytest.mark.asyncio
async def test_draft_node_with_edit(sample_release_signal):
    mock_response = MagicMock()
    mock_response.content = "Shorter post about owner/repo v1.2.0"

    with (
        patch("pipeline.nodes.draft._llm") as mock_llm_factory,
        patch("pipeline.nodes.draft._load_prompt", return_value="mock prompt {brand_voice}"),
    ):
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        state = {
            "active_signal": sample_release_signal,
            "draft": "Long old draft text that needs editing",
            "edit_instruction": "Make it shorter",
            "qa_feedback": None,
            "qa_retries": 0,
            "run_id": "test-thread",
            "qa_result": None,
            "approval_status": None,
            "published_post_id": None,
            "error": None,
        }
        result = await draft_node(state)
        # Verify edit instruction was included in the prompt
        call_args = mock_llm.ainvoke.call_args[0][0]
        human_msg = call_args[1].content
        assert "Make it shorter" in human_msg
        assert "Long old draft text" in human_msg
