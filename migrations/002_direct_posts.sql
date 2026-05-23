-- Pending previews for user-initiated direct posts from Telegram
CREATE TABLE IF NOT EXISTS direct_posts (
    id           TEXT PRIMARY KEY,
    bluesky_text TEXT NOT NULL,
    x_text       TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Allow signal_id to be NULL for direct (non-pipeline) posts
ALTER TABLE posts ALTER COLUMN signal_id DROP NOT NULL;
