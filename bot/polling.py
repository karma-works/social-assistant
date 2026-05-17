"""Telegram polling bot — local dev alternative to the webhook server."""
import asyncio
import logging

from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes, MessageHandler, filters

from langgraph.types import Command

from pipeline import db
from pipeline.graph import get_persistent_graph
from pipeline.settings import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_graph = None


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()

    parts = query.data.split(":", 1)
    if len(parts) != 2:
        return

    thread_id, action = parts[0], parts[1]

    if action in ("approved", "rejected", "regenerate"):
        await query.edit_message_text(f"Got it — {action}.")
        await _resume(thread_id, {"action": action})

    elif action == "edit":
        await db.save_thread(f"edit_pending:{thread_id}", thread_id)
        await query.edit_message_text(
            "Send me your correction as a text message and I'll regenerate the draft."
        )


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    text = update.message.text
    if text.startswith("/"):
        await update.message.reply_text("Bot is running. Waiting for draft approvals.")
        return

    thread_id = await _find_pending_edit_thread()
    if thread_id:
        await update.message.reply_text("Draft regeneration started!")
        await db.update_signal_status(f"edit_pending:{thread_id}", "discarded")
        await _resume(thread_id, {"action": "edit", "instruction": text})
    else:
        await update.message.reply_text("No pending edit found. Use the buttons on the draft message.")


async def _resume(thread_id: str, user_input: dict) -> None:
    try:
        await _graph.ainvoke(
            Command(resume=user_input),
            config={"configurable": {"thread_id": thread_id}},
        )
    except Exception:
        logger.exception("Error resuming graph for thread %s", thread_id)


async def _find_pending_edit_thread() -> str | None:
    async with db.get_conn() as conn:
        row = await conn.execute(
            "SELECT thread_id FROM threads WHERE thread_id LIKE 'edit_pending:%' ORDER BY created_at DESC LIMIT 1"
        )
        result = await row.fetchone()
        if result:
            return result["thread_id"].removeprefix("edit_pending:")
        return None


async def main() -> None:
    global _graph
    settings = get_settings()

    async with get_persistent_graph() as graph:
        _graph = graph
        logger.info("Graph ready. Starting Telegram polling…")

        app = Application.builder().token(settings.telegram_bot_token).build()
        app.add_handler(CallbackQueryHandler(on_button))
        app.add_handler(MessageHandler(filters.TEXT, on_text))

        async with app:
            await app.start()
            await app.updater.start_polling(drop_pending_updates=True)
            logger.info("Polling started — press Ctrl+C to stop")
            # Run until interrupted
            stop_event = asyncio.Event()
            try:
                await stop_event.wait()
            except (KeyboardInterrupt, asyncio.CancelledError):
                pass
            finally:
                await app.updater.stop()
                await app.stop()


if __name__ == "__main__":
    asyncio.run(main())
