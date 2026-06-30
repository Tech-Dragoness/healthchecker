# HealthChecker/app/schemas/schemas.py
"""
schemas/schemas.py  –  Pydantic v2 request/response models.
"""
import re
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator

from app.models.models import AIStatus, RiskTag

NAME_RE = re.compile(r"^[A-Za-z\s\-]{3,120}$")


def _validate_name(v: str) -> str:
    v = v.strip()
    if not NAME_RE.match(v):
        raise ValueError(
            "Name must be at least 3 letters long and may only contain letters, spaces, or hyphens."
        )
    return v


def _validate_dob(v: date) -> date:
    if v >= date.today():
        raise ValueError("Date of birth cannot be today or a future date.")
    age_years = (date.today() - v).days / 365.25
    if age_years > 130:
        raise ValueError("Date of birth is implausibly far in the past.")
    return v


def _validate_glucose(v: float) -> float:
    if v <= 0 or v > 1000:
        raise ValueError("Glucose must be a positive number (mg/dL), typically between 50 and 500.")
    return round(v, 2)


def _validate_haemoglobin(v: float) -> float:
    if v <= 0 or v > 30:
        raise ValueError("Haemoglobin must be a positive number (g/dL), typically between 5 and 20.")
    return round(v, 2)


def _validate_cholesterol(v: float) -> float:
    if v <= 0 or v > 1000:
        raise ValueError("Cholesterol must be a positive number (mg/dL), typically between 100 and 500.")
    return round(v, 2)


class ApplicationCreate(BaseModel):
    full_name: str
    date_of_birth: date
    email: EmailStr
    glucose: float
    haemoglobin: float
    cholesterol: float

    @field_validator("full_name")
    @classmethod
    def v_name(cls, v):
        return _validate_name(v)

    @field_validator("date_of_birth")
    @classmethod
    def v_dob(cls, v):
        return _validate_dob(v)

    @field_validator("glucose")
    @classmethod
    def v_glucose(cls, v):
        return _validate_glucose(v)

    @field_validator("haemoglobin")
    @classmethod
    def v_hb(cls, v):
        return _validate_haemoglobin(v)

    @field_validator("cholesterol")
    @classmethod
    def v_chol(cls, v):
        return _validate_cholesterol(v)


class ApplicationUpdate(ApplicationCreate):
    """Same shape/validation as create — editing re-derives age and re-runs the AI check."""
    pass


class ApplicationResponse(BaseModel):
    id: UUID
    app_ref: str
    full_name: str
    date_of_birth: date
    email: str
    glucose: float
    haemoglobin: float
    cholesterol: float
    age_at_submission: int
    ai_status: AIStatus
    remarks: Optional[str]
    remarks_is_fallback: bool
    risk_tag: Optional[RiskTag]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class PaginatedApplications(BaseModel):
    items: list[ApplicationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
