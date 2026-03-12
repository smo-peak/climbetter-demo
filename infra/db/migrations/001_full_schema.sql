-- ============================================================
-- ClimBetter Database Schema v1.0
-- Target: PostgreSQL 16 + TimescaleDB extension
-- Idempotent: safe to re-run
-- ============================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "timescaledb";

-- ============================================================
-- Drop old MVP tables (from initial prototype)
-- ============================================================
DROP TABLE IF EXISTS sensor_measurements CASCADE;
DROP TABLE IF EXISTS training_sessions CASCADE;

-- ============================================================
-- TABLE: users
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY,
    email           VARCHAR(255) NOT NULL UNIQUE,
    display_name    VARCHAR(100) NOT NULL,
    first_name      VARCHAR(100),
    last_name       VARCHAR(100),
    avatar_url      TEXT,

    role            VARCHAR(20) NOT NULL DEFAULT 'climber-free'
                    CHECK (role IN ('climber-free','climber-premium','climber-elite','coach','gym-admin','admin')),
    climbing_level  VARCHAR(10),
    climbing_styles JSONB DEFAULT '[]',
    weight_kg       DECIMAL(5,1),
    height_cm       INTEGER,
    hand_dominance  VARCHAR(5) CHECK (hand_dominance IN ('left','right','ambi')),

    preferred_unit  VARCHAR(10) DEFAULT 'metric'
                    CHECK (preferred_unit IN ('metric','imperial')),
    preferred_lang  VARCHAR(5) DEFAULT 'fr',
    notification_prefs JSONB DEFAULT '{"push": true, "email": true}',

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at   TIMESTAMPTZ,
    deleted_at      TIMESTAMPTZ,

    total_sessions      INTEGER DEFAULT 0,
    total_load_time_s   INTEGER DEFAULT 0,
    best_max_force_kg   DECIMAL(6,2) DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_deleted ON users(deleted_at) WHERE deleted_at IS NULL;

-- ============================================================
-- TABLE: sensors
-- ============================================================
CREATE TABLE IF NOT EXISTS sensors (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    brand           VARCHAR(50) NOT NULL,
    model           VARCHAR(100) NOT NULL,
    ble_name        VARCHAR(100),
    ble_mac         VARCHAR(17),
    serial_number   VARCHAR(100),
    fw_version      VARCHAR(20),
    battery_voltage DECIMAL(4,2),

    last_tare_at        TIMESTAMPTZ,
    calibration_offset  DECIMAL(6,3) DEFAULT 0,

    nickname        VARCHAR(50),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at    TIMESTAMPTZ,

    UNIQUE(user_id, ble_name)
);

CREATE INDEX IF NOT EXISTS idx_sensors_user ON sensors(user_id);

