CREATE TABLE IF NOT EXISTS employees (
    author_id   text PRIMARY KEY,
    full_name   text NOT NULL,
    department  text NOT NULL CHECK (department IN ('care', 'sales'))
);

CREATE TABLE IF NOT EXISTS events (
    event_id         text PRIMARY KEY CHECK (btrim(event_id) <> ''),
    conversation_id  text NOT NULL CHECK (btrim(conversation_id) <> ''),
    channel          text NOT NULL CHECK (channel IN ('telegram', 'max')),
    chat_id          text NOT NULL CHECK (btrim(chat_id) <> ''),
    lead_id          text CHECK (btrim(lead_id) <> ''),
    occurred_at      timestamptz NOT NULL,
    direction        text NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    author_id        text CHECK (btrim(author_id) <> ''),
    author_type      text NOT NULL CHECK (author_type IN ('partner', 'employee', 'bot', 'system')),
    message_type     text NOT NULL CHECK (message_type IN ('text', 'file', 'image', 'voice', 'template')),
    text             text
);

CREATE INDEX IF NOT EXISTS ix_events_conversation_id_occurred_at
    ON events (conversation_id, occurred_at);

CREATE TABLE IF NOT EXISTS rejected_events (
    id               bigserial PRIMARY KEY,
    event_id         text,
    conversation_id  text,
    issue_code       text NOT NULL,
    description      text NOT NULL,
    payload          jsonb NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_rejected_events_issue_code_payload
    ON rejected_events (issue_code, md5(payload::text));
