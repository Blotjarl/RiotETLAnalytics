import os
import sys
import threading # Import the threading library
from flask import Flask, jsonify
from flask_cors import CORS

# This allows the script to import from the 'etl' folder
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from etl.db_loader import get_db_connection
from etl.main import run_etl_pipeline # Import your main ETL function

app = Flask(__name__)
CORS(app)

# --- NEW: Endpoint to trigger the ETL process ---
@app.route('/api/run-etl', methods=['POST'])
def start_etl():
    """
    Triggers the ETL pipeline in a background thread.
    """
    # Running the ETL in a thread prevents the API from timing out,
    # as the process takes several minutes.
    thread = threading.Thread(target=run_etl_pipeline)
    thread.start()
    
    return jsonify({"message": "ETL process started successfully in the background."}), 202

# --- Your existing data endpoints ---
@app.route('/api/champion-stats', methods=['GET'])
def get_champion_stats():
    # ... (this function remains unchanged)
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

# Add your get_player_stats function here if you are using it