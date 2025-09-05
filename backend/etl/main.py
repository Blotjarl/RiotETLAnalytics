from .riot_api import get_top_100_player_data, get_match_ids_by_puuid, get_match_data_by_id
from .data_transformer import transform_raw_match_data
from .db_loader import load_data_to_db, load_player_data_to_db, get_puuids_from_db

def run_player_leaderboard_update():
    """
    Runs the pipeline to fetch and store the top 100 players.
    """
    print("\n--- Starting Player Leaderboard Update Pipeline ---")
    player_data = get_top_100_player_data()
    load_player_data_to_db(player_data)
    print("\n--- Player Leaderboard Update Finished. ---")

def run_etl_pipeline():
    """
    Runs the full ETL pipeline for match data using PUUIDs from our database.
    """
    print("\n--- Starting Match History ETL Pipeline ---")
    
    # --- 1. EXTRACT ---
    print("--- Phase: EXTRACT ---")
    
    # Get PUUIDs of the top players we just stored in the database.
    # We limit this to a small number to avoid making thousands of API calls during testing.
    # You can increase this limit later.
    player_puuids = get_puuids_from_db(limit=20) 
    if not player_puuids:
        print("ETL Aborted: Could not fetch PUUIDs from the database.")
        return

    # Get a unique set of recent match IDs from these players
    all_match_ids = set()
    print(f"Fetching match histories for top {len(player_puuids)} players...")
    for puuid in player_puuids:
        # Fetch the last 10 match IDs for each player
        match_ids = get_match_ids_by_puuid(puuid, count=10)
        if match_ids:
            all_match_ids.update(match_ids)
    
    # Fetch detailed data for each unique match
    raw_match_data = []
    unique_matches_to_fetch = list(all_match_ids)

    print(f"Found {len(unique_matches_to_fetch)} unique matches. Fetching detailed data...")
    for i, match_id in enumerate(unique_matches_to_fetch):
        # Print progress to the console
        if (i + 1) % 25 == 0:
            print(f"  ...progress: {i + 1}/{len(unique_matches_to_fetch)}")
            
        match_data = get_match_data_by_id(match_id)
        if match_data:
            raw_match_data.append(match_data)

    print(f"Extraction complete. Found data for {len(raw_match_data)} matches.")

    # --- 2. TRANSFORM ---
    print("\n--- Phase: TRANSFORM ---")
    transformed_data = transform_raw_match_data(raw_match_data)
    
    # --- 3. LOAD ---
    print("\n--- Phase: LOAD ---")
    load_data_to_db(transformed_data)

    print("\n--- Match History ETL Pipeline Finished. ---")

if __name__ == "__main__":
    # Now, when we run this script, it will execute BOTH pipelines in order.
    run_player_leaderboard_update()
    run_etl_pipeline()

