-- DRAKS sonuçları için şeffaf takip tabloları (opsiyonel)
CREATE TABLE IF NOT EXISTS draks_signal_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol TEXT NOT NULL,
  timeframe TEXT NOT NULL DEFAULT '1h',
  regime_probs TEXT NOT NULL,
  weights TEXT NOT NULL,
  score REAL NOT NULL,
  decision TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_draks_signal_runs_symbol ON draks_signal_runs(symbol, created_at DESC);

CREATE TABLE IF NOT EXISTS draks_decisions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol TEXT NOT NULL,
  decision TEXT NOT NULL,          -- LONG/SHORT/HOLD
  position_pct REAL,
  stop REAL,
  take_profit REAL,
  reasons TEXT,                    -- JSON string
  raw_response TEXT,               -- JSON string
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_draks_decisions_symbol ON draks_decisions(symbol, created_at DESC);
