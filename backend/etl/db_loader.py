import os
import mysql.connector
from mysql.connector import Error

def get_db_connection():
    """Establishes a connection to the database."""
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_DATABASE")
        )
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error connecting to MySQL Database: {e}")
        return None

def get_puuids_from_db(limit=20):
    """Fetches a list of PUUIDs from the players table."""
    connection = get_db_connection()
    if not connection:
        return []

    cursor = connection.cursor()
    # Query to get PUUIDs, ordered by their rank, up to the specified limit
    query = "SELECT puuid FROM players ORDER BY leaderboardRank ASC LIMIT %s"
    
    try:
        cursor.execute(query, (limit,))
        # The result is a list of tuples, e.g., [('puuid1',), ('puuid2',)]. We need to flatten it.
        puuids = [item[0] for item in cursor.fetchall()]
        print(f"Successfully fetched {len(puuids)} PUUIDs from the database for match history lookup.")
        return puuids
    except Error as e:
        print(f"Error fetching PUUIDs from database: {e}")
        return []
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def load_player_data_to_db(player_data_list):
    """
    Clears the existing players table and loads the new top 100 list.
    """
    if not player_data_list:
        print("No player data to load.")
        return

    connection = get_db_connection()
    if not connection:
        return

    cursor = connection.cursor()
    
    try:
        # Clear the table to ensure a fresh leaderboard
        print("Clearing existing player leaderboard data...")
        cursor.execute("TRUNCATE TABLE players")
        print("Table cleared.")

        # Prepare the insert statement
        sql_insert_query = """
        INSERT INTO players (puuid, leaderboardRank, leaguePoints, `rank`, wins, losses, veteran, inactive, freshBlood, hotStreak)
        VALUES (%(puuid)s, %(leaderboardRank)s, %(leaguePoints)s, %(rank)s, %(wins)s, %(losses)s, %(veteran)s, %(inactive)s, %(freshBlood)s, %(hotStreak)s)
        """
        
        cursor.executemany(sql_insert_query, player_data_list)
        connection.commit()
        print(f"Successfully loaded {cursor.rowcount} records into the players table.")
    except Error as e:
        print(f"Error while inserting player data into MySQL: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def load_data_to_db(participant_data_list):
    """
    Loads a list of participant stats into the database.
    Uses an ON DUPLICATE KEY UPDATE clause to prevent duplicate entries.
    """
    if not participant_data_list:
        print("No participant stats data to load.")
        return

    connection = get_db_connection()
    if not connection:
        return

    cursor = connection.cursor()

    sql_insert_query = """
    INSERT INTO participant_stats (matchId, puuid, summonerName, championName, win, kills, deaths, assists)
    VALUES (%(matchId)s, %(puuid)s, %(summonerName)s, %(championName)s, %(win)s, %(kills)s, %(deaths)s, %(assists)s)
    ON DUPLICATE KEY UPDATE
    kills = VALUES(kills), deaths = VALUES(deaths), assists = VALUES(assists);
    """

    try:
        cursor.executemany(sql_insert_query, participant_data_list)
        connection.commit()
        print(f"Successfully loaded or updated {cursor.rowcount} participant stats records into the database.")
    except Error as e:
        print(f"Error while inserting participant stats into MySQL: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

