from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_user_id
from app.database import get_pool
from app.models.sensors import SensorCreate, SensorResponse, SensorUpdate

router = APIRouter(prefix="/api/v1/sensors", tags=["sensors"])


@router.get("", response_model=list[SensorResponse])
async def list_sensors(user_id: str = Depends(get_user_id)):
    pool = get_pool()
    rows = await pool.fetch(
        "SELECT * FROM sensors WHERE user_id = $1 ORDER BY created_at DESC", user_id
    )
    return [dict(r) for r in rows]


@router.post("", response_model=SensorResponse, status_code=201)
async def create_sensor(body: SensorCreate, user_id: str = Depends(get_user_id)):
    pool = get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO sensors (user_id, brand, model, ble_name, ble_mac, serial_number, fw_version, nickname)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING *
        """,
        user_id, body.brand, body.model, body.ble_name, body.ble_mac,
        body.serial_number, body.fw_version, body.nickname,
    )
    return dict(row)


@router.patch("/{sensor_id}", response_model=SensorResponse)
async def update_sensor(sensor_id: UUID, body: SensorUpdate, user_id: str = Depends(get_user_id)):
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clauses = []
    params: list = [sensor_id, user_id]
    for i, (field, value) in enumerate(updates.items(), start=3):
        set_clauses.append(f"{field} = ${i}")
        params.append(value)

    pool = get_pool()
    row = await pool.fetchrow(
        f"UPDATE sensors SET {', '.join(set_clauses)} WHERE id = $1 AND user_id = $2 RETURNING *",
        *params,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Sensor not found")
    return dict(row)


@router.delete("/{sensor_id}", status_code=204)
async def delete_sensor(sensor_id: UUID, user_id: str = Depends(get_user_id)):
    result = await get_pool().execute(
        "DELETE FROM sensors WHERE id = $1 AND user_id = $2", sensor_id, user_id
    )
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Sensor not found")
