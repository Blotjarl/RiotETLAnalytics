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

-- Supports the daily retention prune (DELETE ... WHERE gamecreation < ...)
CREATE INDEX IF NOT EXISTS idx_matches_gamecreation ON matches (gamecreation);

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

-- Postgres has no CREATE POLICY IF NOT EXISTS, so DROP + CREATE is the
-- standard idiom to keep this file safely re-runnable end to end.
DROP POLICY IF EXISTS "Public read access" ON players;
CREATE POLICY "Public read access" ON players FOR SELECT USING (true);
DROP POLICY IF EXISTS "Public read access" ON matches;
CREATE POLICY "Public read access" ON matches FOR SELECT USING (true);
DROP POLICY IF EXISTS "Public read access" ON participant_stats;
CREATE POLICY "Public read access" ON participant_stats FOR SELECT USING (true);
DROP POLICY IF EXISTS "Public read access" ON champion_stats_by_tier;
CREATE POLICY "Public read access" ON champion_stats_by_tier FOR SELECT USING (true);
-- crawl_state is internal bookkeeping only, intentionally not exposed for public read.

GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT SELECT ON players, matches, participant_stats, champion_stats_by_tier TO anon, authenticated;

-- ============================================================
-- Phase 1: enrich participant_stats with per-participant detail
-- needed for per-role breakdowns, item/build insights, and
-- team-comp / item-conditioned win-probability models later.
-- ============================================================
ALTER TABLE participant_stats
    ADD COLUMN IF NOT EXISTS teamposition VARCHAR(10),   -- TOP/JUNGLE/MIDDLE/BOTTOM/UTILITY; NULL if Riot didn't assign one (seen as "" on remakes/edge cases even in ranked solo/duo)
    ADD COLUMN IF NOT EXISTS teamid INT,                 -- 100 or 200
    ADD COLUMN IF NOT EXISTS item0 INT,
    ADD COLUMN IF NOT EXISTS item1 INT,
    ADD COLUMN IF NOT EXISTS item2 INT,
    ADD COLUMN IF NOT EXISTS item3 INT,
    ADD COLUMN IF NOT EXISTS item4 INT,
    ADD COLUMN IF NOT EXISTS item5 INT,
    ADD COLUMN IF NOT EXISTS item6 INT,                  -- trinket slot
    ADD COLUMN IF NOT EXISTS summoner1id INT,
    ADD COLUMN IF NOT EXISTS summoner2id INT,
    ADD COLUMN IF NOT EXISTS goldearned INT,
    ADD COLUMN IF NOT EXISTS totalminionskilled INT,
    ADD COLUMN IF NOT EXISTS visionscore INT,
    ADD COLUMN IF NOT EXISTS totaldamagedealttochampions INT,
    ADD COLUMN IF NOT EXISTS perks JSONB;                -- raw {statPerks, styles} blob, intentionally unnormalized until a concrete rune insight needs one

-- ============================================================
-- Phase 1: derive `patch` (e.g. "14.14") from gameversion so it can
-- be grouped/filtered/indexed without recomputing it in every query
-- (site, future ML, and Tableau all need this). substring() with a
-- static POSIX pattern is IMMUTABLE, which STORED generated columns
-- require; returns NULL (not an error) if gameversion is NULL or
-- doesn't match, so this is safe against unexpected formats.
-- ============================================================
ALTER TABLE matches
    ADD COLUMN IF NOT EXISTS patch VARCHAR(10) GENERATED ALWAYS AS (substring(gameversion from '^\d+\.\d+')) STORED;

CREATE INDEX IF NOT EXISTS idx_matches_patch ON matches (patch);

-- ============================================================
-- champion_stats_by_patch: insert-only meta history, refreshed via
-- UPSERT (never TRUNCATEd) after each ETL run. Unlike
-- champion_stats_by_tier, a patch's row here keeps its last-computed
-- values once every match for that patch has aged out of the
-- MATCH_RETENTION_DAYS window (the join in refresh_champion_stats_by_patch
-- simply stops producing rows for it). Note the row's counts will
-- visibly shrink for the last few days of a patch's retention window
-- as its matches prune out day by day, before finally freezing --
-- this is expected, not a bug.
-- ============================================================
CREATE TABLE IF NOT EXISTS champion_stats_by_patch (
    patch VARCHAR(10) NOT NULL,
    tier VARCHAR(20) NOT NULL,
    championname VARCHAR(50) NOT NULL,
    playcount INT NOT NULL,
    wincount INT NOT NULL,
    winrate NUMERIC(5, 2) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (patch, tier, championname)
);

CREATE INDEX IF NOT EXISTS idx_champion_stats_by_patch_championname ON champion_stats_by_patch (championname);

-- ============================================================
-- player_lp_history: one append-only snapshot row per player per
-- day, training substrate for a future promotion-likelihood model.
-- No FK to players -- must survive a player being deleted from
-- players when they fall off the leaderboard. recorded_date is a
-- plain DEFAULT column (not GENERATED -- a timestamptz::date cast
-- depends on the session TimeZone setting and is only STABLE, not
-- IMMUTABLE, so Postgres would reject it as a generated column) used
-- to dedupe same-day snapshots if the leaderboard job is ever
-- triggered twice in one UTC day. No retention prune, intentionally:
-- ~11,000 rows/day of a handful of small columns is cheap, and this
-- table IS the historical record the model needs -- it should
-- outlive the 180-day raw-match retention horizon.
-- ============================================================
CREATE TABLE IF NOT EXISTS player_lp_history (
    id BIGSERIAL PRIMARY KEY,
    puuid VARCHAR(100) NOT NULL,
    tier VARCHAR(20) NOT NULL,
    "rank" VARCHAR(10),
    leaguepoints INT,
    wins INT,
    losses INT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    recorded_date DATE NOT NULL DEFAULT ((now() AT TIME ZONE 'utc')::date)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_player_lp_history_puuid_recorded_date ON player_lp_history (puuid, recorded_date);
CREATE INDEX IF NOT EXISTS idx_player_lp_history_puuid ON player_lp_history (puuid);

-- ============================================================
-- RLS + grants for the two new tables, same public-read pattern as
-- every other table above (crawl_state is still the only exception).
-- ============================================================
ALTER TABLE champion_stats_by_patch ENABLE ROW LEVEL SECURITY;
ALTER TABLE player_lp_history ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Public read access" ON champion_stats_by_patch;
CREATE POLICY "Public read access" ON champion_stats_by_patch FOR SELECT USING (true);
DROP POLICY IF EXISTS "Public read access" ON player_lp_history;
CREATE POLICY "Public read access" ON player_lp_history FOR SELECT USING (true);

GRANT SELECT ON champion_stats_by_patch, player_lp_history TO anon, authenticated;
