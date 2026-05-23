"""APScheduler daily pipeline trigger.

Run with:
    python -m src.scheduler.cron

Schedule:   CronTrigger from settings.scheduler_cron ("0 7 * * 1-5" by default)
            in settings.scheduler_timezone ("Africa/Luanda" by default).
            Fires Mon–Fri at 07:00 WAT.

On any unhandled exception the WhatsApp approver receives an alert and the
exception is re-raised so the scheduler logs it properly.
"""

import asyncio
import logging
import signal
import uuid

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config.settings import settings
from src.orchestrator.graph import run_graph
from src.tools.whatsapp import send_text

logger = logging.getLogger(__name__)


async def run_daily_pipeline() -> None:
    """Execute the full social media agent pipeline for today's session.

    1. Generate a UUID session_id scoped to this run.
    2. Log run start.
    3. Call run_graph(session_id).
    4. Log run end with a concise state summary.
    5. On any unhandled exception: send a WhatsApp alert then re-raise.
    """
    session_id = str(uuid.uuid4())
    logger.info("Daily pipeline starting", extra={"session_id": session_id})

    try:
        state = await run_graph(session_id)
        logger.info(
            "Daily pipeline completed",
            extra={
                "session_id": session_id,
                "status": state.get("status"),
                "current_agent": state.get("current_agent"),
                "pending_approval": state.get("pending_approval"),
                "publication_count": len(state.get("publication_results", [])),
            },
        )

    except Exception as exc:
        logger.exception(
            "Daily pipeline failed — sending WhatsApp alert",
            extra={"session_id": session_id, "error": str(exc)},
        )
        try:
            await send_text(
                to=settings.revisor_approver_phone,
                message=(
                    f"⚠️ *BMST Social Agents — Erro no Pipeline*\n"
                    f"🆔 Sessão: `{session_id}`\n"
                    f"❌ Erro: {type(exc).__name__}: {str(exc)[:300]}\n\n"
                    f"O pipeline diário falhou. Verifique os logs para detalhes."
                ),
            )
        except Exception as wa_exc:
            logger.error(
                "WhatsApp alert failed after pipeline error",
                extra={"session_id": session_id, "wa_error": str(wa_exc)},
            )
        raise


def _parse_cron(cron_expr: str) -> dict:
    """Parse a 5-field cron expression into APScheduler CronTrigger keyword arguments.

    Fields (in order): minute hour day month day_of_week.
    """
    parts = cron_expr.split()
    if len(parts) != 5:
        raise ValueError(
            f"scheduler_cron must be a 5-field cron expression (got {len(parts)} fields): "
            f"{cron_expr!r}"
        )
    minute, hour, day, month, day_of_week = parts
    return {
        "minute": minute,
        "hour": hour,
        "day": day,
        "month": month,
        "day_of_week": day_of_week,
    }


async def main() -> None:
    """Start the APScheduler with the daily pipeline job and block until SIGTERM/SIGINT."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    scheduler = AsyncIOScheduler()
    cron_kwargs = _parse_cron(settings.scheduler_cron)

    scheduler.add_job(
        run_daily_pipeline,
        CronTrigger(timezone=settings.scheduler_timezone, **cron_kwargs),
        id="daily_pipeline",
        name="BMST Social Media Daily Pipeline",
        max_instances=1,       # prevent overlapping runs if one overruns
        misfire_grace_time=300,  # allow up to 5 min late start
        coalesce=True,           # if multiple misfires: run once, not N times
    )

    scheduler.start()
    logger.info(
        "Scheduler started",
        extra={
            "cron": settings.scheduler_cron,
            "timezone": settings.scheduler_timezone,
        },
    )

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _handle_signal(*_):
        logger.info("Shutdown signal received — stopping scheduler")
        scheduler.shutdown(wait=True)
        stop_event.set()

    loop.add_signal_handler(signal.SIGTERM, _handle_signal)
    loop.add_signal_handler(signal.SIGINT, _handle_signal)

    await stop_event.wait()
    logger.info("Scheduler exited cleanly")


if __name__ == "__main__":
    asyncio.run(main())
