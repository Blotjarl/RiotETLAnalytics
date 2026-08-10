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

-- ============================================================
-- Phase 2: frontend-facing views. Plain (not materialized) views on
-- top of the raw tables -- always fresh, no ETL refresh code to
-- maintain, and they don't fork the data model that Tableau will
-- connect to directly later. Views don't inherit RLS/grants from
-- their underlying tables, so each needs an explicit GRANT; each
-- also opts into security_invoker (Postgres 15+) so it evaluates
-- as the querying role rather than the view owner -- a no-op today
-- since every underlying table here is already public-read, but the
-- correct default going forward.
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_participant_stats_teamposition ON participant_stats (teamposition);

-- participant_stats is the hot table behind every query above: role-
-- filtered aggregation (champion_stats_by_role) and per-puuid identity
-- resolution (player_current_identity) both join/filter through it by
-- puuid. Without a covering index, each matched row needs a heap fetch,
-- which is prohibitively slow on a resource-constrained instance at this
-- table's row count -- confirmed via EXPLAIN ANALYZE: heap-fetching a
-- ~300-player role query took 4-7s (occasionally exceeding PostgREST's
-- statement timeout entirely); an index-only scan via this covering
-- index brought the same query under 500ms. Requires VACUUM ANALYZE
-- participant_stats for the visibility map to actually let Postgres skip
-- the heap -- VACUUM cannot run inside a transaction block, so it can't
-- be included in this script; run it manually, separately, after
-- applying this file if it hasn't been run recently.
DROP INDEX IF EXISTS idx_participant_stats_puuid_covering;
CREATE INDEX idx_participant_stats_puuid_covering
ON participant_stats (puuid) INCLUDE (matchid, teamposition, championname, win, riotidgamename, riotidtagline);

CREATE OR REPLACE VIEW champion_stats_by_role
WITH (security_invoker = true) AS
SELECT
    ps.teamposition,
    p.tier,
    ps.championname,
    COUNT(*) AS playcount,
    SUM(CASE WHEN ps.win THEN 1 ELSE 0 END) AS wincount,
    ROUND(100.0 * SUM(CASE WHEN ps.win THEN 1 ELSE 0 END) / COUNT(*), 2) AS winrate
FROM participant_stats ps
JOIN players p ON p.puuid = ps.puuid
WHERE ps.teamposition IS NOT NULL
GROUP BY ps.teamposition, p.tier, ps.championname;

GRANT SELECT ON champion_stats_by_role TO anon, authenticated;

-- item0-item5 unnested (item6/trinket intentionally excluded); 0 is
-- Riot's "empty slot" sentinel, not a real item id, so it's filtered
-- out alongside NULL.
CREATE OR REPLACE VIEW item_build_stats
WITH (security_invoker = true) AS
SELECT
    p.tier,
    ps.championname,
    items.itemid,
    COUNT(*) AS playcount,
    SUM(CASE WHEN ps.win THEN 1 ELSE 0 END) AS wincount,
    ROUND(100.0 * SUM(CASE WHEN ps.win THEN 1 ELSE 0 END) / COUNT(*), 2) AS winrate
FROM participant_stats ps
JOIN players p ON p.puuid = ps.puuid
CROSS JOIN LATERAL unnest(ARRAY[ps.item0, ps.item1, ps.item2, ps.item3, ps.item4, ps.item5]) AS items(itemid)
WHERE items.itemid IS NOT NULL AND items.itemid != 0
GROUP BY p.tier, ps.championname, items.itemid;

GRANT SELECT ON item_build_stats TO anon, authenticated;

-- players has no display-name column at all (only puuid), so this
-- resolves each puuid's most recently seen Riot ID from match data.
-- Known limitation: only players whose match history has already
-- been crawled will resolve to a name (the daily rotation covers the
-- full player pool over multiple weeks) -- callers must treat a miss
-- as "name not yet known", not an error.
CREATE OR REPLACE VIEW player_current_identity
WITH (security_invoker = true) AS
SELECT DISTINCT ON (ps.puuid) ps.puuid, ps.riotidgamename, ps.riotidtagline
FROM participant_stats ps
JOIN matches m ON m.matchid = ps.matchid
ORDER BY ps.puuid, m.gamecreation DESC;

