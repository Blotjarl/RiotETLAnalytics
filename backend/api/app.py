import os
import sys
from flask import Flask, jsonify
from flask_cors import CORS

# This is a bit of a trick to allow this script to import from the 'etl' folder
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from etl.db_loader import get_db_connection

# Initialize the Flask app
app = Flask(__name__)
# Enable CORS for all routes, allowing your React app to fetch data
CORS(app)

@app.route('/api/champion-stats', methods=['GET'])
def get_champion_stats():
    """
    API endpoint to get aggregated champion play rates and win rates.
    """
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor(dictionary=True) # dictionary=True returns rows as dicts

    # This SQL query calculates the total plays, wins, and win rate for each champion
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



# This allows you to run the app directly for testing
if __name__ == '__main__':
    app.run(debug=True)