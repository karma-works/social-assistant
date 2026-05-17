import pytest
from pipeline.state import Signal
from datetime import datetime, timezone


@pytest.fixture
def sample_release_signal() -> Signal:
    return Signal(
        id="release-owner-repo-12345",
        source="github_release",
        repo="owner/repo",
        topic_summary="owner/repo v1.2.0 release",
        raw_data={
            "release_id": "12345",
            "tag": "v1.2.0",
            "name": "v1.2.0 - Bug fixes and performance",
            "body": "- Fixed memory leak\n- 2x faster inference\n- New CLI flag --verbose",
            "published_at": "2026-05-17T08:00:00Z",
            "html_url": "https://github.com/owner/repo/releases/tag/v1.2.0",
            "stars": 1200,
            "description": "A fast inference engine for language models",
        },
        detected_at=datetime.now(timezone.utc).isoformat(),
    )


@pytest.fixture
def sample_stars_signal() -> Signal:
    return Signal(
        id="stars-owner-repo-1234567890",
        source="github_stars",
        repo="owner/repo",
        topic_summary="owner/repo star jump +150 stars",
        raw_data={
            "stars": 1500,
            "prev_stars": 1200,
            "delta": 300,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "description": "A fast inference engine for language models",
            "html_url": "https://github.com/owner/repo",
        },
        detected_at=datetime.now(timezone.utc).isoformat(),
    )
