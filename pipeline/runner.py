"""Daily pipeline runner — called by Cloud Scheduler (or locally for dev)."""
import asyncio
import logging
from uuid import uuid4

from pipeline import db
from pipeline.graph import get_graph
from pipeline.nodes.dedup import deduplicate_signals
from pipeline.nodes.ingest_github import ingest_github_signals

logger = logging.getLogger(__name__)


async def run_daily() -> None:
    """Ingest signals, deduplicate, and start a LangGraph thread per signal."""
    logger.info("Daily pipeline run started")

    # 1. Ingest
    raw_signals = await ingest_github_signals()
    logger.info("Ingested %d raw signals", len(raw_signals))

    # 2. Deduplicate
    signals = await deduplicate_signals(raw_signals)
    logger.info("%d signals after dedup", len(signals))

    # Also pick up any pending signals that never had a thread started (e.g. after a crash)
    unstarted = await db.get_pending_unstarted_signals()
    seen_ids = {s["id"] for s in signals}
    for s in unstarted:
        if s["id"] not in seen_ids:
            signals.append(s)
    logger.info("%d signals to process (including %d recovered)", len(signals), len(unstarted))

    if not signals:
        logger.info("No new signals — done")
        return

    # 3. Start a per-signal LangGraph thread (runs until interrupt)
    async with get_graph() as graph:
        for signal in signals:
            thread_id = str(uuid4())
            await db.save_thread(thread_id, signal["id"])
            logger.info(
                "Starting thread %s for signal %s (%s)",
                thread_id, signal["id"], signal["source"],
            )
            try:
                await graph.ainvoke(
                    {
                        "run_id": thread_id,
                        "active_signal": signal,
                        "draft": None,
                        "qa_result": None,
                        "qa_retries": 0,
                        "qa_feedback": None,
                        "approval_status": None,
                        "edit_instruction": None,
                        "published_post_id": None,
                        "error": None,
                    },
                    config={"configurable": {"thread_id": thread_id}},
                )
                # Graph suspends at interrupt() in telegram_send_node — that's expected
            except Exception:
                logger.exception("Pipeline error for signal %s — will retry next run", signal["id"])

    logger.info("Daily run complete — %d threads started", len(signals))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_daily())
