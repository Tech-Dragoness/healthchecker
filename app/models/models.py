# Task 1 Updated/app/models/models.py
"""
models/models.py  –  SQLAlchemy ORM model for HealthChecker.

Single-table, no auth / no roles — just blood-test applications.
"""
import uuid
import enum
from sqlalchemy import (
    Column, String, Enum, DateTime, Date, Numeric, Integer, Boolean, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.connection import Base


class AIStatus(str, enum.Enum):
    processing = "processing"
    done = "done"


class RiskTag(str, enum.Enum):
    normal = "normal"
    slightly_abnormal = "slightly_abnormal"
    high = "high"


class Application(Base):
    __tablename__ = "applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    app_ref = Column(String(20), unique=True, nullable=False)  # e.g. APP-000001

    # Patient identity (collected directly on this simplified system — no user accounts)
    full_name = Column(String(120), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    email = Column(String(255), nullable=False, index=True)

    # Blood test values
    glucose = Column(Numeric(8, 2), nullable=False)
    haemoglobin = Column(Numeric(8, 2), nullable=False)
    cholesterol = Column(Numeric(8, 2), nullable=False)

    # Derived at submission/edit time
    age_at_submission = Column(Integer, nullable=False)

    # AI remark
    ai_status = Column(Enum(AIStatus, name="ai_status", create_type=False), nullable=False, default=AIStatus.processing)
    remarks = Column(Text, nullable=True)
    remarks_is_fallback = Column(Boolean, nullable=False, default=False)  # True = non-AI auto remark (AI failed)

    # Rule-based risk classification — NEVER taken from the AI's own output
    risk_tag = Column(Enum(RiskTag, name="risk_tag", create_type=False), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
