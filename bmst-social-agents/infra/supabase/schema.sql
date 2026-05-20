-- =============================================================================
-- bmst-social-agents — Supabase schema
-- Apply with: supabase db push  OR  paste into the SQL editor
-- RLS is disabled; the API uses the service role key which bypasses RLS.
-- =============================================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- -----------------------------------------------------------------------------
-- published_topics
-- Deduplication log: one row per topic published by the pipeline.
-- SCOUT reads this table to avoid repeating recent topics.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS published_topics (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    topic       TEXT        NOT NULL,
    -- Content pillar — constrains the two strategic categories
    pillar      TEXT        NOT NULL CHECK (pillar IN ('ai', 'automation')),
    -- ISO-8601 date of the pipeline run that produced this topic (YYYY-MM-DD)
    run_date    TEXT        NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_published_topics_created_at
    ON published_topics (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_published_topics_pillar
    ON published_topics (pillar);

ALTER TABLE published_topics DISABLE ROW LEVEL SECURITY;

COMMENT ON TABLE published_topics IS
    'One row per topic published by the daily pipeline. Used by SCOUT for deduplication.';
COMMENT ON COLUMN published_topics.pillar IS
    'Strategic content pillar: ai or automation.';


-- -----------------------------------------------------------------------------
-- content_drafts
-- Working drafts produced by WRITER and CAROUSEL, keyed by session + platform.
-- The latest row per (session_id, platform) is the canonical draft.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS content_drafts (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id  TEXT        NOT NULL,
    platform    TEXT        NOT NULL,
    -- Full content object (PlatformPost or CarouselOutput serialised to JSON)
    content     JSONB       NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_content_drafts_session_platform
    ON content_drafts (session_id, platform, created_at DESC);

ALTER TABLE content_drafts DISABLE ROW LEVEL SECURITY;

COMMENT ON TABLE content_drafts IS
    'Draft content per pipeline session and platform, written by WRITER and CAROUSEL.';


-- -----------------------------------------------------------------------------
-- review_log
-- Quality-gate audit trail. REVISOR inserts a row when it completes its
-- AI analysis (human_decision = NULL). The WhatsApp approval webhook calls
-- update_approval() which fills in the human columns.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS review_log (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Opaque ID from ReviewResult, used by update_approval()
    review_id           TEXT        NOT NULL UNIQUE,
    -- Session context (nullable — populated when available from the calling agent)
    session_id          TEXT,
    platform            TEXT        NOT NULL,
    quality_score       FLOAT       NOT NULL,
    ai_detection_score  FLOAT       NOT NULL,
    -- List of issues found during quality check
    issues              JSONB       NOT NULL DEFAULT '[]',
    -- REVISOR AI recommendation before human responds
    ai_recommendation   TEXT        NOT NULL,
    -- Human decision — NULL means pending approval
    human_decision      TEXT,
    human_note          TEXT,
    human_decided_at    TIMESTAMPTZ,
    -- Revision note from REVISOR (if any)
    revision_note       TEXT,
    -- Name/id of the approver who will be contacted
    approver            TEXT        NOT NULL,
    -- When REVISOR completed its analysis
    reviewed_at         TIMESTAMPTZ NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_review_log_review_id
    ON review_log (review_id);

CREATE INDEX IF NOT EXISTS idx_review_log_pending
    ON review_log (human_decision, session_id)
    WHERE human_decision IS NULL;

CREATE INDEX IF NOT EXISTS idx_review_log_created_at
    ON review_log (created_at DESC);

ALTER TABLE review_log DISABLE ROW LEVEL SECURITY;

COMMENT ON TABLE review_log IS
    'REVISOR quality-gate results. human_decision IS NULL = awaiting human approval.';
COMMENT ON COLUMN review_log.ai_recommendation IS
    'REVISOR AI verdict: approved | rejected | revision_requested.';
COMMENT ON COLUMN review_log.human_decision IS
    'Human verdict received via WhatsApp. NULL while pending.';


-- -----------------------------------------------------------------------------
-- publication_log
-- Outcome record for every PUBLISHER attempt, including failures.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS publication_log (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Opaque ID from PublicationResult
    publication_id  TEXT        NOT NULL UNIQUE,
    platform        TEXT        NOT NULL,
    -- URL of the published post; NULL if publish failed
    post_url        TEXT,
    -- published | failed | manual_delivery
    status          TEXT        NOT NULL,
    published_at    TIMESTAMPTZ NOT NULL,
    -- Error message when status = 'failed'
    error           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_publication_log_platform_status
    ON publication_log (platform, status, created_at DESC);

ALTER TABLE publication_log DISABLE ROW LEVEL SECURITY;

COMMENT ON TABLE publication_log IS
    'Every PUBLISHER attempt — success, failure, or manual fallback.';


-- -----------------------------------------------------------------------------
-- approvers
-- Human approvers who receive WhatsApp approval requests from REVISOR.
-- Only rows where active = true are contacted.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS approvers (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT        NOT NULL,
    -- E.164 format: + followed by 7–15 digits
    whatsapp    TEXT        NOT NULL UNIQUE,
    active      BOOLEAN     NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE approvers DISABLE ROW LEVEL SECURITY;

COMMENT ON TABLE approvers IS
    'Registered human approvers for the REVISOR WhatsApp approval flow.';
COMMENT ON COLUMN approvers.whatsapp IS
    'E.164 phone number (e.g. +41795748225).';


-- -----------------------------------------------------------------------------
-- Seed data
-- -----------------------------------------------------------------------------
INSERT INTO approvers (name, whatsapp, active)
VALUES ('Fidel Inácio Kussunga', '+41795748225', true)
ON CONFLICT (whatsapp) DO NOTHING;
