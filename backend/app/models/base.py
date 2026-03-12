from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TimestampMixin(BaseModel):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SoftDeleteMixin(BaseModel):
    deleted_at: Optional[datetime] = None
