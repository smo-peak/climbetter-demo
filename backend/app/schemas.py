from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# --- Training Sessions ---

class SessionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    session_type: str = Field(pattern=r"^(bouldering|lead|speed|training)$")
    grade: str | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    notes: str | None = None
    started_at: datetime | None = None


class SessionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    session_type: str | None = Field(
        default=None, pattern=r"^(bouldering|lead|speed|training)$"
    )
    grade: str | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    notes: str | None = None


class SessionOut(BaseModel):
    id: UUID
    user_id: str
    title: str
    session_type: str
    grade: str | None
    duration_seconds: int | None
    notes: str | None
    started_at: datetime
    created_at: datetime
    updated_at: datetime


# --- Sensor Measurements ---

class MeasurementIn(BaseModel):
    time: datetime
    sensor_type: str = Field(min_length=1, max_length=50)
    value: float
    unit: str = Field(min_length=1, max_length=20)
    metadata: dict | None = None


class MeasurementBatch(BaseModel):
    session_id: UUID
    measurements: list[MeasurementIn] = Field(min_length=1, max_length=10000)


class MeasurementOut(BaseModel):
    time: datetime
    session_id: UUID
    sensor_type: str
    value: float
    unit: str
    metadata: dict | None
