import os
import sys
import threading
from flask import Flask, jsonify
from flask_cors import CORS

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from etl.db_loader import get_db_connection
from etl.main import run_etl_pipeline, run_player_leaderboard_update

app = Flask(__name__)
CORS(app)

@app.route('/api/run-etl', methods=['POST'])
def start_etl():
    """Triggers the MATCH HISTORY ETL pipeline in a background thread."""
    thread = threading.Thread(target=run_etl_pipeline)
    thread.start()
    return jsonify({"message": "Match history ETL process started successfully."}), 202

@app.route('/api/run-player-update', methods=['POST'])
def start_player_update():
    """Triggers the PLAYER LEADERBOARD update pipeline in a background thread."""
    thread = threading.Thread(target=run_player_leaderboard_update)
    thread.start()
    return jsonify({"message": "Player leaderboard update started successfully."}), 202

@app.route('/api/players', methods=['GET'])
def get_players():
    """Fetches the current top 100 players from the database."""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)
    # Order by the rank we assigned to ensure the list is sorted correctly
    query = "SELECT * FROM players ORDER BY leaderboardRank ASC"
    
    cursor.execute(query)
    players = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(players)

@app.route('/api/champion-stats', methods=['GET'])
def get_champion_stats():
    """Fetches aggregate champion statistics."""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)
    query = """
    SELECT
        championName,
        COUNT(championName) AS playCount,
        SUM(CASE WHEN win = 1 THEN 1 ELSE 0 END) AS winCount,
        (SUM(CASE WHEN win = 1 THEN 1 ELSE 0 END) / COUNT(championName)) * 100 AS winRate
    FROM
        participant_stats
    GROUP BY
        championName
    ORDER BY
        playCount DESC;
    """
    cursor.execute(query)
    champion_stats = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(champion_stats)

