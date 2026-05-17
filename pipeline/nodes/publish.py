"""Publishing node — posts to Bluesky and X, stores results in DB."""
from pipeline import db
from pipeline.settings import get_config
from pipeline.state import PipelineState
from pipeline.tools import bluesky_api, x_api


async def publish_node(state: PipelineState) -> dict:
    signal = state["active_signal"]
    config = get_config()
    topic = signal.get("topic_summary") or signal["repo"]

    published_post_id: str | None = None

    if config.platforms.get("bluesky", {}).get("enabled", True):
        post_uri = await bluesky_api.post(state["draft"])
        await db.save_post(
            signal_id=signal["id"],
            platform="bluesky",
            topic_summary=topic,
            content=state["draft"],
            platform_post_id=post_uri,
        )
        published_post_id = post_uri

    if config.platforms.get("x", {}).get("enabled", False):
        tweet_id = await x_api.post(state["x_draft"])
        await db.save_post(
            signal_id=signal["id"],
            platform="x",
            topic_summary=topic,
            content=state["x_draft"],
            platform_post_id=tweet_id,
        )
        published_post_id = published_post_id or tweet_id

    await db.update_signal_status(signal["id"], "approved")

    return {"published_post_id": published_post_id}
