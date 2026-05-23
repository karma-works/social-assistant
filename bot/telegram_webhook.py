"""FastAPI app — Telegram webhook receiver (ADR-007)."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from langgraph.types import Command
from telegram import Bot, Update
from telegram.ext import Application

from bot import direct_post
from pipeline import db
from pipeline.graph import get_persistent_graph
from pipeline.settings import get_settings

logger = logging.getLogger(__name__)

_graph = None
_app: Application | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _graph, _app
    settings = get_settings()

    async with get_persistent_graph() as graph:
        _graph = graph

        # Build Telegram application (for update parsing only — no polling)
        _app = Application.builder().token(settings.telegram_bot_token).build()
        await _app.initialize()

        yield

        if _app:
            await _app.shutdown()


api = FastAPI(lifespan=lifespan)


@api.post("/telegram/webhook")
async def telegram_webhook(request: Request) -> Response:
    settings = get_settings()
    data = await request.json()
    update = Update.de_json(data, Bot(token=settings.telegram_bot_token))

    # ---------- Inline keyboard button press ----------
    if update.callback_query:
        query = update.callback_query
        await query.answer()

        callback_data = query.data or ""

        # --- Direct post platform selection ---
        if callback_data.startswith("direct:"):
            _, pending_id, platform = callback_data.split(":", 2)
            if platform == "cancel":
                await db.delete_direct_post(pending_id)
                await query.edit_message_text("Cancelled.")
            else:
                await direct_post.handle_publish_callback(
                    pending_id, platform, query.edit_message_text
                )
            return Response(status_code=200)

        # --- Pipeline approval flow ---
        parts = callback_data.split(":", 1)
        if len(parts) != 2:
            return Response(status_code=200)

        thread_id, action = parts[0], parts[1]

        if action in ("approved", "rejected", "regenerate"):
            await _resume_graph(thread_id, {"action": action})
            await query.edit_message_text(f"Got it — {action}.")

        elif action == "edit":
            # Store that we're waiting for edit text for this thread
            await db.save_thread(f"edit_pending:{thread_id}", thread_id)
            await query.edit_message_text(
                "Send me your correction as a reply and I'll regenerate the draft."
            )

    # ---------- Text message ----------
    elif update.message and update.message.text:
        text = update.message.text

        # If there's a pending edit for a pipeline thread, route there first
        thread_id = await _find_pending_edit_thread()
        if thread_id:
            await _resume_graph(thread_id, {"action": "edit", "instruction": text})
            await update.message.reply_text("Draft regeneration started!")
            await db.update_signal_status(f"edit_pending:{thread_id}", "discarded")
        else:
            # Direct post: show platform preview
            await direct_post.handle_incoming_message(text, update.message.reply_text)

    return Response(status_code=200)


async def _resume_graph(thread_id: str, user_input: dict) -> None:
    try:
        await _graph.ainvoke(
            Command(resume=user_input),
            config={"configurable": {"thread_id": thread_id}},
        )
    except Exception:
        logger.exception("Error resuming graph for thread %s", thread_id)


async def _find_pending_edit_thread() -> str | None:
    # Look for threads with 'edit_pending:' prefix in the threads table
    from pipeline import db as _db
    async with _db.get_conn() as conn:
        row = await conn.execute(
            """
            SELECT thread_id FROM threads
            WHERE thread_id LIKE 'edit_pending:%'
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
        result = await row.fetchone()
        if result:
            return result["thread_id"].removeprefix("edit_pending:")
        return None
