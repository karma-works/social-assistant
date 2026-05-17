"""Tests for GitHub ingestion signal detection logic."""
import pytest
from unittest.mock import AsyncMock, patch
from pipeline.nodes.ingest_github import _release_signal, _star_signal


@pytest.mark.asyncio
async def test_release_signal_new_release():
    with (
        patch("pipeline.nodes.ingest_github.github_api.get_latest_release", new_callable=AsyncMock) as mock_release,
        patch("pipeline.nodes.ingest_github.github_api.get_repo_info", new_callable=AsyncMock) as mock_info,
        patch("pipeline.nodes.ingest_github.db.get_last_release_id", new_callable=AsyncMock) as mock_last,
    ):
        mock_release.return_value = {
            "release_id": "999",
            "tag": "v2.0.0",
            "name": "v2.0.0",
            "body": "Big release",
            "published_at": "2026-05-17T08:00:00Z",
            "html_url": "https://github.com/owner/repo/releases/tag/v2.0.0",
        }
        mock_info.return_value = {"stars": 500, "description": "A tool"}
        mock_last.return_value = "888"  # different from latest

        signal = await _release_signal("owner/repo")

        assert signal is not None
        assert signal["source"] == "github_release"
        assert signal["raw_data"]["tag"] == "v2.0.0"


@pytest.mark.asyncio
async def test_release_signal_already_seen():
    with (
        patch("pipeline.nodes.ingest_github.github_api.get_latest_release", new_callable=AsyncMock) as mock_release,
        patch("pipeline.nodes.ingest_github.db.get_last_release_id", new_callable=AsyncMock) as mock_last,
    ):
        mock_release.return_value = {"release_id": "999", "tag": "v2.0.0", "name": "v2.0.0",
                                     "body": "", "published_at": "2026-05-17T08:00:00Z",
                                     "html_url": ""}
        mock_last.return_value = "999"  # same → no signal

        signal = await _release_signal("owner/repo")
        assert signal is None


@pytest.mark.asyncio
async def test_star_signal_abs_jump():
    from pipeline.settings import AppConfig
    mock_config = AppConfig.__new__(AppConfig)
    mock_config.star_jump_pct_7d = 50
    mock_config.star_jump_abs_24h = 100
    mock_config.star_cooldown_days = 30
    mock_config.pipeline = {}

    with (
        patch("pipeline.nodes.ingest_github.get_config", return_value=mock_config),
        patch("pipeline.nodes.ingest_github.db.get_days_since_last_star_post", new_callable=AsyncMock, return_value=None),
        patch("pipeline.nodes.ingest_github.github_api.get_repo_stars", new_callable=AsyncMock, return_value=1500),
        patch("pipeline.nodes.ingest_github.db.get_last_star_count", new_callable=AsyncMock) as mock_last,
        patch("pipeline.nodes.ingest_github.github_api.get_repo_info", new_callable=AsyncMock, return_value={"description": "A tool", "html_url": ""}),
    ):
        from datetime import datetime, timedelta, timezone
        mock_last.return_value = {
            "count": 1350,  # delta = 150 > 100 threshold
            "checked_at": (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat(),
        }
        signal = await _star_signal("owner/repo")
        assert signal is not None
        assert signal["source"] == "github_stars"
        assert signal["raw_data"]["delta"] == 150
