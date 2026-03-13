from decimal import Decimal
from uuid import UUID

import asyncpg


async def compute_stats(
    pool: asyncpg.Pool, session_id: UUID, user_id: str
) -> dict | None:
    """Compute and store session stats from detected sequences.

    Returns the session_stats row or None if no sequences exist.
    """
    # Delete previous stats for re-computation
    await pool.execute("DELETE FROM session_stats WHERE session_id = $1", session_id)

    # Get session duration
    session = await pool.fetchrow(
        "SELECT started_at, ended_at FROM sessions WHERE id = $1", session_id
    )
    if session is None or session["ended_at"] is None:
        return None

    total_duration = int((session["ended_at"] - session["started_at"]).total_seconds())

    # Get sequences grouped by type and position
    seqs = await pool.fetch(
        "SELECT * FROM sequences WHERE session_id = $1 ORDER BY sequence_number",
        session_id,
    )
    if not seqs:
        return None

    load_seqs = [s for s in seqs if s["type"] == "load"]
    rest_seqs = [s for s in seqs if s["type"] == "rest"]

    total_load_time = int(sum(float(s["duration_s"]) for s in load_seqs))
    total_rest_time = int(sum(float(s["duration_s"]) for s in rest_seqs))
    load_rest_ratio = (
        Decimal(str(round(total_load_time / total_rest_time, 2)))
        if total_rest_time > 0 else None
    )

    # Per-position stats
    left_seqs = [s for s in load_seqs if s["sensor_position"] == "left"]
    right_seqs = [s for s in load_seqs if s["sensor_position"] == "right"]

    left_avg = _avg(left_seqs, "avg_force_kg")
    left_max = _max(left_seqs, "max_force_kg")
    right_avg = _avg(right_seqs, "avg_force_kg")
    right_max = _max(right_seqs, "max_force_kg")

    # Total (all positions)
    total_avg = _avg(load_seqs, "avg_force_kg") or Decimal("0")
    total_max = _max(load_seqs, "max_force_kg") or Decimal("0")
    total_impulse = _sum(load_seqs, "impulse_kgs")

    # Asymmetry
    lr_ratio = None
    asymmetry = None
    if left_avg and right_avg and float(right_avg) > 0:
        lr_ratio = Decimal(str(round(float(left_avg) / float(right_avg), 2)))
        asymmetry = Decimal(str(round(abs(1 - float(lr_ratio)) * 100, 2)))

    # Endurance index: last load avg / first load avg × 100
    endurance_index = None
    fatigue_rate = None
    if len(load_seqs) >= 2:
        first_avg = float(load_seqs[0]["avg_force_kg"] or 0)
        last_avg = float(load_seqs[-1]["avg_force_kg"] or 0)
        if first_avg > 0:
            endurance_index = Decimal(str(round(last_avg / first_avg * 100, 2)))
            fatigue_rate = Decimal(str(round((1 - last_avg / first_avg) * 100, 2)))

    # Get user weight for force/weight ratio
    user_weight = await pool.fetchval(
        "SELECT weight_kg FROM users WHERE id = $1", user_id
    )

    endurance_score = float(endurance_index) if endurance_index else 50
    stability_score = 100 - min(float(_avg(load_seqs, "force_std_kg") or 0) * 10, 100)
    volume_score = min(total_load_time / 300 * 100, 100)  # 5min = 100

    if user_weight and float(user_weight) > 0:
        # Score v2: force/weight ratio based
        fw_ratio = float(total_max) / float(user_weight)
        if fw_ratio < 0.2:
            fw_ratio_score = 20.0
        elif fw_ratio < 0.4:
            fw_ratio_score = 20 + (fw_ratio - 0.2) / 0.2 * 30
        elif fw_ratio < 0.6:
            fw_ratio_score = 50 + (fw_ratio - 0.4) / 0.2 * 25
        elif fw_ratio < 0.8:
            fw_ratio_score = 75 + (fw_ratio - 0.6) / 0.2 * 15
        else:
            fw_ratio_score = 90 + min((fw_ratio - 0.8) / 0.2 * 10, 10)

        perf_score = Decimal(str(round(
            fw_ratio_score * 0.40 + endurance_score * 0.25 +
            stability_score * 0.20 + volume_score * 0.15,
            2
        )))

        score_breakdown = {
            "force": round(fw_ratio_score, 1),
            "force_weight_ratio": round(fw_ratio, 2),
            "endurance": round(endurance_score, 1),
            "stability": round(stability_score, 1),
            "volume": round(volume_score, 1),
            "algorithm_version": "2.0",
        }
    else:
        # Score v1 fallback: raw force based
        force_score = min(float(total_max) / 50 * 100, 100)  # 50kg = 100

        perf_score = Decimal(str(round(
            force_score * 0.35 + endurance_score * 0.25 +
            stability_score * 0.20 + volume_score * 0.20,
            2
        )))

        score_breakdown = {
            "force": round(force_score, 1),
            "endurance": round(endurance_score, 1),
            "stability": round(stability_score, 1),
            "volume": round(volume_score, 1),
            "algorithm_version": "1.0",
        }

    # Compare with history
    hist_avg = await pool.fetchval(
        """
        SELECT AVG(total_max_force_kg) FROM session_stats ss
        JOIN sessions s ON s.id = ss.session_id
        WHERE s.user_id = $1 AND s.status = 'completed'
          AND s.started_at > NOW() - INTERVAL '30 days'
        """,
        user_id,
    )
    hist_best = await pool.fetchval(
        """
        SELECT MAX(total_max_force_kg) FROM session_stats ss
        JOIN sessions s ON s.id = ss.session_id
        WHERE s.user_id = $1 AND s.status = 'completed'
        """,
        user_id,
    )

    force_vs_avg = None
    force_vs_best = None
    is_pb = False
    if hist_avg and float(hist_avg) > 0:
        force_vs_avg = Decimal(str(round(float(total_max) / float(hist_avg) * 100, 2)))
    if hist_best and float(hist_best) > 0:
        force_vs_best = Decimal(str(round(float(total_max) / float(hist_best) * 100, 2)))
        is_pb = float(total_max) > float(hist_best)

    import json
    row = await pool.fetchrow(
        """
        INSERT INTO session_stats (
            session_id, total_duration_s, total_load_time_s, total_rest_time_s,
            load_rest_ratio, num_sequences,
            left_avg_force_kg, left_max_force_kg,
            right_avg_force_kg, right_max_force_kg,
            total_avg_force_kg, total_max_force_kg, total_impulse_kgs,
            left_right_ratio, asymmetry_pct,
            endurance_index, fatigue_rate,
            performance_score, score_breakdown,
            force_vs_avg_pct, force_vs_best_pct, is_personal_best
        ) VALUES (
            $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22
        ) RETURNING *
        """,
        session_id, total_duration, total_load_time, total_rest_time,
        load_rest_ratio, len(load_seqs),
        left_avg, left_max, right_avg, right_max,
        total_avg, total_max, total_impulse,
        lr_ratio, asymmetry,
        endurance_index, fatigue_rate,
        perf_score, json.dumps(score_breakdown),
        force_vs_avg, force_vs_best, is_pb,
    )

    # asyncpg returns JSONB as string — parse it back to dict
    result = dict(row) if row else None
    if result and isinstance(result.get("score_breakdown"), str):
        result["score_breakdown"] = json.loads(result["score_breakdown"])
    return result


def _avg(seqs: list, field: str) -> Decimal | None:
    vals = [float(s[field]) for s in seqs if s[field] is not None]
    if not vals:
        return None
    return Decimal(str(round(sum(vals) / len(vals), 2)))


def _max(seqs: list, field: str) -> Decimal | None:
    vals = [float(s[field]) for s in seqs if s[field] is not None]
    if not vals:
        return None
    return Decimal(str(round(max(vals), 2)))


def _sum(seqs: list, field: str) -> Decimal | None:
    vals = [float(s[field]) for s in seqs if s[field] is not None]
    if not vals:
        return None
    return Decimal(str(round(sum(vals), 2)))
