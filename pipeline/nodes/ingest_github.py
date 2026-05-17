"""GitHub ingestion — detects post-worthy signals per ADR-009."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from pipeline import db
from pipeline.settings import get_config, get_settings
from pipeline.state import Signal
from pipeline.tools import github_api


async def ingest_github_signals() -> list[Signal]:
    """
    Poll all tracked repos and users for new signals.
    Returns a flat list of Signal dicts ready for dedup.
    """
    config = get_config()
    signals: list[Signal] = []

    all_repos: set[str] = set(config.tracked_repos)

    # Expand tracked users → their repos
    for user in config.tracked_users:
        known = await db.known_repos(user)
        user_repos = await github_api.list_user_repos(user)
        for r in user_repos:
            all_repos.add(r["full_name"])
            # Check for new repo signal
            if r["full_name"] not in known:
                sig = await _new_repo_signal(r["full_name"])
                if sig:
                    signals.append(sig)

    # Check each repo for releases and star jumps
    for repo in all_repos:
        release_sig = await _release_signal(repo)
        if release_sig:
            signals.append(release_sig)

        star_sig = await _star_signal(repo)
        if star_sig:
            signals.append(star_sig)

    return signals


async def _release_signal(repo: str) -> Signal | None:
    """Return a signal if a new release was published since last seen."""
    latest = await github_api.get_latest_release(repo)
    if not latest:
        return None

    last_seen = await db.get_last_release_id(repo)
    if latest["release_id"] == last_seen:
        return None

    info = await github_api.get_repo_info(repo)
    return Signal(
        id=f"release-{repo.replace('/', '-')}-{latest['release_id']}",
        source="github_release",
        repo=repo,
        topic_summary=None,  # filled by dedup node
        raw_data={
            "release_id": latest["release_id"],
            "tag": latest["tag"],
            "name": latest["name"],
            "body": latest["body"],
            "published_at": latest["published_at"],
            "html_url": latest["html_url"],
            "stars": info["stars"] if info else 0,
            "description": info["description"] if info else "",
        },
        detected_at=datetime.now(timezone.utc).isoformat(),
    )


async def _star_signal(repo: str) -> Signal | None:
    """Return a signal if star count crossed a threshold (ADR-009)."""
    config = get_config()

    # Check cooldown
    days_since = await db.get_days_since_last_star_post(repo)
    if days_since is not None and days_since < config.star_cooldown_days:
        return None

    current_stars = await github_api.get_repo_stars(repo)
    if current_stars is None:
        return None

    last = await db.get_last_star_count(repo)
    now_str = datetime.now(timezone.utc).isoformat()

    if last is None:
        # First time seeing this repo — store baseline, no signal yet
        await db.save_signal(
            Signal(
                id=f"stars-baseline-{repo.replace('/', '-')}",
                source="github_stars",
                repo=repo,
                topic_summary=None,
                raw_data={"stars": current_stars, "checked_at": now_str},
                detected_at=now_str,
            )
        )
        return None

    prev_count = last["count"]
    prev_dt = datetime.fromisoformat(last["checked_at"])
    hours_elapsed = (datetime.now(timezone.utc) - prev_dt).total_seconds() / 3600

    # Absolute jump in 24h
    abs_jump = hours_elapsed <= 24 and (current_stars - prev_count) >= config.star_jump_abs_24h
    # Percentage jump in 7 days
    pct_jump = (
        hours_elapsed <= 24 * 7
        and prev_count > 0
        and ((current_stars - prev_count) / prev_count * 100) >= config.star_jump_pct_7d
    )

    if not (abs_jump or pct_jump):
        return None

    info = await github_api.get_repo_info(repo)
    return Signal(
        id=f"stars-{repo.replace('/', '-')}-{int(datetime.now(timezone.utc).timestamp())}",
        source="github_stars",
        repo=repo,
        topic_summary=None,
        raw_data={
            "stars": current_stars,
            "prev_stars": prev_count,
            "delta": current_stars - prev_count,
            "checked_at": now_str,
            "description": info["description"] if info else "",
            "html_url": f"https://github.com/{repo}",
        },
        detected_at=now_str,
    )


async def _new_repo_signal(repo: str) -> Signal | None:
    """Return a signal for a newly created repo if it has README + description."""
    info = await github_api.get_repo_info(repo)
    if not info:
        return None
    if not info["description"]:
        return None

    readme = await github_api.get_readme(repo)
    if not readme.strip():
        return None

    return Signal(
        id=f"newrepo-{repo.replace('/', '-')}",
        source="github_new_repo",
        repo=repo,
        topic_summary=None,
        raw_data={
            "name": info["name"],
            "description": info["description"],
            "readme_excerpt": readme[:1500],
            "stars": info["stars"],
            "language": info["language"],
            "topics": info["topics"],
            "html_url": info["html_url"],
        },
        detected_at=datetime.now(timezone.utc).isoformat(),
    )
