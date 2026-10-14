import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.core.config import settings
from app.core.database import SessionLocal
from app.services.reminder import process_pending_reminders

logger = logging.getLogger("medislot.scheduler")

scheduler = BackgroundScheduler(daemon=True)

def scheduled_reminder_worker():
    """Periodic job that inspects the reminder_jobs ledger and dispatches due reminders."""
    db = SessionLocal()
    try:
        count = process_pending_reminders(db)
        if count > 0:
            logger.info(f"APScheduler: Dispatched {count} due reminder notifications.")
    except Exception as ex:
        logger.error(f"APScheduler error in scheduled_reminder_worker: {ex}")
    finally:
        db.close()

def start_scheduler():
    """Initializes and starts the APScheduler background thread."""
    if not settings.ENABLE_SCHEDULER:
        logger.info("APScheduler is disabled via configuration.")
        return

    if not scheduler.running:
        # Check every 30 seconds for due reminders
        scheduler.add_job(
            func=scheduled_reminder_worker,
            trigger=IntervalTrigger(seconds=30),
            id="medislot_process_reminders",
            name="Process Pending Appointment Reminders",
            replace_existing=True
        )
        scheduler.start()
        logger.info("APScheduler started successfully for MediSlot background jobs.")

def stop_scheduler():
    """Gracefully shuts down the background scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped.")

def trigger_pending_reminders_now() -> int:
    """Manually triggers immediate execution of due reminders (useful for APIs and tests)."""
    db = SessionLocal()
    try:
        return process_pending_reminders(db)
    finally:
        db.close()
