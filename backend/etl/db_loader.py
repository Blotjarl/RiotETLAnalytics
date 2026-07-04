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
        (matchid, puuid, riotidgamename, riotidtagline, championname, win, kills, deaths, assists)
    VALUES
        (%(matchId)s, %(puuid)s, %(riotIdGameName)s, %(riotIdTagline)s, %(championName)s, %(win)s, %(kills)s, %(deaths)s, %(assists)s)
    ON CONFLICT (matchid, puuid) DO UPDATE SET
        kills = EXCLUDED.kills, deaths = EXCLUDED.deaths, assists = EXCLUDED.assists;
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