GRANT SELECT ON player_current_identity TO anon, authenticated;

-- ============================================================
-- Phase 3: bias-corrected insights. Two distinct statistical biases
-- in raw win-rate stats: (1) champion matchup selection bias -- a
-- champion picked deliberately into favorable matchups (e.g. a
-- counter-pick) has an inflated aggregate win rate that partly
-- reflects matchup selection, not raw strength; (2) item snowball /
-- reverse-causation bias -- some items look strong because players
-- buy them after already snowballing, not because the item caused
-- the win.
-- ============================================================
ALTER TABLE participant_stats
    ADD COLUMN IF NOT EXISTS firstbloodkill BOOLEAN;

-- Covering index for the lane-opponent self-join below (champion_matchup_stats'
-- refresh). Neither the PK (matchid, puuid) nor idx_participant_stats_puuid_covering
-- help here -- both are keyed off puuid, but this join's condition is on
-- (matchid, teamposition, teamid). Without a dedicated index, each row's lane-
-- opponent lookup needs a heap fetch per candidate row -- the same pattern that
-- caused a production incident on champion_stats_by_role earlier. (matchid,
-- teamposition) as leading key columns makes the opponent lookup an index
-- condition landing on ~2 rows directly; teamid/championname/win are INCLUDEd
-- so the scan can be index-only. Run ANALYZE participant_stats after applying
-- this file (ANALYZE, unlike VACUUM, is safe inside a transaction, but this
-- script doesn't run it automatically since it only takes effect once real
-- data exists).
CREATE INDEX IF NOT EXISTS idx_participant_stats_matchid_teamposition
ON participant_stats (matchid, teamposition) INCLUDE (teamid, championname, win);

-- champion_matchup_stats / champion_matchup_bias are ETL-refreshed tables
-- (TRUNCATE + INSERT, like champion_stats_by_tier), NOT plain views, and
-- deliberately not UPSERTed. Reasoning: the bias-insights page's overview
-- needs ALL champions in a tier/role at once (the whole point is comparing
-- selection_effect across champions), unlike every other Phase 2 view which
-- is always queried pre-filtered to one champion. A live view here would
-- run the self-join unfiltered on every request, subject to PostgREST's
-- statement timeout -- structurally the same shape that caused the earlier
-- incident. Refreshing once/day via the ETL's direct DATABASE_URL connection
-- (bypassing PostgREST's timeout, same as every other refresh_* job)
-- sidesteps this entirely. TRUNCATE+INSERT (not UPSERT) avoids the row-
-- update bloat that compounded the earlier incident. Each table's PK
-- doubles as the index its own query pattern needs.
CREATE TABLE IF NOT EXISTS champion_matchup_stats (
    tier VARCHAR(20) NOT NULL,
    teamposition VARCHAR(10) NOT NULL,
    championname VARCHAR(50) NOT NULL,
    opponent_championname VARCHAR(50) NOT NULL,
    playcount INT NOT NULL,
    wincount INT NOT NULL,
    winrate NUMERIC(5, 2) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tier, teamposition, championname, opponent_championname)
);

-- observed_winrate: this champion's actual aggregate win rate, naturally
-- weighted by which opponents were actually faced (skewed by self-selected
-- matchup picking). expected_winrate: the SAME per-opponent win rates,
-- reweighted by how common each opponent is OVERALL in that role/tier (from
-- champion_stats_by_role) rather than by how often this champion specifically
-- faced them -- i.e. "what win rate would this champion have if matchups
-- were random instead of chosen." selection_effect = observed - expected is
-- the quantified matchup-selection bias (standardization/reweighting, the
-- technique behind opponent-adjusted sports stats).
CREATE TABLE IF NOT EXISTS champion_matchup_bias (
    tier VARCHAR(20) NOT NULL,
    teamposition VARCHAR(10) NOT NULL,
    championname VARCHAR(50) NOT NULL,
    games_played INT NOT NULL,
    observed_winrate NUMERIC(5, 2) NOT NULL,
    expected_winrate NUMERIC(5, 2) NOT NULL,
    selection_effect NUMERIC(5, 2) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tier, teamposition, championname)
);

