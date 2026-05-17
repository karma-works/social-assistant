"""Publishing node — posts to Bluesky and stores in local DB (ADR-004)."""
from pipeline import db
from pipeline.settings import get_config
from pipeline.state import PipelineState
from pipeline.tools import bluesky_api


async def publish_node(state: PipelineState) -> dict:
    signal = state["active_signal"]
    draft = state["draft"]
    config = get_config()

    published_post_id: str | None = None

    if config.platforms.get("bluesky", {}).get("enabled", True):
        post_uri = await bluesky_api.post(draft)
        await db.save_post(
            signal_id=signal["id"],
            platform="bluesky",
            topic_summary=signal.get("topic_summary") or signal["repo"],
            content=draft,
            platform_post_id=post_uri,
        )
        published_post_id = post_uri

    await db.update_signal_status(signal["id"], "approved")

    return {"published_post_id": published_post_id}
