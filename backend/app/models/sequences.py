from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SequenceType(str, Enum):
    LOAD = "load"
    REST = "rest"


class SequenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    sensor_position: str
    sequence_number: int
    type: SequenceType
    started_at: datetime
    ended_at: datetime
    duration_s: Decimal
    avg_force_kg: Optional[Decimal]
    max_force_kg: Optional[Decimal]
    min_force_kg: Optional[Decimal]
    force_std_kg: Optional[Decimal]
    rfd_peak_kgs: Optional[Decimal]
    impulse_kgs: Optional[Decimal]