ALTER TABLE champion_matchup_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE champion_matchup_bias ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Public read access" ON champion_matchup_stats;
CREATE POLICY "Public read access" ON champion_matchup_stats FOR SELECT USING (true);
DROP POLICY IF EXISTS "Public read access" ON champion_matchup_bias;
CREATE POLICY "Public read access" ON champion_matchup_bias FOR SELECT USING (true);

GRANT SELECT ON champion_matchup_stats, champion_matchup_bias TO anon, authenticated;

-- Item snowball-bias proxy: item win rates split by whether the buyer got
-- first blood, as a partial signal for "was already ahead early" vs "bought
-- it more speculatively". This is a plain view, not a table -- unlike the
-- matchup-bias pair above, its access pattern is always pre-filtered to one
-- tier+championname, identical to the already-proven-safe item_build_stats.
-- Explicitly a PARTIAL proxy, not a causal fix: the fully rigorous version
-- needs Riot's match-timeline API (game state at the moment of purchase),
-- which this codebase doesn't fetch.
-- firstbloodkill IS NOT NULL excludes matches crawled before this column
-- existed (their first-blood status is genuinely unknown, not false) --
-- without this filter those rows would silently get folded into whichever
-- bucket a truthy/falsy check in the frontend happened to treat NULL as.
CREATE OR REPLACE VIEW item_build_stats_by_firstblood
WITH (security_invoker = true) AS
SELECT
    p.tier,
    ps.championname,
    items.itemid,
    ps.firstbloodkill,
    COUNT(*) AS playcount,
    SUM(CASE WHEN ps.win THEN 1 ELSE 0 END) AS wincount,
    ROUND(100.0 * SUM(CASE WHEN ps.win THEN 1 ELSE 0 END) / COUNT(*), 2) AS winrate
FROM participant_stats ps
JOIN players p ON p.puuid = ps.puuid
CROSS JOIN LATERAL unnest(ARRAY[ps.item0, ps.item1, ps.item2, ps.item3, ps.item4, ps.item5]) AS items(itemid)
WHERE items.itemid IS NOT NULL AND items.itemid != 0 AND ps.firstbloodkill IS NOT NULL
GROUP BY p.tier, ps.championname, items.itemid, ps.firstbloodkill;

GRANT SELECT ON item_build_stats_by_firstblood TO anon, authenticated;

-- ============================================================
-- item_stats_by_tier / item_stats_by_tier_firstblood: item win rates
-- aggregated across ALL champions, for the "Any Champion" option on the
-- Item Builds and Bias Insights pages. ETL-refreshed (TRUNCATE + INSERT),
-- not views -- aggregating across every champion requires scanning and
-- unnesting the full participant_stats table for a tier, the same
-- unfiltered-aggregation shape that timed out earlier today when queried
-- live through PostgREST. Both are small (bounded by ~250 items), so an
-- unfiltered-by-champion query against these specific tables is cheap.
-- ============================================================
CREATE TABLE IF NOT EXISTS item_stats_by_tier (
    tier VARCHAR(20) NOT NULL,
    itemid INT NOT NULL,
    playcount INT NOT NULL,
    wincount INT NOT NULL,
    winrate NUMERIC(5, 2) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tier, itemid)
);

-- firstbloodkill excluded (not just NULLed) for rows where it's unknown --
-- same reasoning as item_build_stats_by_firstblood above, and NULL can't
-- participate in a PRIMARY KEY anyway.
CREATE TABLE IF NOT EXISTS item_stats_by_tier_firstblood (
    tier VARCHAR(20) NOT NULL,
    itemid INT NOT NULL,
    firstbloodkill BOOLEAN NOT NULL,
    playcount INT NOT NULL,
    wincount INT NOT NULL,
    winrate NUMERIC(5, 2) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tier, itemid, firstbloodkill)
);

ALTER TABLE item_stats_by_tier ENABLE ROW LEVEL SECURITY;
ALTER TABLE item_stats_by_tier_firstblood ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Public read access" ON item_stats_by_tier;
CREATE POLICY "Public read access" ON item_stats_by_tier FOR SELECT USING (true);
DROP POLICY IF EXISTS "Public read access" ON item_stats_by_tier_firstblood;
CREATE POLICY "Public read access" ON item_stats_by_tier_firstblood FOR SELECT USING (true);

GRANT SELECT ON item_stats_by_tier, item_stats_by_tier_firstblood TO anon, authenticated;
