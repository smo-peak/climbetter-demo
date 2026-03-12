from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SessionType(str, Enum):
    FREE_SESSION = "free_session"
    MAX_FORCE = "max_force"
    ENDURANCE = "endurance"
    REPEATERS = "repeaters"
    RATE_OF_FORCE = "rate_of_force"
    ASSESSMENT = "assessment"
    PROGRAM_SESSION = "program_session"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    SYNCING = "syncing"


class LocationType(str, Enum):
    INDOOR = "indoor"
    OUTDOOR = "outdoor"
    HOME = "home"


class ClimbingType(str, Enum):
    BOULDERING = "bouldering"
    SPORT = "sport"
    TRAD = "trad"
    ICE = "ice"
    TRAINING = "training"


class SessionCreate(BaseModel):
    client_id: Optional[UUID] = None
    type: SessionType = SessionType.FREE_SESSION
    title: Optional[str] = None
    description: Optional[str] = None
    location_type: LocationType = LocationType.INDOOR
    location_name: Optional[str] = None
    climbing_type: Optional[ClimbingType] = None
    grade: Optional[str] = None
    started_at: datetime
    sensor_count: int = 1
    force_threshold_kg: Decimal = Decimal("2.0")
    sample_rate_hz: int = 80
    tags: List[str] = []
    notes: Optional[str] = None
    recorded_offline: bool = False


class SessionEnd(BaseModel):
    ended_at: datetime
    rating: Optional[int] = Field(None, ge=1, le=5)
    perceived_effort: Optional[int] = Field(None, ge=1, le=10)
    notes: Optional[str] = None


class SessionUpdate(BaseModel):
    title: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    perceived_effort: Optional[int] = Field(None, ge=1, le=10)


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: Optional[UUID]
    user_id: UUID
    type: SessionType
    title: Optional[str]
    description: Optional[str]
    location_type: LocationType
    location_name: Optional[str]
    climbing_type: Optional[ClimbingType]
    grade: Optional[str]
    started_at: datetime
    ended_at: Optional[datetime]
    duration_s: Optional[int]
    sensor_count: int
    force_threshold_kg: Decimal
    status: SessionStatus
    tags: list
    notes: Optional[str]
    rating: Optional[int]
    perceived_effort: Optional[int]
    recorded_offline: bool
    synced_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class SessionListResponse(BaseModel):
    items: List[SessionResponse]
    total: int
    page: int
    page_size: int
    has_more: bool
