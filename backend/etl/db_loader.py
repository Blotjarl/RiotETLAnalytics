import os
import psycopg2
from psycopg2 import Error


def get_db_connection():
    """Establishes a connection to the Postgres database."""
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        print("Error connecting to Postgres database: DATABASE_URL environment variable is not set.")
        return None
    try:
        return psycopg2.connect(database_url)
    except Error as e:
        print(f"Error connecting to Postgres database: {e}")
        return None


def get_puuids_from_db(limit=20):
    """Fetches a list of PUUIDs from the players table, ordered by leaderboard rank."""
    connection = get_db_connection()
    if not connection:
        return []

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT puuid FROM players ORDER BY leaderboardrank ASC LIMIT %s",
                (limit,),
            )
            puuids = [row[0] for row in cursor.fetchall()]
            print(f"Successfully fetched {len(puuids)} PUUIDs from the database.")
            return puuids
    except Error as e:
        print(f"Error fetching PUUIDs from database: {e}")
        return []
    finally:
        connection.close()


def get_puuids_to_crawl(limit=1000):
    """
    Returns a rotating slice of player PUUIDs to crawl this run, prioritizing
    players that have never been crawled or were crawled longest ago. This is
    what lets a daily run cover a large player pool incrementally instead of
    re-fetching everyone every day.
    """
    connection = get_db_connection()
    if not connection:
        return []

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT p.puuid
                FROM players p
                LEFT JOIN crawl_state cs ON cs.puuid = p.puuid
                ORDER BY cs.last_crawled_at ASC NULLS FIRST, p.leaderboardrank ASC
                LIMIT %s
                """,
                (limit,),
            )
            puuids = [row[0] for row in cursor.fetchall()]
            print(f"Selected {len(puuids)} PUUIDs to crawl this run.")
            return puuids
    except Error as e:
        print(f"Error selecting PUUIDs to crawl: {e}")
        return []
    finally:
        connection.close()


def mark_puuids_crawled(puuids):
    """Records that the given PUUIDs were crawled just now, for rotation purposes."""
    if not puuids:
        return

    connection = get_db_connection()
    if not connection:
        return

    sql = """
    INSERT INTO crawl_state (puuid, last_crawled_at)
    VALUES (%s, now())
    ON CONFLICT (puuid) DO UPDATE SET last_crawled_at = EXCLUDED.last_crawled_at;
    """

    try:
        with connection.cursor() as cursor:
            cursor.executemany(sql, [(puuid,) for puuid in puuids])
        connection.commit()
        print(f"Marked {len(puuids)} PUUIDs as crawled.")
    except Error as e:
        print(f"Error updating crawl_state: {e}")
        connection.rollback()
    finally:
        connection.close()


def get_existing_match_ids(match_ids):
    """Returns the subset of the given match IDs that are already stored, for dedup."""
    if not match_ids:
        return set()

    connection = get_db_connection()
    if not connection:
        return set()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT matchid FROM matches WHERE matchid = ANY(%s)",
                (list(match_ids),),
            )
            return {row[0] for row in cursor.fetchall()}
    except Error as e:
        print(f"Error checking existing match IDs: {e}")
        return set()
    finally:
        connection.close()


def load_player_data_to_db(player_data_list):
    """
    Upserts the current Challenger/Grandmaster/Master leaderboard. Players who
    fell off the leaderboard are removed (cascading their crawl_state); players
    still present keep their row (and crawl_state) so the incremental crawl
    rotation isn't reset on every leaderboard refresh.
    """
    if not player_data_list:
        print("No player data to load.")
        return

    connection = get_db_connection()
    if not connection:
        return

    upsert_sql = """
    INSERT INTO players
        (puuid, platform, tier, leaderboardrank, leaguepoints, "rank", wins, losses, veteran, inactive, freshblood, hotstreak, last_updated)
    VALUES
        (%(puuid)s, %(platform)s, %(tier)s, %(leaderboardRank)s, %(leaguePoints)s, %(rank)s, %(wins)s, %(losses)s, %(veteran)s, %(inactive)s, %(freshBlood)s, %(hotStreak)s, now())
    ON CONFLICT (puuid) DO UPDATE SET
        platform = EXCLUDED.platform,
        tier = EXCLUDED.tier,
        leaderboardrank = EXCLUDED.leaderboardrank,
        leaguepoints = EXCLUDED.leaguepoints,
        "rank" = EXCLUDED."rank",
        wins = EXCLUDED.wins,
        losses = EXCLUDED.losses,
        veteran = EXCLUDED.veteran,
        inactive = EXCLUDED.inactive,
        freshblood = EXCLUDED.freshblood,
        hotstreak = EXCLUDED.hotstreak,
        last_updated = now();
    """

    try:
        with connection.cursor() as cursor:
            current_puuids = [p["puuid"] for p in player_data_list]
            cursor.execute(
                "DELETE FROM players WHERE puuid != ALL(%s)", (current_puuids,)
            )
            cursor.executemany(upsert_sql, player_data_list)
        connection.commit()
        print(f"Successfully upserted {len(player_data_list)} players into the leaderboard.")
    except Error as e:
        print(f"Error while upserting player data into Postgres: {e}")
        connection.rollback()
    finally:
        connection.close()


def record_lp_history(player_data_list):
    """
    Appends one row per player to player_lp_history for today (UTC). Skips a
    player already recorded today (ON CONFLICT on the puuid+recorded_date
    unique index) so a manual re-trigger of the leaderboard update doesn't
    create duplicate same-day snapshots. Never updates existing rows --
    intentionally append-only training substrate for a future promotion-
    likelihood model.
    """
    if not player_data_list:
        return

    connection = get_db_connection()
    if not connection:
        return

    sql = """
    INSERT INTO player_lp_history (puuid, tier, "rank", leaguepoints, wins, losses)
    VALUES (%(puuid)s, %(tier)s, %(rank)s, %(leaguePoints)s, %(wins)s, %(losses)s)
    ON CONFLICT (puuid, recorded_date) DO NOTHING;
    """

    try:
        with connection.cursor() as cursor:
            cursor.executemany(sql, player_data_list)
        connection.commit()
        print(f"Recorded LP history snapshot for {len(player_data_list)} players.")
    except Error as e:
        print(f"Error recording player_lp_history: {e}")
        connection.rollback()
    finally:
        connection.close()


def load_matches_to_db(match_list):
    """
    Upserts match-level metadata (one row per match).
    Returns True on success (including a no-op on an empty list), False on
    failure, so callers can avoid proceeding as if the load had succeeded.
    """
    if not match_list:
        return True

    connection = get_db_connection()
    if not connection:
        return False

    sql = """
    INSERT INTO matches
        (matchid, platformid, queueid, gamecreation, gameduration, gameversion, gamemode)
    VALUES
        (%(matchId)s, %(platformId)s, %(queueId)s, %(gameCreation)s, %(gameDuration)s, %(gameVersion)s, %(gameMode)s)
    ON CONFLICT (matchid) DO NOTHING;
    """

    try:
        with connection.cursor() as cursor:
            cursor.executemany(sql, match_list)
        connection.commit()
        print(f"Successfully loaded {len(match_list)} match records into the database.")
        return True
    except Error as e:
        print(f"Error while inserting match data into Postgres: {e}")
        connection.rollback()
        return False
    finally:
        connection.close()


def load_data_to_db(participant_data_list):
    """
    Loads participant stats. Matches must already be loaded (FK constraint).
    Returns True on success (including a no-op on an empty list), False on
    failure, so callers can avoid proceeding as if the load had succeeded.
    """
    if not participant_data_list:
        print("No participant stats data to load.")
        return True

    connection = get_db_connection()
    if not connection:
        return False

    sql = """
    INSERT INTO participant_stats
        (matchid, puuid, riotidgamename, riotidtagline, championname, win, kills, deaths, assists,
         teamposition, teamid, item0, item1, item2, item3, item4, item5, item6,
         summoner1id, summoner2id, goldearned, totalminionskilled, visionscore,
         totaldamagedealttochampions, firstbloodkill)
    VALUES
        (%(matchId)s, %(puuid)s, %(riotIdGameName)s, %(riotIdTagline)s, %(championName)s, %(win)s, %(kills)s, %(deaths)s, %(assists)s,
         %(teamPosition)s, %(teamId)s, %(item0)s, %(item1)s, %(item2)s, %(item3)s, %(item4)s, %(item5)s, %(item6)s,
         %(summoner1Id)s, %(summoner2Id)s, %(goldEarned)s, %(totalMinionsKilled)s, %(visionScore)s,
         %(totalDamageDealtToChampions)s, %(firstBloodKill)s)
    ON CONFLICT (matchid, puuid) DO UPDATE SET
        kills = EXCLUDED.kills,
        deaths = EXCLUDED.deaths,
        assists = EXCLUDED.assists,
        teamposition = EXCLUDED.teamposition,
        teamid = EXCLUDED.teamid,
        item0 = EXCLUDED.item0,
        item1 = EXCLUDED.item1,
        item2 = EXCLUDED.item2,
        item3 = EXCLUDED.item3,
        item4 = EXCLUDED.item4,
        item5 = EXCLUDED.item5,
        item6 = EXCLUDED.item6,
        summoner1id = EXCLUDED.summoner1id,
        summoner2id = EXCLUDED.summoner2id,
        goldearned = EXCLUDED.goldearned,
        totalminionskilled = EXCLUDED.totalminionskilled,
        visionscore = EXCLUDED.visionscore,
        totaldamagedealttochampions = EXCLUDED.totaldamagedealttochampions,
        firstbloodkill = EXCLUDED.firstbloodkill;
    """

    try:
        with connection.cursor() as cursor:
            cursor.executemany(sql, participant_data_list)
        connection.commit()
        print(f"Successfully loaded or updated {len(participant_data_list)} participant stats records.")
        return True
    except Error as e:
        print(f"Error while inserting participant stats into Postgres: {e}")
        connection.rollback()
        return False
    finally:
        connection.close()


def prune_old_matches(retention_days):
    """
    Deletes matches older than retention_days (and their participant_stats
    rows, via ON DELETE CASCADE), so the database doesn't grow forever.
    """
    connection = get_db_connection()
    if not connection:
        return

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM matches WHERE gamecreation < now() - make_interval(days => %s)",
                (retention_days,),
            )
            deleted = cursor.rowcount
        connection.commit()
        print(f"Pruned {deleted} matches older than {retention_days} days.")
    except Error as e:
        print(f"Error pruning old matches: {e}")
        connection.rollback()
    finally:
        connection.close()


def refresh_champion_stats_by_tier():
    """Rebuilds the champion_stats_by_tier insight table from raw match data."""
    connection = get_db_connection()
    if not connection:
        return

    sql = """
    TRUNCATE TABLE champion_stats_by_tier;
    INSERT INTO champion_stats_by_tier (tier, championname, playcount, wincount, winrate)
    SELECT
        p.tier,
        ps.championname,
        COUNT(*) AS play_count,
        SUM(CASE WHEN ps.win THEN 1 ELSE 0 END) AS win_count,
        ROUND(100.0 * SUM(CASE WHEN ps.win THEN 1 ELSE 0 END) / COUNT(*), 2) AS win_rate
    FROM participant_stats ps
    JOIN players p ON p.puuid = ps.puuid
    GROUP BY p.tier, ps.championname;
    """

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
        connection.commit()
        print("Refreshed champion_stats_by_tier.")
    except Error as e:
        print(f"Error refreshing champion_stats_by_tier: {e}")
        connection.rollback()
    finally:
        connection.close()


def refresh_champion_stats_by_patch():
    """
    Upserts the champion_stats_by_patch history table from current raw match
    data. Unlike champion_stats_by_tier this is never truncated: once every
    matches row for a given patch ages out of the retention prune, the join
    below stops producing rows for that patch and its history row simply
    stops being touched, freezing as a permanent record of that patch's meta.
    """
    connection = get_db_connection()
    if not connection:
        return

    sql = """
    INSERT INTO champion_stats_by_patch (patch, tier, championname, playcount, wincount, winrate, updated_at)
    SELECT
        m.patch,
        p.tier,
        ps.championname,
        COUNT(*) AS play_count,
        SUM(CASE WHEN ps.win THEN 1 ELSE 0 END) AS win_count,
        ROUND(100.0 * SUM(CASE WHEN ps.win THEN 1 ELSE 0 END) / COUNT(*), 2) AS win_rate,
        now()
    FROM participant_stats ps
    JOIN matches m ON m.matchid = ps.matchid
    JOIN players p ON p.puuid = ps.puuid
    WHERE m.patch IS NOT NULL
    GROUP BY m.patch, p.tier, ps.championname
    ON CONFLICT (patch, tier, championname) DO UPDATE SET
        playcount = EXCLUDED.playcount,
        wincount = EXCLUDED.wincount,
        winrate = EXCLUDED.winrate,
        updated_at = now();
    """

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
        connection.commit()
        print("Refreshed champion_stats_by_patch.")
    except Error as e:
        print(f"Error refreshing champion_stats_by_patch: {e}")
        connection.rollback()
    finally:
        connection.close()


def get_match_ids_missing_rich_fields(limit=8000):
    """
    Returns matchids whose participant_stats rows predate the Phase 1
    rich-field columns. goldEarned is never null in a real match-v5 response,
    so a null goldearned here reliably means "not yet backfilled". Used by
    the one-off backfill script; naturally resumable since each call returns
    the next not-yet-backfilled slice once earlier ones are loaded.
    """
    connection = get_db_connection()
    if not connection:
        return []

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT matchid
                FROM participant_stats
                WHERE goldearned IS NULL
                ORDER BY matchid
                LIMIT %s
                """,
                (limit,),
            )
            match_ids = [row[0] for row in cursor.fetchall()]
            print(f"Found {len(match_ids)} matches needing rich-field backfill.")
            return match_ids
    except Error as e:
        print(f"Error selecting matches needing backfill: {e}")
        return []
    finally:
        connection.close()


