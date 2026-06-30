# HealthChecker/app/api/routes/applications.py
"""
api/routes/applications.py  –  Application CRUD endpoints (no auth, single page app).
"""
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.connection import get_db
from app.models.models import Application, AIStatus, RiskTag
from app.schemas.schemas import ApplicationCreate, ApplicationUpdate, ApplicationResponse, PaginatedApplications
from app.tasks.ai_tasks import enqueue_ai_job

router = APIRouter(prefix="/applications", tags=["applications"])
logger = logging.getLogger(__name__)


def _calc_age(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


async def _make_app_ref(db: AsyncSession) -> str:
    count_result = await db.execute(select(func.count()).select_from(Application))
    count = count_result.scalar_one()
    return f"APP-{count + 1:06d}"


@router.post("/", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(payload: ApplicationCreate, db: AsyncSession = Depends(get_db)):
    age = _calc_age(payload.date_of_birth)
    app = Application(
        app_ref=await _make_app_ref(db),
        full_name=payload.full_name,
        date_of_birth=payload.date_of_birth,
        email=payload.email,
        glucose=payload.glucose,
        haemoglobin=payload.haemoglobin,
        cholesterol=payload.cholesterol,
        age_at_submission=age,
        ai_status=AIStatus.processing,
    )
    db.add(app)
    await db.flush()
    await db.refresh(app)
    await enqueue_ai_job(app.id)
    return app


@router.get("/", response_model=PaginatedApplications)
async def list_applications(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=500),
    search: Optional[str] = Query(None, description="Matches name or email, not limited by current page"),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    remarks_type: Optional[str] = Query(None, pattern="^(ai|manual)$"),
    risk_tag: Optional[RiskTag] = Query(None),
    sort: str = Query("newest", pattern="^(newest|oldest|name)$"),
):
    filters = []
    if search:
        like = f"%{search.strip()}%"
        filters.append(or_(Application.full_name.ilike(like), Application.email.ilike(like)))
    if date_from:
        filters.append(Application.created_at >= datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc))
    if date_to:
        filters.append(Application.created_at < datetime.combine(date_to + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc))
    if remarks_type == "ai":
        filters.append(Application.remarks_is_fallback.is_(False))
    elif remarks_type == "manual":
        filters.append(Application.remarks_is_fallback.is_(True))
    if risk_tag:
        filters.append(Application.risk_tag == risk_tag)

    base_stmt = select(Application)
    count_stmt = select(func.count()).select_from(Application)
    if filters:
        base_stmt = base_stmt.where(and_(*filters))
        count_stmt = count_stmt.where(and_(*filters))

    total = (await db.execute(count_stmt)).scalar_one()

    if sort == "oldest":
        base_stmt = base_stmt.order_by(Application.created_at.asc())
    elif sort == "name":
        base_stmt = base_stmt.order_by(Application.full_name.asc())
    else:
        base_stmt = base_stmt.order_by(Application.created_at.desc())

    base_stmt = base_stmt.offset((page - 1) * page_size).limit(page_size)
    items = (await db.execute(base_stmt)).scalars().all()

    total_pages = max(1, (total + page_size - 1) // page_size)
    return PaginatedApplications(items=items, total=total, page=page, page_size=page_size, total_pages=total_pages)


@router.get("/{app_id}", response_model=ApplicationResponse)
async def get_application(app_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Application).where(Application.id == app_id))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found.")
    return app


@router.put("/{app_id}", response_model=ApplicationResponse)
async def update_application(app_id: UUID, payload: ApplicationUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Application).where(Application.id == app_id))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found.")

    app.full_name = payload.full_name
    app.date_of_birth = payload.date_of_birth
    app.email = payload.email
    app.glucose = payload.glucose
    app.haemoglobin = payload.haemoglobin
    app.cholesterol = payload.cholesterol
    app.age_at_submission = _calc_age(payload.date_of_birth)

    # Editing invalidates the previous remark/tag — recompute via AI + rule engine
    app.remarks = None
    app.remarks_is_fallback = False
    app.risk_tag = None
    app.ai_status = AIStatus.processing
    await db.flush()
    await db.refresh(app)

    await enqueue_ai_job(app.id)
    return app


@router.delete("/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application(app_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Application).where(Application.id == app_id))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found.")
    await db.delete(app)
