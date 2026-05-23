"""User-initiated direct posts: Telegram message → preview → publish."""
import logging
import uuid
from typing import Awaitable, Callable

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message

from pipeline import db
from pipeline.settings import get_config
from pipeline.tools import bluesky_api, x_api
from pipeline.tools.gemini_shorten import shorten_for_x

logger = logging.getLogger(__name__)

_BLUESKY_LIMIT = 300
_X_LIMIT = 280


async def handle_incoming_message(text: str, reply: Callable[..., Awaitable[Message]]) -> None:
    """Build a platform preview and ask the user where to publish."""
    text = text.strip()

    bluesky_text = text if len(text) <= _BLUESKY_LIMIT else text[: _BLUESKY_LIMIT - 1] + "…"
    x_text = await shorten_for_x(text, _X_LIMIT)

    pending_id = str(uuid.uuid4())[:12]
    await db.save_direct_post(pending_id, bluesky_text, x_text)

    bsky_note = " _(shortened)_" if len(text) > _BLUESKY_LIMIT else ""
    x_note = " _(AI shortened)_" if len(text) > _X_LIMIT else ""

    preview = (
        "*Preview*\n\n"
        f"🦋 *Bluesky* ({len(bluesky_text)} chars){bsky_note}\n"
        f"```\n{bluesky_text}\n```\n\n"
        f"𝕏 *X* ({len(x_text)} chars){x_note}\n"
        f"```\n{x_text}\n```\n\n"
        "*Where do you want to publish?*"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🦋 Bluesky", callback_data=f"direct:{pending_id}:bluesky"),
            InlineKeyboardButton("𝕏 X", callback_data=f"direct:{pending_id}:x"),
        ],
        [
            InlineKeyboardButton("✅ Both", callback_data=f"direct:{pending_id}:both"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"direct:{pending_id}:cancel"),
        ],
    ])

    await reply(preview, parse_mode="Markdown", reply_markup=keyboard)


async def handle_publish_callback(
    pending_id: str,
    platform: str,
    edit_message: Callable[..., Awaitable],
) -> None:
    """Publish to the chosen platform(s) and update the preview message."""
    post = await db.get_direct_post(pending_id)
    if not post:
        await edit_message("Post not found — please resend your message.")
        return

    config = get_config()
    results: list[str] = []

    try:
        if platform in ("bluesky", "both") and config.platforms.get("bluesky", {}).get("enabled", True):
            post_uri = await bluesky_api.post(post["bluesky_text"])
            await db.save_post(
                signal_id=None,
                platform="bluesky",
                topic_summary="direct",
                content=post["bluesky_text"],
                platform_post_id=post_uri,
            )
            results.append(f"🦋 Bluesky: {post_uri}")

        if platform in ("x", "both") and config.platforms.get("x", {}).get("enabled", True):
            tweet_id = await x_api.post(post["x_text"])
            await db.save_post(
                signal_id=None,
                platform="x",
                topic_summary="direct",
                content=post["x_text"],
                platform_post_id=tweet_id,
            )
            results.append(f"𝕏 X: https://x.com/i/web/status/{tweet_id}")
    except Exception:
        logger.exception("Failed to publish direct post %s", pending_id)
        await edit_message("Publishing failed — check logs.")
        return
    finally:
        await db.delete_direct_post(pending_id)

    if results:
        await edit_message("Published!\n" + "\n".join(results))
    else:
        await edit_message("No platforms are enabled — check config.yaml.")
