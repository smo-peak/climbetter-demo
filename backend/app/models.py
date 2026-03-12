import asyncpg


async def create_tables(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS training_sessions (
                id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id         TEXT NOT NULL,
                title           TEXT NOT NULL,
                session_type    TEXT NOT NULL
                                CHECK (session_type IN (
                                    'bouldering','lead','speed','training'
                                )),
                grade           TEXT,
                duration_seconds INTEGER,
                notes           TEXT,
                started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
                created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
            );

            CREATE INDEX IF NOT EXISTS idx_sessions_user_id
                ON training_sessions (user_id);

            CREATE INDEX IF NOT EXISTS idx_sessions_started_at
                ON training_sessions (started_at DESC);
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sensor_measurements (
                time            TIMESTAMPTZ NOT NULL,
                session_id      UUID NOT NULL
                                REFERENCES training_sessions(id) ON DELETE CASCADE,
                sensor_type     TEXT NOT NULL,
                value           DOUBLE PRECISION NOT NULL,
                unit            TEXT NOT NULL,
                metadata        JSONB
            );

            SELECT create_hypertable(
                'sensor_measurements', 'time',
                if_not_exists => TRUE
            );

            CREATE INDEX IF NOT EXISTS idx_measurements_session
                ON sensor_measurements (session_id, time DESC);
        """)
