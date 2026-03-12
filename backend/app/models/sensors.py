from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SensorCreate(BaseModel):
    brand: str
    model: str
    ble_name: Optional[str] = None
    ble_mac: Optional[str] = None
    serial_number: Optional[str] = None
    fw_version: Optional[str] = None
    nickname: Optional[str] = None


class SensorUpdate(BaseModel):
    nickname: Optional[str] = None
    fw_version: Optional[str] = None
    battery_voltage: Optional[Decimal] = None
    calibration_offset: Optional[Decimal] = None


class SensorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    brand: str
    model: str
    ble_name: Optional[str]
    nickname: Optional[str]
    fw_version: Optional[str]
    battery_voltage: Optional[Decimal]
    last_seen_at: Optional[datetime]
    created_at: datetime