def refresh_champion_matchup_stats():
    """
    Rebuilds champion_matchup_stats (TRUNCATE + INSERT, like
    champion_stats_by_tier -- not UPSERT, to avoid the row-update bloat
    that contributed to a past production incident). Self-joins
    participant_stats to itself on (matchid, teamposition, opposite teamid)
    to find each participant's lane opponent. Uses
    idx_participant_stats_matchid_teamposition (schema.sql) to drive the
    join -- a plain (non-covering) index, since this only runs once a day
    from here, over a direct connection with a large timeout budget, not
    from live PostgREST traffic, so it doesn't need to guarantee an
    index-only scan the way a live, user-facing query would.
    """
    connection = get_db_connection()
    if not connection:
        return

    sql = """
    TRUNCATE TABLE champion_matchup_stats;
    INSERT INTO champion_matchup_stats
        (tier, teamposition, championname, opponent_championname, playcount, wincount, winrate)
    SELECT
        p.tier,
        ps1.teamposition,
        ps1.championname,
        ps2.championname,
        COUNT(*) AS playcount,
        SUM(CASE WHEN ps1.win THEN 1 ELSE 0 END) AS wincount,
        ROUND(100.0 * SUM(CASE WHEN ps1.win THEN 1 ELSE 0 END) / COUNT(*), 2) AS winrate
    FROM participant_stats ps1
    JOIN participant_stats ps2
      ON ps2.matchid = ps1.matchid
     AND ps2.teamposition = ps1.teamposition
     AND ps2.teamid != ps1.teamid
    JOIN players p ON p.puuid = ps1.puuid
    WHERE ps1.teamposition IS NOT NULL
    GROUP BY p.tier, ps1.teamposition, ps1.championname, ps2.championname;
    """

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            cursor.execute("ANALYZE champion_matchup_stats;")
        connection.commit()
        print("Refreshed champion_matchup_stats.")
    except Error as e:
        print(f"Error refreshing champion_matchup_stats: {e}")
        connection.rollback()
    finally:
        connection.close()


