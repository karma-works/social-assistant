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

    if not signals:
        logger.info("No new signals — done")
        return

    # 3. Start a per-signal LangGraph thread (runs until interrupt)
    graph = await get_graph()

    for signal in signals:
        thread_id = str(uuid4())
        await db.save_thread(thread_id, signal["id"])
        logger.info("Starting thread %s for signal %s (%s)", thread_id, signal["id"], signal["source"])
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
            logger.exception("Pipeline error for signal %s", signal["id"])
            await db.update_signal_status(signal["id"], "discarded")

    logger.info("Daily run complete — %d threads started", len(signals))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_daily())
