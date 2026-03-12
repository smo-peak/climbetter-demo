import math
from decimal import Decimal
from uuid import UUID

import asyncpg


async def detect_sequences(
    pool: asyncpg.Pool, session_id: UUID, threshold_kg: Decimal
) -> int:
    """Detect load/rest sequences from force readings.

    Returns the number of sequences inserted.
    """
    # Clear previous sequences for re-computation
    await pool.execute("DELETE FROM sequences WHERE session_id = $1", session_id)

    # Get all readings ordered by position and time
    rows = await pool.fetch(
        """
        SELECT time, sensor_position, force_kg
        FROM force_readings
        WHERE session_id = $1
        ORDER BY sensor_position, time ASC
        """,
        session_id,
    )

    if not rows:
        return 0

    # Group by sensor_position
    positions: dict[str, list] = {}
    for r in rows:
        pos = r["sensor_position"]
        positions.setdefault(pos, []).append(r)

    total_inserted = 0

    for position, readings in positions.items():
        sequences = _detect_for_position(readings, threshold_kg)
        if not sequences:
            continue

        await pool.executemany(
            """
            INSERT INTO sequences
                (session_id, sensor_position, sequence_number, type,
                 started_at, ended_at, duration_s,
                 avg_force_kg, max_force_kg, min_force_kg,
                 force_std_kg, rfd_peak_kgs, impulse_kgs)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
            """,
            [
                (
                    session_id, position, s["seq_num"], s["type"],
                    s["started_at"], s["ended_at"], s["duration_s"],
                    s["avg_force"], s["max_force"], s["min_force"],
                    s["std_force"], s["rfd_peak"], s["impulse"],
                )
                for s in sequences
            ],
        )
        total_inserted += len(sequences)

    return total_inserted


def _detect_for_position(
    readings: list, threshold_kg: Decimal
) -> list[dict]:
    """Detect load/rest transitions for a single sensor position."""
    if len(readings) < 2:
        return []

    sequences: list[dict] = []
    is_loaded = float(readings[0]["force_kg"]) >= float(threshold_kg)
    seg_start = 0
    seq_num = 1

    for i in range(1, len(readings)):
        current_loaded = float(readings[i]["force_kg"]) >= float(threshold_kg)
        if current_loaded != is_loaded:
            # Transition detected — close current segment
            seq = _build_sequence(
                readings[seg_start:i], seq_num, "load" if is_loaded else "rest"
            )
            sequences.append(seq)
            seq_num += 1
            seg_start = i
            is_loaded = current_loaded

    # Close final segment
    seq = _build_sequence(
        readings[seg_start:], seq_num, "load" if is_loaded else "rest"
    )
    sequences.append(seq)

    return sequences


def _build_sequence(readings: list, seq_num: int, seq_type: str) -> dict:
    """Build a sequence dict with computed stats."""
    started = readings[0]["time"]
    ended = readings[-1]["time"]
    duration = (ended - started).total_seconds()

    forces = [float(r["force_kg"]) for r in readings]
    avg_f = sum(forces) / len(forces)
    max_f = max(forces)
    min_f = min(forces)

    # Standard deviation
    if len(forces) > 1:
        variance = sum((f - avg_f) ** 2 for f in forces) / (len(forces) - 1)
        std_f = math.sqrt(variance)
    else:
        std_f = 0.0

    # Rate of Force Development peak (max Δforce/Δtime between consecutive points)
    # Ignore dt < 1ms to avoid unrealistic spikes from duplicate/near-duplicate timestamps
    rfd_peak = 0.0
    for i in range(1, len(readings)):
        dt = (readings[i]["time"] - readings[i - 1]["time"]).total_seconds()
        if dt >= 0.001:
            df = abs(float(readings[i]["force_kg"]) - float(readings[i - 1]["force_kg"]))
            rfd = df / dt
            rfd_peak = max(rfd_peak, rfd)

    # Impulse (force × time integral, trapezoidal)
    impulse = 0.0
    for i in range(1, len(readings)):
        dt = (readings[i]["time"] - readings[i - 1]["time"]).total_seconds()
        avg_pair = (float(readings[i]["force_kg"]) + float(readings[i - 1]["force_kg"])) / 2
        impulse += avg_pair * dt

    return {
        "seq_num": seq_num,
        "type": seq_type,
        "started_at": started,
        "ended_at": ended,
        "duration_s": Decimal(str(round(duration, 2))),
        "avg_force": Decimal(str(round(avg_f, 2))) if seq_type == "load" else None,
        "max_force": Decimal(str(round(max_f, 2))) if seq_type == "load" else None,
        "min_force": Decimal(str(round(min_f, 2))) if seq_type == "load" else None,
        "std_force": Decimal(str(round(std_f, 2))) if seq_type == "load" else None,
        "rfd_peak": Decimal(str(round(rfd_peak, 2))) if seq_type == "load" else None,
        "impulse": Decimal(str(round(impulse, 2))) if seq_type == "load" else None,
    }
