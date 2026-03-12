from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.sequences import SequenceResponse
from app.models.sessions import SessionResponse


class SessionStatsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: UUID

    total_duration_s: int
    total_load_time_s: int
    total_rest_time_s: int
    load_rest_ratio: Optional[Decimal]
    num_sequences: int

    left_avg_force_kg: Optional[Decimal]
    left_max_force_kg: Optional[Decimal]
    right_avg_force_kg: Optional[Decimal]
    right_max_force_kg: Optional[Decimal]

    total_avg_force_kg: Decimal
    total_max_force_kg: Decimal
    total_impulse_kgs: Optional[Decimal]

    left_right_ratio: Optional[Decimal]
    asymmetry_pct: Optional[Decimal]

    endurance_index: Optional[Decimal]
    fatigue_rate: Optional[Decimal]

    performance_score: Optional[Decimal]
    score_breakdown: Optional[dict]

    force_vs_avg_pct: Optional[Decimal]
    force_vs_best_pct: Optional[Decimal]
    is_personal_best: bool

    computed_at: datetime
    algorithm_version: str


class SessionFullResponse(BaseModel):
    session: SessionResponse
    stats: Optional[SessionStatsResponse] = None
    sequences: List[SequenceResponse] = []
