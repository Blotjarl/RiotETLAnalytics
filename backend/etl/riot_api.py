import os
import time
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
RIOT_API_KEY = os.getenv("RIOT_API_KEY")

# Define our regions
PLATFORM_REGION = "na1"
ROUTING_REGION = "americas"

# Define the rate limit delay in seconds
RATE_LIMIT_DELAY = 1.2

def get_challenger_players():
    """Fetches the list of Challenger league players."""
    url = f"https://{PLATFORM_REGION}.api.riotgames.com/lol/league/v4/challengerleagues/by-queue/RANKED_SOLO_5x5"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    
    print("Fetching Challenger player list...")
    try:
        response = requests.get(url, headers=headers)
        time.sleep(RATE_LIMIT_DELAY) # Enforce rate limit
        response.raise_for_status()
        league_data = response.json()
        print("Successfully fetched player data.")
        return league_data.get('entries', [])
    except requests.exceptions.RequestException as e:
        print(f"An error occurred fetching challenger list: {e}")
        return None

def get_top_100_player_data():
    """
    Orchestrates the new, simplified process for fetching top player data.
    This is much faster and more reliable as it uses a single API call.
    """
    print("--- Starting Top 100 Player Data Fetch ---")
    
    challengers = get_challenger_players()
    if not challengers:
        print("Could not fetch challenger list. Aborting.")
        return []

    # Sort players by league points in descending order
    sorted_challengers = sorted(challengers, key=lambda x: x.get('leaguePoints', 0), reverse=True)
    
    # Take the top 100
    top_100_challengers = sorted_challengers[:100]
    print(f"Successfully sorted and selected top {len(top_100_challengers)} players.")

    processed_player_data = []
    
    # Process the data into the format for our database
    for i, player_data in enumerate(top_100_challengers):
        # We must ensure the 'puuid' key exists, otherwise the data is unusable
        if 'puuid' not in player_data:
            print(f"  -> Skipping an entry at rank {i+1}, 'puuid' is missing.")
            continue

        processed_player_data.append({
            "puuid": player_data['puuid'],
            "leaderboardRank": i + 1, # Add the 1-100 rank
            "leaguePoints": player_data.get('leaguePoints', 0),
            "rank": player_data.get('rank', 'N/A'),
            "wins": player_data.get('wins', 0),
            "losses": player_data.get('losses', 0),
            "veteran": player_data.get('veteran', False),
            "inactive": player_data.get('inactive', False),
            "freshBlood": player_data.get('freshBlood', False),
            "hotStreak": player_data.get('hotStreak', False),
        })

    print(f"\n--- Successfully processed {len(processed_player_data)} players. ---")
    return processed_player_data

# The functions below are kept for the Match History ETL pipeline
def get_summoner_by_id(summoner_id):
    """Fetches summoner details (including PUUID) using their summonerId."""
    url = f"https://{PLATFORM_REGION}.api.riotgames.com/lol/summoner/v4/summoners/{summoner_id}"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    try:
        response = requests.get(url, headers=headers)
        time.sleep(RATE_LIMIT_DELAY) # Enforce rate limit
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None

def get_match_data_by_id(match_id):
    """Fetches the detailed data for a single match."""
    url = f"https://{ROUTING_REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    try:
        response = requests.get(url, headers=headers)
        time.sleep(RATE_LIMIT_DELAY) # Enforce rate limit
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None

def get_match_ids_by_puuid(puuid, count=20):
    """Fetches a list of match IDs for a given PUUID."""
    url = f"https://{ROUTING_REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
    params = {"start": 0, "count": count}
    headers = {"X-Riot-Token": RIOT_API_KEY}
    try:
        response = requests.get(url, params=params, headers=headers)
        time.sleep(RATE_LIMIT_DELAY) # Enforce rate limit
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None

