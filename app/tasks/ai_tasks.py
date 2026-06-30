# Task 1 Updated/app/tasks/ai_tasks.py
"""
tasks/ai_tasks.py  –  Background task runner for AI predictions.

Uses asyncio.Queue to serialize/throttle AI calls so we never overwhelm the
API, even under load. This queue/worker/backoff pattern is preserved from
the original HealthPredict backend's tasks/ai_tasks.py.

Gender is fixed to "not specified" since this simplified system does not
collect gender — get_health_prediction()/the prompt builder are otherwise
untouched (see services/ai_service.py).
"""
import asyncio
import logging
from uuid import UUID

from sqlalchemy import select

from app.db.connection import AsyncSessionLocal
from app.models.models import Application, AIStatus
from app.services.ai_service import get_health_prediction
from app.services.risk_service import compute_risk_tag, build_fallback_remark

logger = logging.getLogger(__name__)

# ── In-process queue ───────────────────────────────────────────────────────────
# In production, replace with Celery + Redis for true multi-process distribution.
_queue: asyncio.Queue = asyncio.Queue()
_worker_started = False


async def _worker():
    """Continuously processes AI jobs from the queue."""
    logger.info("AI task worker started.")
    while True:
        job = await _queue.get()
        app_id: UUID = job["app_id"]
        try:
            await _process_ai_job(app_id)
        except Exception as e:
            logger.error(f"AI job failed for {app_id}: {e}")
        finally:
            _queue.task_done()


async def _process_ai_job(app_id: UUID):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Application).where(Application.id == app_id))
        app = result.scalar_one_or_none()
        if not app:
            # Row may not be visible yet if the creating transaction hasn't committed.
            for attempt in range(1, 6):
                await asyncio.sleep(0.5 * attempt)
                result = await db.execute(select(Application).where(Application.id == app_id))
                app = result.scalar_one_or_none()
                if app:
                    break
            else:
                logger.warning(f"Application {app_id} not found after retries — skipping.")
                return

        glucose, hb, chol = float(app.glucose), float(app.haemoglobin), float(app.cholesterol)

        try:
            remark = await get_health_prediction(
                glucose=glucose,
                haemoglobin=hb,
                cholesterol=chol,
                age=app.age_at_submission,
                gender="not specified",
            )
            await db.refresh(app)
            app.remarks = remark
            app.remarks_is_fallback = False
            app.ai_status = AIStatus.done
            app.risk_tag = compute_risk_tag(glucose, hb, chol)
            await db.commit()
            logger.info(f"AI remark saved for application {app_id}")

        except Exception as e:
            logger.error(f"AI prediction error for {app_id}: {e}")
            await db.refresh(app)
            app.remarks = build_fallback_remark(glucose, hb, chol)
            app.remarks_is_fallback = True
            app.ai_status = AIStatus.done
            app.risk_tag = compute_risk_tag(glucose, hb, chol)
            await db.commit()


async def enqueue_ai_job(app_id: UUID):
    """Add a new AI prediction job to the queue."""
    await _queue.put({"app_id": app_id})
    logger.info(f"AI job enqueued for application {app_id}. Queue size: {_queue.qsize()}")


async def start_worker():
    """Start the background worker (call once at app startup)."""
    global _worker_started
    if not _worker_started:
        asyncio.create_task(_worker())
        _worker_started = True
        logger.info("AI background worker initialised.")
