"""Bluesky publishing via atproto SDK."""
from atproto import AsyncClient

from pipeline.settings import get_settings

_client: AsyncClient | None = None


async def _get_client() -> AsyncClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncClient()
        await _client.login(settings.bluesky_handle, settings.bluesky_password)
    return _client


async def post(text: str) -> str:
    """
    Publish text to Bluesky. Handles thread (posts separated by '---').
    Returns the URI of the first post.
    """
    client = await _get_client()
    parts = [p.strip() for p in text.split("---") if p.strip()]

    if not parts:
        raise ValueError("Empty post text")

    root_uri: str | None = None
    root_cid: str | None = None
    reply_ref = None

    for i, part in enumerate(parts):
        if len(part) > 300:
            part = part[:297] + "…"

        if i == 0:
            response = await client.send_post(text=part)
            root_uri = response.uri
            root_cid = response.cid
        else:
            response = await client.send_post(
                text=part,
                reply_to={
                    "root": {"uri": root_uri, "cid": root_cid},
                    "parent": {"uri": reply_ref["uri"], "cid": reply_ref["cid"]},
                },
            )
        reply_ref = {"uri": response.uri, "cid": response.cid}

    return root_uri  # type: ignore[return-value]
