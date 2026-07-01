-- HealthChecker/app/db/setup.sql
-- Run this once against a fresh PostgreSQL database to create everything
-- HealthChecker needs. See README.md for exact run instructions.

-- 1. Create the database (run this single line from psql connected to the
--    default "postgres" database — CREATE DATABASE cannot run inside a
--    transaction block / cannot be combined with the rest of this script).
--    Skip this line if the database already exists.
-- CREATE DATABASE healthchecker;

-- 2. Connect to the new database, then run everything below:
-- \c healthchecker

CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- gives us gen_random_uuid()

DO $$ BEGIN
    CREATE TYPE ai_status AS ENUM ('processing', 'done');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE risk_tag AS ENUM ('normal', 'slightly_abnormal', 'high');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS applications (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    app_ref               VARCHAR(20) UNIQUE NOT NULL,

    full_name             VARCHAR(120) NOT NULL,
    date_of_birth         DATE NOT NULL,
    email                 VARCHAR(255) NOT NULL,

    glucose               NUMERIC(8,2) NOT NULL,
    haemoglobin           NUMERIC(8,2) NOT NULL,
    cholesterol           NUMERIC(8,2) NOT NULL,

    age_at_submission     INTEGER NOT NULL,

    ai_status             ai_status NOT NULL DEFAULT 'processing',
    remarks               TEXT,
    remarks_is_fallback   BOOLEAN NOT NULL DEFAULT FALSE,
    risk_tag              risk_tag,

    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_applications_email ON applications (email);
CREATE INDEX IF NOT EXISTS idx_applications_full_name ON applications (full_name);
CREATE INDEX IF NOT EXISTS idx_applications_created_at ON applications (created_at);
CREATE INDEX IF NOT EXISTS idx_applications_risk_tag ON applications (risk_tag);

-- Optional: a dedicated low-privilege app user (recommended over using a superuser).
-- Replace the password, and make sure it matches DB_USER / DB_PASSWORD in your .env.
-- CREATE USER healthchecker_user WITH PASSWORD 'healthchecker_pass';
-- GRANT ALL PRIVILEGES ON DATABASE healthchecker TO healthchecker_user;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO healthchecker_user;
