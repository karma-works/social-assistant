"""GitHub API client — thin httpx wrapper, no PyGitHub dependency."""
from datetime import datetime, timezone
from typing import Any

import httpx

from pipeline.settings import get_settings

_BASE = "https://api.github.com"


def _headers() -> dict[str, str]:
    token = get_settings().github_token
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def get_latest_release(repo: str) -> dict | None:
    """Return the latest non-prerelease release, or None."""
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{_BASE}/repos/{repo}/releases/latest",
            headers=_headers(),
            timeout=10,
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        data = r.json()
        if data.get("prerelease") or data.get("draft"):
            return None
        return {
            "release_id": str(data["id"]),
            "tag": data["tag_name"],
            "name": data["name"] or data["tag_name"],
            "body": (data.get("body") or "")[:2000],
            "published_at": data["published_at"],
            "html_url": data["html_url"],
        }


async def get_repo_stars(repo: str) -> int | None:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{_BASE}/repos/{repo}",
            headers=_headers(),
            timeout=10,
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()["stargazers_count"]


async def get_repo_info(repo: str) -> dict | None:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{_BASE}/repos/{repo}",
            headers=_headers(),
            timeout=10,
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        d = r.json()
        return {
            "name": d["name"],
            "full_name": d["full_name"],
            "description": d.get("description") or "",
            "stars": d["stargazers_count"],
            "language": d.get("language") or "",
            "topics": d.get("topics", []),
            "html_url": d["html_url"],
            "created_at": d["created_at"],
            "pushed_at": d.get("pushed_at"),
        }


async def get_readme(repo: str) -> str:
    """Return decoded README text (first 3000 chars), or empty string."""
    import base64
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{_BASE}/repos/{repo}/readme",
            headers=_headers(),
            timeout=10,
        )
        if r.status_code == 404:
            return ""
        r.raise_for_status()
        data = r.json()
        if data.get("encoding") == "base64":
            return base64.b64decode(data["content"]).decode("utf-8", errors="replace")[:3000]
        return ""


async def list_user_repos(user: str, since: datetime | None = None) -> list[dict]:
    """Return public repos for a user, optionally filtered by creation date."""
    params: dict[str, Any] = {"type": "public", "sort": "created", "per_page": 30}
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{_BASE}/users/{user}/repos",
            headers=_headers(),
            params=params,
            timeout=10,
        )
        r.raise_for_status()
        repos = r.json()
        if since:
            repos = [
                repo for repo in repos
                if datetime.fromisoformat(repo["created_at"].replace("Z", "+00:00")) > since
            ]
        return repos