-- ============================================================
-- TABLE: sessions
-- ============================================================
CREATE TABLE IF NOT EXISTS sessions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id       UUID UNIQUE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    type            VARCHAR(30) NOT NULL DEFAULT 'free_session'
                    CHECK (type IN (
                        'free_session','max_force','endurance','repeaters',
                        'rate_of_force','assessment','program_session'
                    )),

    title           VARCHAR(200),
    description     TEXT,
    location_type   VARCHAR(20) DEFAULT 'indoor'
                    CHECK (location_type IN ('indoor','outdoor','home')),
    location_name   VARCHAR(200),
    climbing_type   VARCHAR(20)
                    CHECK (climbing_type IN ('bouldering','sport','trad','ice','training') OR climbing_type IS NULL),
    grade           VARCHAR(10),

    started_at      TIMESTAMPTZ NOT NULL,
    ended_at        TIMESTAMPTZ,
    duration_s      INTEGER GENERATED ALWAYS AS (
                        CASE WHEN ended_at IS NOT NULL
                        THEN EXTRACT(EPOCH FROM (ended_at - started_at))::INTEGER
                        ELSE NULL END
                    ) STORED,

    sensor_count        SMALLINT DEFAULT 1,
    force_threshold_kg  DECIMAL(5,2) DEFAULT 2.0,
    sample_rate_hz      INTEGER DEFAULT 80,

    status          VARCHAR(20) NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active','completed','cancelled','syncing')),

    recorded_offline BOOLEAN DEFAULT FALSE,
    synced_at       TIMESTAMPTZ,

    tags            JSONB DEFAULT '[]',
    notes           TEXT,
    rating          SMALLINT CHECK (rating BETWEEN 1 AND 5),
    perceived_effort SMALLINT CHECK (perceived_effort BETWEEN 1 AND 10),

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user_date ON sessions(user_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_type ON sessions(type);
CREATE INDEX IF NOT EXISTS idx_sessions_client ON sessions(client_id) WHERE client_id IS NOT NULL;

-- ============================================================
-- TABLE: sensor_configs
-- ============================================================
CREATE TABLE IF NOT EXISTS sensor_configs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id      UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    sensor_id       UUID NOT NULL REFERENCES sensors(id) ON DELETE SET NULL,

    position        VARCHAR(10) NOT NULL DEFAULT 'unknown'
                    CHECK (position IN ('left','right','both','unknown')),
    tare_offset_kg  DECIMAL(6,3) DEFAULT 0,

    UNIQUE(session_id, position)
);

CREATE INDEX IF NOT EXISTS idx_sensor_configs_session ON sensor_configs(session_id);

-- ============================================================
-- TABLE: force_readings (HYPERTABLE)
-- ============================================================
CREATE TABLE IF NOT EXISTS force_readings (
    time            TIMESTAMPTZ NOT NULL,
    session_id      UUID NOT NULL,
    sensor_position VARCHAR(10) NOT NULL,

    force_kg        DECIMAL(7,3) NOT NULL,
    force_n         DECIMAL(7,2) GENERATED ALWAYS AS (force_kg * 9.80665) STORED,

    rfd_kgs         DECIMAL(7,2),
    quality         SMALLINT DEFAULT 100
                    CHECK (quality BETWEEN 0 AND 100)
);