def refresh_champion_matchup_bias():
    """
    Rebuilds champion_matchup_bias (TRUNCATE + INSERT). Must run AFTER
    refresh_champion_matchup_stats(), since it reads from that table rather
    than from raw participant_stats -- running it first would compute bias
    numbers against stale matchup data.

    observed_winrate: the champion's actual win rate, naturally weighted by
    which opponents were actually faced (skewed by self-selected matchup
    picking, e.g. Rammus being preferentially picked into Yi/Irelia).
    expected_winrate: the same per-opponent win rates reweighted by how
    common each opponent is OVERALL in that role/tier (champion_stats_by_role),
    i.e. "what win rate this champion would have if matchups were random
    instead of chosen" -- standardization/reweighting, the technique behind
    opponent-adjusted sports stats. Computed from raw wincount/playcount
    (not the already-rounded winrate column) to avoid compounding rounding
    error. selection_effect = observed - expected is the quantified bias.
    """
    connection = get_db_connection()
    if not connection:
        return

    sql = """
    TRUNCATE TABLE champion_matchup_bias;
    INSERT INTO champion_matchup_bias
        (tier, teamposition, championname, games_played, observed_winrate, expected_winrate, selection_effect)
    SELECT
        m.tier,
        m.teamposition,
        m.championname,
        SUM(m.playcount) AS games_played,
        ROUND(100.0 * SUM(m.wincount) / NULLIF(SUM(m.playcount), 0), 2) AS observed_winrate,
        ROUND(
            SUM((m.wincount::numeric / NULLIF(m.playcount, 0)) * r.playcount) / NULLIF(SUM(r.playcount), 0) * 100.0,
        2) AS expected_winrate,
        ROUND(
            (100.0 * SUM(m.wincount) / NULLIF(SUM(m.playcount), 0))
            - (SUM((m.wincount::numeric / NULLIF(m.playcount, 0)) * r.playcount) / NULLIF(SUM(r.playcount), 0) * 100.0),
        2) AS selection_effect
    FROM champion_matchup_stats m
    JOIN champion_stats_by_role r
      ON r.tier = m.tier AND r.teamposition = m.teamposition AND r.championname = m.opponent_championname
    GROUP BY m.tier, m.teamposition, m.championname;
    """

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            cursor.execute("ANALYZE champion_matchup_bias;")
        connection.commit()
        print("Refreshed champion_matchup_bias.")
    except Error as e:
        print(f"Error refreshing champion_matchup_bias: {e}")
        connection.rollback()
    finally:
        connection.close()


