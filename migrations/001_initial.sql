-- social-assistant initial schema

CREATE TABLE IF NOT EXISTS signals (
    id            TEXT PRIMARY KEY,
    source        TEXT NOT NULL,           -- 'github_release' | 'github_stars' | 'github_new_repo'
    repo          TEXT NOT NULL,           -- owner/repo
    topic_summary TEXT,                    -- LLM-generated, used for dedup
    raw_data      JSONB NOT NULL DEFAULT '{}',
    detected_at   TIMESTAMPTZ NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending', 'approved', 'rejected', 'discarded'))
);

CREATE INDEX IF NOT EXISTS signals_repo_source ON signals (repo, source);
CREATE INDEX IF NOT EXISTS signals_detected_at ON signals (detected_at DESC);

CREATE TABLE IF NOT EXISTS posts (
    id               TEXT PRIMARY KEY,
    signal_id        TEXT REFERENCES signals(id),
    platform         TEXT NOT NULL,        -- 'bluesky' | 'x'
    topic_summary    TEXT NOT NULL,
    content          TEXT NOT NULL,
    published_at     TIMESTAMPTZ NOT NULL,
    platform_post_id TEXT,
    metadata         JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS posts_published_at ON posts (published_at DESC);
CREATE INDEX IF NOT EXISTS posts_platform ON posts (platform);

CREATE TABLE IF NOT EXISTS threads (
    thread_id  TEXT PRIMARY KEY,           -- LangGraph thread_id
    signal_id  TEXT REFERENCES signals(id),
    created_at TIMESTAMPTZ NOT NULL
);
