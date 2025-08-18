import os
import requests
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
RIOT_API_KEY = os.getenv("RIOT_API_KEY")

# Define our regions
PLATFORM_REGION = "na1"
ROUTING_REGION = "americas"

def get_challenger_players():
    """Fetches the list of Challenger league players (with their PUUIDs)."""
    url = f"https://{PLATFORM_REGION}.api.riotgames.com/lol/league/v4/challengerleagues/by-queue/RANKED_SOLO_5x5"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    
    print("Fetching Challenger player list...")
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        league_data = response.json()
        print("Successfully fetched player data.")
        return league_data.get('entries', [])
    except requests.exceptions.RequestException as e:
        print(f"An error occurred fetching challenger list: {e}")
        return None

def get_account_by_puuid(puuid):
    """Fetches account details (gameName, tagLine) using their PUUID."""
    # NOTE: The Account API uses the continental routing value (americas, europe, asia)
    url = f"https://{ROUTING_REGION}.api.riotgames.com/riot/account/v1/accounts/by-puuid/{puuid}"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    
    try:
        response = requests.get(url, headers=headers)
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
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None

def get_match_ids_by_puuid(puuid, count=20):
    """Fetches a list of match IDs for a given PUUID."""
    # The Match API also uses the continental routing value
    url = f"https://{ROUTING_REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"

    # We can add parameters to the request, like the number of matches to fetch
    params = {
        "start": 0,
        "count": count,
    }
    headers = {"X-Riot-Token": RIOT_API_KEY}

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None

# This block allows us to test the functions directly
if __name__ == "__main__":
    # --- Step 1: Get Challenger Players ---
    challengers = get_challenger_players()
    if not challengers:
        print("Could not fetch challenger list. Exiting.")
        exit()

    sorted_challengers = sorted(challengers, key=lambda x: x['leaguePoints'], reverse=True)

    # --- Step 2: Get Unique Match IDs ---
    all_match_ids = set()
    players_to_check = sorted_challengers[:100]

    print(f"\nFetching match histories for the top {len(players_to_check)} players...")
    for player_data in players_to_check:
        match_ids = get_match_ids_by_puuid(player_data['puuid'], count=20)
        if match_ids:
            all_match_ids.update(match_ids)
        time.sleep(0.05) # Small delay

    print(f"\nFound a total of {len(all_match_ids)} unique match IDs.")

    # --- Step 3: Get Detailed Data for Each Match ---
    match_data_list = []
    # We only need the first 1000 unique matches
    unique_matches_to_fetch = list(all_match_ids)[:1000]

    print(f"\nFetching detailed data for {len(unique_matches_to_fetch)} matches... (This may take a few minutes)")

    for i, match_id in enumerate(unique_matches_to_fetch):
        # Print progress every 25 matches
        if (i + 1) % 25 == 0:
            print(f"  ...fetched {i + 1}/{len(unique_matches_to_fetch)}")

        match_data = get_match_data_by_id(match_id)
        if match_data:
            match_data_list.append(match_data)

        time.sleep(0.1) # Respect rate limits

    print(f"\nSuccessfully fetched data for {len(match_data_list)} matches.")
    
    import json
    with open('raw_matches.json', 'w') as f:
        json.dump(match_data_list, f)
    print("Saved raw match data to 'raw_matches.json'")

    # You can uncomment the line below to inspect the data of the first match
    # import json
    # print(json.dumps(match_data_list[0], indent=2))