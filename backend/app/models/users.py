from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRole(str, Enum):
    CLIMBER_FREE = "climber-free"
    CLIMBER_PREMIUM = "climber-premium"
    CLIMBER_ELITE = "climber-elite"
    COACH = "coach"
    GYM_ADMIN = "gym-admin"
    ADMIN = "admin"


class HandDominance(str, Enum):
    LEFT = "left"
    RIGHT = "right"
    AMBI = "ambi"


class UnitSystem(str, Enum):
    METRIC = "metric"
    IMPERIAL = "imperial"


class UserCreate(BaseModel):
    id: UUID
    email: EmailStr
    display_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    climbing_level: Optional[str] = None
    climbing_styles: Optional[List[str]] = None
    weight_kg: Optional[Decimal] = None
    height_cm: Optional[int] = None
    hand_dominance: Optional[HandDominance] = None
    preferred_unit: Optional[UnitSystem] = None
    preferred_lang: Optional[str] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    display_name: str
    first_name: Optional[str]
    last_name: Optional[str]
    avatar_url: Optional[str]
    role: UserRole
    climbing_level: Optional[str]
    climbing_styles: list = []
    weight_kg: Optional[Decimal]
    height_cm: Optional[int]
    hand_dominance: Optional[HandDominance]
    preferred_unit: UnitSystem
    preferred_lang: str
    total_sessions: int
    total_load_time_s: int
    best_max_force_kg: Decimal
    created_at: datetime
    last_login_at: Optional[datetime]


class UserPublicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_name: str
    avatar_url: Optional[str]
    climbing_level: Optional[str]
    climbing_styles: list = []
    total_sessions: int
    best_max_force_kg: Decimal
