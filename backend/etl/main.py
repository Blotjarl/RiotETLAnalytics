# We need to import the functions from our other files
from riot_api import get_challenger_players, get_match_ids_by_puuid, get_match_data_by_id
import time

import json
from data_transformer import transform_raw_match_data
from db_loader import load_data_to_db # Import the new function

def run_etl_pipeline():
    # ... (EXTRACT phase is the same)
    # ...

    print("--- SKIPPING API: Loading raw_matches.json ---")
    try:
        with open('raw_matches.json', 'r') as f:
            raw_match_data = json.load(f)
        print(f"Successfully loaded {len(raw_match_data)} matches from file.")
    except FileNotFoundError:
        # ... (error handling)
        return

    # --- 2. TRANSFORM ---
    print("\n--- Phase: TRANSFORM ---")
    transformed_data = transform_raw_match_data(raw_match_data)
    print(f"Successfully transformed {len(transformed_data)} participant records.")

    # --- 3. LOAD ---
    print("\n--- Phase: LOAD ---")
    load_data_to_db(transformed_data) # Call the loader function!

    print("\nETL Pipeline finished.")

if __name__ == "__main__":
    run_etl_pipeline()