def refresh_item_stats_by_tier():
    """
    Rebuilds item_stats_by_tier (TRUNCATE + INSERT). Item win rates
    aggregated across ALL champions per tier -- powers the "Any Champion"
    option on the Item Builds page. ETL-refreshed rather than a live view
    for the same reason as champion_matchup_stats: aggregating across every
    champion means scanning/unnesting the full participant_stats table for
    a tier, an unfiltered-aggregation shape that isn't safe to run live
    through PostgREST.
    """
    connection = get_db_connection()
    if not connection:
        return

    sql = """
    TRUNCATE TABLE item_stats_by_tier;
    INSERT INTO item_stats_by_tier (tier, itemid, playcount, wincount, winrate)
    SELECT
        p.tier,
        items.itemid,
        COUNT(*) AS playcount,
        SUM(CASE WHEN ps.win THEN 1 ELSE 0 END) AS wincount,
        ROUND(100.0 * SUM(CASE WHEN ps.win THEN 1 ELSE 0 END) / COUNT(*), 2) AS winrate
    FROM participant_stats ps
    JOIN players p ON p.puuid = ps.puuid
    CROSS JOIN LATERAL unnest(ARRAY[ps.item0, ps.item1, ps.item2, ps.item3, ps.item4, ps.item5]) AS items(itemid)
    WHERE items.itemid IS NOT NULL AND items.itemid != 0
    GROUP BY p.tier, items.itemid;
    """

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            cursor.execute("ANALYZE item_stats_by_tier;")
        connection.commit()
        print("Refreshed item_stats_by_tier.")
    except Error as e:
        print(f"Error refreshing item_stats_by_tier: {e}")
        connection.rollback()
    finally:
        connection.close()


