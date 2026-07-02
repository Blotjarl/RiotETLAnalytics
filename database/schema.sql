-- Postgres schema for the riot-analytics-platform (Supabase).
-- Run this against your Supabase project's SQL editor (or `psql $DATABASE_URL -f schema.sql`).
--
-- Note: all identifiers are lowercase and unquoted on purpose -- Postgres folds
-- unquoted identifiers to lowercase, so this avoids any quoting mismatches
-- between this file and the Python ETL's SQL.

-- ============================================================
-- players: current Challenger + Grandmaster + Master leaderboard
-- ============================================================
CREATE TABLE IF NOT EXISTS players (
    puuid VARCHAR(100) NOT NULL,
    platform VARCHAR(10) NOT NULL DEFAULT 'na1',
    tier VARCHAR(20) NOT NULL,        -- CHALLENGER, GRANDMASTER, MASTER
    leaderboardrank INT,              -- rank within the combined C+GM+M pool, sorted by LP desc
    leaguepoints INT,
    "rank" VARCHAR(10),               -- division within tier, e.g. "I" (apex tiers are single-division); quoted, RANK is a reserved word
    wins INT,
    losses INT,
    veteran BOOLEAN,
    inactive BOOLEAN,
    freshblood BOOLEAN,
    hotstreak BOOLEAN,
    last_updated TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (puuid)
);

-- ============================================================
-- crawl_state: tracks when we last pulled each player's match
-- history, so the daily job can rotate through the pool instead
-- of re-fetching every player every run.
-- ============================================================
CREATE TABLE IF NOT EXISTS crawl_state (
    puuid VARCHAR(100) NOT NULL REFERENCES players(puuid) ON DELETE CASCADE,
    last_crawled_at TIMESTAMPTZ,
    PRIMARY KEY (puuid)
);

-- ============================================================
-- matches: one row per match (match-level metadata only)
-- ============================================================
CREATE TABLE IF NOT EXISTS matches (
    matchid VARCHAR(30) NOT NULL,     -- real Riot match id, e.g. "NA1_1234567890"
    platformid VARCHAR(10),
    queueid INT,
    gamecreation TIMESTAMPTZ,
    gameduration INT,                 -- seconds
    gameversion VARCHAR(30),          -- patch, e.g. "14.14.587.1234"
    gamemode VARCHAR(30),
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (matchid)
);

-- ============================================================
-- participant_stats: one row per player per match
-- ============================================================
CREATE TABLE IF NOT EXISTS participant_stats (
    matchid VARCHAR(30) NOT NULL REFERENCES matches(matchid) ON DELETE CASCADE,
    puuid VARCHAR(100) NOT NULL,
    riotidgamename VARCHAR(100),
    riotidtagline VARCHAR(20),
    championname VARCHAR(50),
    win BOOLEAN,
    kills INT,
    deaths INT,
    assists INT,
    -- A unique key to prevent duplicate entries for the same player in the same match
    PRIMARY KEY (matchid, puuid)
);

CREATE INDEX IF NOT EXISTS idx_participant_stats_puuid ON participant_stats (puuid);
CREATE INDEX IF NOT EXISTS idx_participant_stats_champion ON participant_stats (championname);

-- ============================================================
-- champion_stats_by_tier: materialized insight table, rebuilt
-- (TRUNCATE + INSERT) by the ETL job after each load. Broken out
-- by tier since apex-tier meta differs a lot from the overall
-- population.
-- ============================================================
CREATE TABLE IF NOT EXISTS champion_stats_by_tier (
    tier VARCHAR(20) NOT NULL,
    championname VARCHAR(50) NOT NULL,
    playcount INT NOT NULL,
    wincount INT NOT NULL,
    winrate NUMERIC(5, 2) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tier, championname)
);

-- ============================================================
-- Row-Level Security: expose all tables as public, read-only,
-- via Supabase's auto-generated REST API (anon key). The ETL job
-- connects with the Postgres connection string directly (not the
-- anon key), so it bypasses RLS and can write freely.
-- ============================================================
ALTER TABLE players ENABLE ROW LEVEL SECURITY;
ALTER TABLE crawl_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE participant_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE champion_stats_by_tier ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read access" ON players FOR SELECT USING (true);
CREATE POLICY "Public read access" ON matches FOR SELECT USING (true);
CREATE POLICY "Public read access" ON participant_stats FOR SELECT USING (true);
CREATE POLICY "Public read access" ON champion_stats_by_tier FOR SELECT USING (true);
-- crawl_state is internal bookkeeping only, intentionally not exposed for public read.

GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT SELECT ON players, matches, participant_stats, champion_stats_by_tier TO anon, authenticated;
