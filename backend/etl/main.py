import time
from .riot_api import get_challenger_players, get_match_ids_by_puuid, get_match_data_by_id
from .data_transformer import transform_raw_match_data
from .db_loader import load_data_to_db

def run_etl_pipeline():
    """
    Runs the full ETL pipeline:
    1. Extracts live data from the Riot API.
    2. Transforms the raw data.
    3. Loads the clean data into the database.
    """
    
    # --- 1. EXTRACT (from live API) ---
    print("--- Starting ETL Pipeline: EXTRACT ---")
    
    # Get Challenger players to find their PUUIDs
    challengers = get_challenger_players()
    if not challengers:
        print("ETL Aborted: Could not fetch challenger list.")
        return

    sorted_challengers = sorted(challengers, key=lambda x: x['leaguePoints'], reverse=True)
    
    # Get a unique set of recent match IDs from the top players
    all_match_ids = set()
    players_to_check = sorted_challengers[:100]
    
    print(f"Fetching match histories for top {len(players_to_check)} players...")
    for player_data in players_to_check:
        match_ids = get_match_ids_by_puuid(player_data['puuid'], count=20)
        if match_ids:
            all_match_ids.update(match_ids)
        time.sleep(0.05) # Small delay to respect rate limits
    
    # Fetch detailed data for each unique match
    raw_match_data = []
    unique_matches_to_fetch = list(all_match_ids)[:1000] # Limit to 1000

    print(f"Fetching detailed data for up to {len(unique_matches_to_fetch)} matches...")
    for i, match_id in enumerate(unique_matches_to_fetch):
        if (i + 1) % 50 == 0:
            print(f"  ...progress: {i + 1}/{len(unique_matches_to_fetch)}")

        match_data = get_match_data_by_id(match_id)
        if match_data:
            raw_match_data.append(match_data)
        time.sleep(0.1) # Respect rate limits

    print(f"Extraction complete. Found data for {len(raw_match_data)} matches.")

    # --- 2. TRANSFORM ---
    print("\n--- Phase: TRANSFORM ---")
    transformed_data = transform_raw_match_data(raw_match_data)
    
    # --- 3. LOAD ---
    print("\n--- Phase: LOAD ---")
    load_data_to_db(transformed_data)

    print("\nETL Pipeline finished.")

if __name__ == "__main__":
    run_etl_pipeline()