def refresh_item_stats_by_tier_firstblood():
    """
    Rebuilds item_stats_by_tier_firstblood (TRUNCATE + INSERT). Same as
    refresh_item_stats_by_tier but split by firstbloodkill, for the "Any
    Champion" option on the Bias Insights item-snowball section. Rows where
    firstbloodkill hasn't been captured yet (NULL -- matches crawled before
    this column existed) are excluded rather than folded into the "no
    first blood" bucket, since they're unknown, not false -- also required
    since firstbloodkill is NOT NULL in this table's primary key.
    """
    connection = get_db_connection()
    if not connection:
        return

    sql = """
    TRUNCATE TABLE item_stats_by_tier_firstblood;
    INSERT INTO item_stats_by_tier_firstblood (tier, itemid, firstbloodkill, playcount, wincount, winrate)
    SELECT
        p.tier,
        items.itemid,
        ps.firstbloodkill,
        COUNT(*) AS playcount,
        SUM(CASE WHEN ps.win THEN 1 ELSE 0 END) AS wincount,
        ROUND(100.0 * SUM(CASE WHEN ps.win THEN 1 ELSE 0 END) / COUNT(*), 2) AS winrate
    FROM participant_stats ps
    JOIN players p ON p.puuid = ps.puuid
    CROSS JOIN LATERAL unnest(ARRAY[ps.item0, ps.item1, ps.item2, ps.item3, ps.item4, ps.item5]) AS items(itemid)
    WHERE items.itemid IS NOT NULL AND items.itemid != 0 AND ps.firstbloodkill IS NOT NULL
    GROUP BY p.tier, items.itemid, ps.firstbloodkill;
    """

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            cursor.execute("ANALYZE item_stats_by_tier_firstblood;")
        connection.commit()
        print("Refreshed item_stats_by_tier_firstblood.")
    except Error as e:
        print(f"Error refreshing item_stats_by_tier_firstblood: {e}")
        connection.rollback()
    finally:
        connection.close()
