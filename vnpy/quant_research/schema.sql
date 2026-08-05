
-- 实验表
CREATE TABLE IF NOT EXISTS experiments (
    experiment_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT,
    tags TEXT,
    params TEXT,
    metrics TEXT,
    notes TEXT,
    starred INTEGER DEFAULT 0,
    created_by TEXT,
    parent_id TEXT,
    created_at TEXT,
    updated_at TEXT
);

-- 数据集表
CREATE TABLE IF NOT EXISTS datasets (
    dataset_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT,
    description TEXT,
    source TEXT,
    status TEXT,
    symbols TEXT,
    start_date TEXT,
    end_date TEXT,
    fields TEXT,
    row_count INTEGER,
    size_mb REAL,
    quality_score REAL DEFAULT 0.0,
    quality_metrics TEXT,
    tags TEXT,
    dependencies TEXT,
    created_by TEXT,
    created_at TEXT,
    updated_at TEXT
);

-- 数据集快照表
CREATE TABLE IF NOT EXISTS dataset_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    dataset_id TEXT,
    version TEXT,
    row_count INTEGER,
    quality_score REAL,
    created_at TEXT
);

-- 特征表
CREATE TABLE IF NOT EXISTS features (
    feature_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT,
    description TEXT,
    category TEXT,
    formula TEXT,
    status TEXT,
    ic REAL,
    rank_ic REAL,
    ir REAL,
    icir REAL,
    author TEXT,
    tags TEXT,
    dependencies TEXT,
    dataset_ids TEXT,
    created_at TEXT,
    updated_at TEXT
);

-- 策略表
CREATE TABLE IF NOT EXISTS strategies (
    strategy_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT,
    description TEXT,
    strategy_type TEXT,
    status TEXT,
    author TEXT,
    universe TEXT,
    params TEXT,
    annual_return REAL,
    max_drawdown REAL,
    sharpe REAL,
    win_rate REAL,
    tags TEXT,
    feature_ids TEXT,
    dataset_ids TEXT,
    backtest_ids TEXT,
    created_at TEXT,
    updated_at TEXT
);

-- 回测表
CREATE TABLE IF NOT EXISTS backtests (
    backtest_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT,
    strategy_id TEXT,
    strategy_name TEXT,
    start_date TEXT,
    end_date TEXT,
    initial_capital REAL,
    commission REAL,
    annual_return REAL,
    max_drawdown REAL,
    sharpe REAL,
    win_rate REAL,
    total_trades INTEGER,
    tags TEXT,
    feature_ids TEXT,
    dataset_ids TEXT,
    created_by TEXT,
    created_at TEXT,
    updated_at TEXT
);

-- 报告表
CREATE TABLE IF NOT EXISTS reports (
    report_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    report_type TEXT,
    author TEXT,
    summary TEXT,
    published INTEGER DEFAULT 0,
    experiment_id TEXT,
    strategy_id TEXT,
    backtest_id TEXT,
    feature_ids TEXT,
    tags TEXT,
    created_at TEXT,
    updated_at TEXT
);

-- 报告章节表
CREATE TABLE IF NOT EXISTS report_sections (
    section_id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id TEXT,
    title TEXT,
    content TEXT,
    section_order INTEGER
);

-- 日志表
CREATE TABLE IF NOT EXISTS logs (
    log_id TEXT PRIMARY KEY,
    timestamp TEXT,
    level TEXT,
    source TEXT,
    message TEXT,
    context_id TEXT,
    context_name TEXT,
    details TEXT,
    user TEXT
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_experiments_status ON experiments(status);
CREATE INDEX IF NOT EXISTS idx_experiments_created_at ON experiments(created_at);
CREATE INDEX IF NOT EXISTS idx_datasets_status ON datasets(status);
CREATE INDEX IF NOT EXISTS idx_features_status ON features(status);
CREATE INDEX IF NOT EXISTS idx_strategies_status ON strategies(status);
CREATE INDEX IF NOT EXISTS idx_backtests_status ON backtests(status);
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level);
