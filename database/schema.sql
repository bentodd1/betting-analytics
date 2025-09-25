-- Sports Betting Analytics Database Schema
-- PostgreSQL implementation based on The Odds API structure

-- Drop tables if they exist (for clean reinstalls)
DROP TABLE IF EXISTS bet_outcomes CASCADE;
DROP TABLE IF EXISTS totals CASCADE;
DROP TABLE IF EXISTS spreads CASCADE;
DROP TABLE IF EXISTS moneylines CASCADE;
DROP TABLE IF EXISTS bookmakers CASCADE;
DROP TABLE IF EXISTS games CASCADE;
DROP TABLE IF EXISTS teams CASCADE;
DROP TABLE IF EXISTS sports CASCADE;

-- Core sports table
CREATE TABLE sports (
    sport_id SERIAL PRIMARY KEY,
    sport_key VARCHAR(50) UNIQUE NOT NULL,
    sport_title VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Teams table
CREATE TABLE teams (
    team_id SERIAL PRIMARY KEY,
    team_name VARCHAR(100) NOT NULL,
    sport_id INTEGER REFERENCES sports(sport_id),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(team_name, sport_id)
);

-- Games table - matches The Odds API event structure
CREATE TABLE games (
    game_id VARCHAR(100) PRIMARY KEY,           -- API 'id' field
    sport_id INTEGER REFERENCES sports(sport_id),
    commence_time TIMESTAMP NOT NULL,           -- API 'commence_time'
    home_team_id INTEGER REFERENCES teams(team_id),
    away_team_id INTEGER REFERENCES teams(team_id),
    home_score INTEGER,
    away_score INTEGER,
    status VARCHAR(20) DEFAULT 'scheduled',     -- scheduled, in_progress, completed
    completed_at TIMESTAMP,
    raw_data JSONB,                            -- Store full API response
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Bookmakers table - matches API bookmaker structure
CREATE TABLE bookmakers (
    bookmaker_id SERIAL PRIMARY KEY,
    bookmaker_key VARCHAR(50) UNIQUE NOT NULL,  -- API 'key' field
    bookmaker_title VARCHAR(100) NOT NULL,      -- API 'title' field
    created_at TIMESTAMP DEFAULT NOW()
);

-- Moneyline odds table - h2h market from API
CREATE TABLE moneylines (
    moneyline_id SERIAL PRIMARY KEY,
    game_id VARCHAR(100) REFERENCES games(game_id),
    bookmaker_id INTEGER REFERENCES bookmakers(bookmaker_id),
    home_price DECIMAL(10,2),                   -- American odds for home team
    away_price DECIMAL(10,2),                   -- American odds for away team
    last_update TIMESTAMP,                      -- API 'last_update' timestamp
    snapshot_timestamp TIMESTAMP NOT NULL,      -- When this odds snapshot was taken
    recorded_at TIMESTAMP DEFAULT NOW(),        -- When we fetched/recorded this data
    is_latest BOOLEAN DEFAULT TRUE,
    raw_outcomes JSONB,                         -- Store raw outcomes array
    created_at TIMESTAMP DEFAULT NOW(),

    -- Add constraint to prevent duplicate odds at same time
    UNIQUE(game_id, bookmaker_id, snapshot_timestamp)
);

-- Spread odds table - spreads market from API
CREATE TABLE spreads (
    spread_id SERIAL PRIMARY KEY,
    game_id VARCHAR(100) REFERENCES games(game_id),
    bookmaker_id INTEGER REFERENCES bookmakers(bookmaker_id),
    home_spread DECIMAL(10,2),                  -- Point spread for home team
    home_price DECIMAL(10,2),                   -- Odds for home spread
    away_spread DECIMAL(10,2),                  -- Point spread for away team
    away_price DECIMAL(10,2),                   -- Odds for away spread
    last_update TIMESTAMP,                      -- API 'last_update' timestamp
    snapshot_timestamp TIMESTAMP NOT NULL,      -- When this odds snapshot was taken
    recorded_at TIMESTAMP DEFAULT NOW(),        -- When we fetched/recorded this data
    is_latest BOOLEAN DEFAULT TRUE,
    raw_outcomes JSONB,                         -- Store raw outcomes array
    created_at TIMESTAMP DEFAULT NOW(),

    -- Add constraint to prevent duplicate odds at same time
    UNIQUE(game_id, bookmaker_id, snapshot_timestamp)
);

-- Totals (over/under) odds table - totals market from API
CREATE TABLE totals (
    total_id SERIAL PRIMARY KEY,
    game_id VARCHAR(100) REFERENCES games(game_id),
    bookmaker_id INTEGER REFERENCES bookmakers(bookmaker_id),
    total_line DECIMAL(10,2),                   -- Total points line
    over_price DECIMAL(10,2),                   -- Odds for over
    under_price DECIMAL(10,2),                  -- Odds for under
    last_update TIMESTAMP,                      -- API 'last_update' timestamp
    snapshot_timestamp TIMESTAMP NOT NULL,      -- When this odds snapshot was taken
    recorded_at TIMESTAMP DEFAULT NOW(),        -- When we fetched/recorded this data
    is_latest BOOLEAN DEFAULT TRUE,
    raw_outcomes JSONB,                         -- Store raw outcomes array
    created_at TIMESTAMP DEFAULT NOW(),

    -- Add constraint to prevent duplicate odds at same time
    UNIQUE(game_id, bookmaker_id, snapshot_timestamp)
);

-- API snapshots table - track historical data fetching
CREATE TABLE api_snapshots (
    snapshot_id SERIAL PRIMARY KEY,
    sport_key VARCHAR(50) NOT NULL,
    snapshot_timestamp TIMESTAMP NOT NULL,      -- Timestamp from historical API
    previous_timestamp TIMESTAMP,               -- Previous available snapshot
    next_timestamp TIMESTAMP,                   -- Next available snapshot
    games_count INTEGER DEFAULT 0,
    total_odds_count INTEGER DEFAULT 0,
    raw_response JSONB,                         -- Store full API response
    fetched_at TIMESTAMP DEFAULT NOW()
);

-- Bet outcomes table - calculated results for completed games
CREATE TABLE bet_outcomes (
    outcome_id SERIAL PRIMARY KEY,
    game_id VARCHAR(100) REFERENCES games(game_id),
    bookmaker_id INTEGER REFERENCES bookmakers(bookmaker_id),
    bet_type VARCHAR(20) NOT NULL,              -- moneyline, spread, total
    bet_selection VARCHAR(50),                  -- home, away, over, under
    outcome VARCHAR(20),                        -- win, loss, push
    reference_id INTEGER,                       -- ID from moneylines/spreads/totals
    odds_value DECIMAL(10,2),                   -- The odds at time of bet
    calculated_at TIMESTAMP DEFAULT NOW()
);

-- Performance indexes
CREATE INDEX idx_games_commence ON games(commence_time);
CREATE INDEX idx_games_status ON games(status);
CREATE INDEX idx_games_sport ON games(sport_id);

CREATE INDEX idx_moneylines_game ON moneylines(game_id);
CREATE INDEX idx_moneylines_bookmaker ON moneylines(bookmaker_id);
CREATE INDEX idx_moneylines_snapshot ON moneylines(snapshot_timestamp);
CREATE INDEX idx_moneylines_recorded ON moneylines(recorded_at);
CREATE INDEX idx_moneylines_latest ON moneylines(is_latest);
-- Composite indexes for line movement analysis
CREATE INDEX idx_moneylines_game_bookmaker_time ON moneylines(game_id, bookmaker_id, snapshot_timestamp);

CREATE INDEX idx_spreads_game ON spreads(game_id);
CREATE INDEX idx_spreads_bookmaker ON spreads(bookmaker_id);
CREATE INDEX idx_spreads_snapshot ON spreads(snapshot_timestamp);
CREATE INDEX idx_spreads_recorded ON spreads(recorded_at);
CREATE INDEX idx_spreads_latest ON spreads(is_latest);
-- Composite indexes for line movement analysis
CREATE INDEX idx_spreads_game_bookmaker_time ON spreads(game_id, bookmaker_id, snapshot_timestamp);

CREATE INDEX idx_totals_game ON totals(game_id);
CREATE INDEX idx_totals_bookmaker ON totals(bookmaker_id);
CREATE INDEX idx_totals_snapshot ON totals(snapshot_timestamp);
CREATE INDEX idx_totals_recorded ON totals(recorded_at);
CREATE INDEX idx_totals_latest ON totals(is_latest);
-- Composite indexes for line movement analysis
CREATE INDEX idx_totals_game_bookmaker_time ON totals(game_id, bookmaker_id, snapshot_timestamp);

CREATE INDEX idx_api_snapshots_sport ON api_snapshots(sport_key);
CREATE INDEX idx_api_snapshots_timestamp ON api_snapshots(snapshot_timestamp);

CREATE INDEX idx_bet_outcomes_game ON bet_outcomes(game_id);
CREATE INDEX idx_bet_outcomes_type ON bet_outcomes(bet_type);

-- Insert common sports (matches The Odds API sport keys)
INSERT INTO sports (sport_key, sport_title) VALUES
('americanfootball_nfl', 'NFL'),
('basketball_nba', 'NBA'),
('baseball_mlb', 'MLB'),
('icehockey_nhl', 'NHL'),
('soccer_epl', 'English Premier League'),
('americanfootball_ncaaf', 'NCAA Football'),
('basketball_ncaab', 'NCAA Basketball'),
('soccer_usa_mls', 'Major League Soccer'),
('tennis_wta', 'WTA Tennis'),
('tennis_atp', 'ATP Tennis');

-- Insert common bookmakers (based on The Odds API)
INSERT INTO bookmakers (bookmaker_key, bookmaker_title) VALUES
('draftkings', 'DraftKings'),
('fanduel', 'FanDuel'),
('betmgm', 'BetMGM'),
('caesars', 'Caesars Sportsbook'),
('pointsbet', 'PointsBet'),
('betrivers', 'BetRivers'),
('unibet_us', 'Unibet'),
('williamhill_us', 'Caesars (William Hill)'),
('bovada', 'Bovada'),
('mybookie', 'MyBookie'),
('superdraft', 'SuperDraft'),
('betway', 'Betway'),
('wynnbet', 'WynnBET');

-- Game results view for completed games
CREATE VIEW game_results AS
SELECT
    g.game_id,
    s.sport_title,
    g.commence_time,
    ht.team_name as home_team,
    at.team_name as away_team,
    g.home_score,
    g.away_score,
    g.status,
    g.completed_at,
    CASE
        WHEN g.home_score > g.away_score THEN ht.team_name
        WHEN g.away_score > g.home_score THEN at.team_name
        ELSE 'TIE'
    END as winner,
    (g.home_score + g.away_score) as total_score
FROM games g
JOIN sports s ON g.sport_id = s.sport_id
JOIN teams ht ON g.home_team_id = ht.team_id
JOIN teams at ON g.away_team_id = at.team_id
WHERE g.status = 'completed'
ORDER BY g.completed_at DESC;

-- Line movement analysis view for moneylines
CREATE VIEW moneyline_movements AS
SELECT
    m.game_id,
    s.sport_title,
    ht.team_name as home_team,
    at.team_name as away_team,
    g.commence_time,
    b.bookmaker_title,
    m.snapshot_timestamp,
    m.home_price,
    m.away_price,
    -- Calculate line movement from previous snapshot
    LAG(m.home_price) OVER (
        PARTITION BY m.game_id, m.bookmaker_id
        ORDER BY m.snapshot_timestamp
    ) as prev_home_price,
    LAG(m.away_price) OVER (
        PARTITION BY m.game_id, m.bookmaker_id
        ORDER BY m.snapshot_timestamp
    ) as prev_away_price,
    -- Calculate movement amount
    m.home_price - LAG(m.home_price) OVER (
        PARTITION BY m.game_id, m.bookmaker_id
        ORDER BY m.snapshot_timestamp
    ) as home_movement,
    m.away_price - LAG(m.away_price) OVER (
        PARTITION BY m.game_id, m.bookmaker_id
        ORDER BY m.snapshot_timestamp
    ) as away_movement,
    m.recorded_at
FROM moneylines m
JOIN games g ON m.game_id = g.game_id
JOIN sports s ON g.sport_id = s.sport_id
JOIN teams ht ON g.home_team_id = ht.team_id
JOIN teams at ON g.away_team_id = at.team_id
JOIN bookmakers b ON m.bookmaker_id = b.bookmaker_id
ORDER BY m.game_id, m.bookmaker_id, m.snapshot_timestamp;

-- Line movement analysis view for spreads
CREATE VIEW spread_movements AS
SELECT
    sp.game_id,
    s.sport_title,
    ht.team_name as home_team,
    at.team_name as away_team,
    g.commence_time,
    b.bookmaker_title,
    sp.snapshot_timestamp,
    sp.home_spread,
    sp.home_price,
    sp.away_spread,
    sp.away_price,
    -- Calculate line movement from previous snapshot
    LAG(sp.home_spread) OVER (
        PARTITION BY sp.game_id, sp.bookmaker_id
        ORDER BY sp.snapshot_timestamp
    ) as prev_home_spread,
    LAG(sp.home_price) OVER (
        PARTITION BY sp.game_id, sp.bookmaker_id
        ORDER BY sp.snapshot_timestamp
    ) as prev_home_price,
    -- Calculate movement amount
    sp.home_spread - LAG(sp.home_spread) OVER (
        PARTITION BY sp.game_id, sp.bookmaker_id
        ORDER BY sp.snapshot_timestamp
    ) as spread_movement,
    sp.home_price - LAG(sp.home_price) OVER (
        PARTITION BY sp.game_id, sp.bookmaker_id
        ORDER BY sp.snapshot_timestamp
    ) as price_movement,
    sp.recorded_at
FROM spreads sp
JOIN games g ON sp.game_id = g.game_id
JOIN sports s ON g.sport_id = s.sport_id
JOIN teams ht ON g.home_team_id = ht.team_id
JOIN teams at ON g.away_team_id = at.team_id
JOIN bookmakers b ON sp.bookmaker_id = b.bookmaker_id
ORDER BY sp.game_id, sp.bookmaker_id, sp.snapshot_timestamp;

-- Line movement analysis view for totals
CREATE VIEW total_movements AS
SELECT
    t.game_id,
    s.sport_title,
    ht.team_name as home_team,
    at.team_name as away_team,
    g.commence_time,
    b.bookmaker_title,
    t.snapshot_timestamp,
    t.total_line,
    t.over_price,
    t.under_price,
    -- Calculate line movement from previous snapshot
    LAG(t.total_line) OVER (
        PARTITION BY t.game_id, t.bookmaker_id
        ORDER BY t.snapshot_timestamp
    ) as prev_total_line,
    LAG(t.over_price) OVER (
        PARTITION BY t.game_id, t.bookmaker_id
        ORDER BY t.snapshot_timestamp
    ) as prev_over_price,
    -- Calculate movement amount
    t.total_line - LAG(t.total_line) OVER (
        PARTITION BY t.game_id, t.bookmaker_id
        ORDER BY t.snapshot_timestamp
    ) as line_movement,
    t.over_price - LAG(t.over_price) OVER (
        PARTITION BY t.game_id, t.bookmaker_id
        ORDER BY t.snapshot_timestamp
    ) as over_price_movement,
    t.recorded_at
FROM totals t
JOIN games g ON t.game_id = g.game_id
JOIN sports s ON g.sport_id = s.sport_id
JOIN teams ht ON g.home_team_id = ht.team_id
JOIN teams at ON g.away_team_id = at.team_id
JOIN bookmakers b ON t.bookmaker_id = b.bookmaker_id
ORDER BY t.game_id, t.bookmaker_id, t.snapshot_timestamp;