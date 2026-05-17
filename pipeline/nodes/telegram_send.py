"""Telegram approval node — sends draft and suspends via LangGraph interrupt (ADR-007)."""
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

from langgraph.types import interrupt

from pipeline.settings import get_settings
from pipeline.state import PipelineState, QAResult


def _bot() -> Bot:
    return Bot(token=get_settings().telegram_bot_token)


def _build_message(state: PipelineState) -> str:
    signal = state["active_signal"]
    qa: QAResult | None = state.get("qa_result")

    header = f"📋 *New draft — {signal['source']} / {signal['repo']}*\n\n"
    body = (
        f"🦋 *Bluesky* ({len(state.get('draft') or '')} chars)\n"
        f"```\n{state.get('draft', '')}\n```\n\n"
        f"𝕏 *X / Twitter* ({len(state.get('x_draft') or '')} chars)\n"
        f"```\n{state.get('x_draft', '')}\n```"
    )

    if qa and qa["overall"] == "warn":
        issues = "\n".join(f"• {i}" for i in qa["style_issues"])
        body += f"\n\n⚠️ *QA warnings:*\n{issues}"

    return header + body


def _build_keyboard(thread_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"{thread_id}:approved"),
            InlineKeyboardButton("❌ Reject", callback_data=f"{thread_id}:rejected"),
        ],
        [
            InlineKeyboardButton("✏️ Edit", callback_data=f"{thread_id}:edit"),
            InlineKeyboardButton("🔄 Regenerate", callback_data=f"{thread_id}:regenerate"),
        ],
    ])


async def telegram_send_node(state: PipelineState) -> dict:
    settings = get_settings()
    bot = _bot()

    thread_id = state["run_id"]
    await bot.send_message(
        chat_id=settings.telegram_chat_id,
        text=_build_message(state),
        parse_mode="Markdown",
        reply_markup=_build_keyboard(thread_id),
    )

    # Suspend here — resumes when webhook calls Command(resume=...)
    user_input: dict = interrupt({"thread_id": thread_id, "status": "waiting_for_approval"})

    return {
        "approval_status": user_input["action"],
        "edit_instruction": user_input.get("instruction"),
    }


def route_after_approval(state: PipelineState) -> str:
    from langgraph.graph import END
    match state.get("approval_status"):
        case "approved":
            return "publish"
        case "edit" | "regenerate":
            return "draft"
        case _:
            return END  # rejected or unknown
