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

def load_data_to_db(participant_data_list):
    """
    Loads a list of participant stats into the database.
    Uses an ON DUPLICATE KEY UPDATE clause to prevent duplicate entries.
    """
    if not participant_data_list:
        print("No data to load.")
        return

    connection = get_db_connection()
    if not connection:
        return

    cursor = connection.cursor()

    # This SQL statement will insert a new row, but if a row with the same
    # primary key (matchId, puuid) already exists, it will update it instead.
    sql_insert_query = """
    INSERT INTO participant_stats (matchId, puuid, summonerName, championName, win, kills, deaths, assists, lp, ladderRank)
    VALUES (%(matchId)s, %(puuid)s, %(summonerName)s, %(championName)s, %(win)s, %(kills)s, %(deaths)s, %(assists)s, %(lp)s, %(ladderRank)s)
    ON DUPLICATE KEY UPDATE
    kills = VALUES(kills), deaths = VALUES(deaths), assists = VALUES(assists);
    """

    try:
        cursor.executemany(sql_insert_query, participant_data_list)
        connection.commit()
        print(f"Successfully loaded or updated {cursor.rowcount} records into the database.")
    except Error as e:
        print(f"Error while inserting data into MySQL: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()