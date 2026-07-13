CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    role TEXT NOT NULL,       -- 'user' or 'assistant'
    content TEXT NOT NULL,
    tokens_used INTEGER DEFAULT 0,
    embedding TEXT            -- JSON array of float embedding vector
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    action TEXT NOT NULL,       -- e.g. 'web_search', 'open_app', 'run_code'
    input_data TEXT,
    output_data TEXT,
    success BOOLEAN DEFAULT 1,
    duration_ms INTEGER DEFAULT 0,
    error_msg TEXT
);

CREATE TABLE IF NOT EXISTS user_preferences (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_tasks_action ON tasks(action);