SELECT create_hypertable('force_readings', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_force_session_time ON force_readings(session_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_force_session_sensor ON force_readings(session_id, sensor_position, time DESC);

-- Compression after 7 days
ALTER TABLE force_readings SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'session_id, sensor_position',
    timescaledb.compress_orderby = 'time DESC'
);
SELECT add_compression_policy('force_readings', INTERVAL '7 days', if_not_exists => TRUE);

-- Retention: 2 years
SELECT add_retention_policy('force_readings', INTERVAL '730 days', if_not_exists => TRUE);

-- ============================================================
-- TABLE: sequences
-- ============================================================
CREATE TABLE IF NOT EXISTS sequences (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id      UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    sensor_position VARCHAR(10) NOT NULL,

    sequence_number SMALLINT NOT NULL,
    type            VARCHAR(10) NOT NULL
                    CHECK (type IN ('load','rest')),

    started_at      TIMESTAMPTZ NOT NULL,
    ended_at        TIMESTAMPTZ NOT NULL,
    duration_s      DECIMAL(8,2) NOT NULL,

    avg_force_kg    DECIMAL(6,2),
    max_force_kg    DECIMAL(6,2),
    min_force_kg    DECIMAL(6,2),
    force_std_kg    DECIMAL(6,2),
    rfd_peak_kgs    DECIMAL(7,2),
    impulse_kgs     DECIMAL(10,2),

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sequences_session ON sequences(session_id, sensor_position, sequence_number);

-- ============================================================
-- TABLE: session_stats
-- ============================================================
CREATE TABLE IF NOT EXISTS session_stats (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id      UUID NOT NULL UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,

    total_duration_s    INTEGER NOT NULL,
    total_load_time_s   INTEGER NOT NULL,
    total_rest_time_s   INTEGER NOT NULL,
    load_rest_ratio     DECIMAL(4,2),
    num_sequences       SMALLINT NOT NULL,

    left_avg_force_kg   DECIMAL(6,2),
    left_max_force_kg   DECIMAL(6,2),
    left_min_force_kg   DECIMAL(6,2),
    left_force_std_kg   DECIMAL(6,2),

    right_avg_force_kg  DECIMAL(6,2),
    right_max_force_kg  DECIMAL(6,2),
    right_min_force_kg  DECIMAL(6,2),
    right_force_std_kg  DECIMAL(6,2),

    total_avg_force_kg  DECIMAL(6,2) NOT NULL,
    total_max_force_kg  DECIMAL(6,2) NOT NULL,
    total_impulse_kgs   DECIMAL(10,2),

    left_right_ratio    DECIMAL(4,2),
    asymmetry_pct       DECIMAL(5,2),

    endurance_index     DECIMAL(5,2),
    fatigue_rate        DECIMAL(5,2),

    performance_score   DECIMAL(5,2),
    score_breakdown     JSONB,

    force_vs_avg_pct    DECIMAL(5,2),
    force_vs_best_pct   DECIMAL(5,2),
    is_personal_best    BOOLEAN DEFAULT FALSE,

    raw_data_available  BOOLEAN DEFAULT TRUE,

    computed_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    algorithm_version   VARCHAR(10) DEFAULT '1.0'
);

CREATE INDEX IF NOT EXISTS idx_session_stats_session ON session_stats(session_id);

-- ============================================================
-- FUNCTIONS & TRIGGERS
-- ============================================================

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_updated_at ON users;
CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

DROP TRIGGER IF EXISTS trg_sessions_updated_at ON sessions;
CREATE TRIGGER trg_sessions_updated_at BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

DROP TRIGGER IF EXISTS trg_sensors_updated_at ON sensors;
CREATE TRIGGER trg_sensors_updated_at BEFORE UPDATE ON sensors
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Update user aggregate stats when session completes
CREATE OR REPLACE FUNCTION update_user_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'completed' AND (OLD.status IS NULL OR OLD.status != 'completed') THEN
        UPDATE users SET
            total_sessions = (
                SELECT COUNT(*) FROM sessions
                WHERE user_id = NEW.user_id AND status = 'completed' AND deleted_at IS NULL
            ),
            total_load_time_s = (
                SELECT COALESCE(SUM(ss.total_load_time_s), 0)
                FROM sessions s JOIN session_stats ss ON ss.session_id = s.id
                WHERE s.user_id = NEW.user_id AND s.status = 'completed' AND s.deleted_at IS NULL
            ),
            best_max_force_kg = (
                SELECT COALESCE(MAX(ss.total_max_force_kg), 0)
                FROM sessions s JOIN session_stats ss ON ss.session_id = s.id
                WHERE s.user_id = NEW.user_id AND s.status = 'completed' AND s.deleted_at IS NULL
            )
        WHERE id = NEW.user_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_session_update_user_stats ON sessions;
CREATE TRIGGER trg_session_update_user_stats AFTER INSERT OR UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION update_user_stats();

-- ============================================================
-- MATERIALIZED VIEW: user_progression
-- ============================================================
DROP MATERIALIZED VIEW IF EXISTS user_progression;
CREATE MATERIALIZED VIEW user_progression AS
SELECT
    s.user_id,
    DATE_TRUNC('week', s.started_at) AS week,
    COUNT(*)                          AS sessions_count,
    SUM(ss.total_load_time_s)         AS total_load_time_s,
    AVG(ss.total_avg_force_kg)        AS avg_force_kg,
    MAX(ss.total_max_force_kg)        AS max_force_kg,
    AVG(ss.performance_score)         AS avg_performance_score,
    AVG(ss.left_right_ratio)          AS avg_lr_ratio
FROM sessions s
JOIN session_stats ss ON ss.session_id = s.id
WHERE s.status = 'completed' AND s.deleted_at IS NULL
GROUP BY s.user_id, DATE_TRUNC('week', s.started_at);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_progression ON user_progression(user_id, week);
