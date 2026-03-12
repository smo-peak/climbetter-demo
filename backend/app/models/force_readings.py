from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ForceReadingCreate(BaseModel):
    time: datetime
    sensor_position: str = Field(..., pattern=r"^(left|right|both)$")
    force_kg: Decimal = Field(..., ge=0, le=500)
    rfd_kgs: Optional[Decimal] = None
    quality: int = Field(100, ge=0, le=100)


class ForceReadingBatch(BaseModel):
    session_id: UUID
    readings: List[ForceReadingCreate] = Field(..., min_length=1, max_length=2000)


class ForceReadingResponse(BaseModel):
    time: datetime
    sensor_position: str
    force_kg: Decimal
    force_n: Decimal
    rfd_kgs: Optional[Decimal]
    quality: int
