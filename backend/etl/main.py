import sys

from .riot_api import get_top_apex_player_data, get_match_ids_by_puuid, get_match_data_by_id
from .data_transformer import transform_raw_match_data
from .db_loader import (
    load_data_to_db,
    load_player_data_to_db,
    load_matches_to_db,
    get_puuids_to_crawl,
    mark_puuids_crawled,
    get_existing_match_ids,
    refresh_champion_stats_by_tier,
    refresh_champion_stats_by_patch,
    record_lp_history,
    prune_old_matches,
)

# How much of the player pool to crawl match history for in a single run, and
# how many recent matches to pull per player. Tuned to comfortably fit within
# Riot's default rate limit (20 req/1s, 100 req/2min) inside a single GitHub
# Actions job, even before match-id dedup kicks in. Since the pool is
# ~1,500-3,000 apex players, a rotating slice of 500/day gives full coverage
# every few days while new matches accumulate daily.
PLAYERS_TO_CRAWL_PER_RUN = 500
MATCHES_PER_PLAYER = 20

# How long to keep match data before it's pruned, to keep the database from
# growing forever. Lower to 90 if 180 turns out to be too much for the free
# Supabase storage tier.
MATCH_RETENTION_DAYS = 180


def run_player_leaderboard_update():
    """Fetches and stores the current Challenger + Grandmaster + Master leaderboard."""
    print("\n--- Starting Player Leaderboard Update Pipeline ---")
    player_data = get_top_apex_player_data()
    load_player_data_to_db(player_data)
    record_lp_history(player_data)
    print("\n--- Player Leaderboard Update Finished. ---")


def run_etl_pipeline():
    """
    Runs the incremental match history ETL: crawls a rotating slice of the
    player pool, fetches only match IDs we don't already have, loads them,
    and rebuilds the champion_stats_by_tier insight table.

    Returns True on success, False if the load step failed. On failure, the
    rotation state is deliberately NOT advanced (mark_puuids_crawled is
    skipped) and the insight table is NOT rebuilt from an incomplete load,
    since neither would be safe to do on top of data that didn't actually
    get persisted.
    """
    print("\n--- Starting Match History ETL Pipeline ---")

    # --- 1. EXTRACT ---
    print("--- Phase: EXTRACT ---")

    player_puuids = get_puuids_to_crawl(limit=PLAYERS_TO_CRAWL_PER_RUN)
    if not player_puuids:
        print("ETL Aborted: No PUUIDs available to crawl (has the leaderboard update run yet?).")
        return True

    all_match_ids = set()
    print(f"Fetching match histories for {len(player_puuids)} players...")
    for puuid in player_puuids:
        match_ids = get_match_ids_by_puuid(puuid, count=MATCHES_PER_PLAYER)
        if match_ids:
            all_match_ids.update(match_ids)

    already_stored = get_existing_match_ids(all_match_ids)
    new_match_ids = list(all_match_ids - already_stored)
    print(
        f"Found {len(all_match_ids)} unique matches across crawled players "
        f"({len(already_stored)} already stored, {len(new_match_ids)} new)."
    )

    raw_match_data = []
    for i, match_id in enumerate(new_match_ids):
        if (i + 1) % 25 == 0:
            print(f"  ...progress: {i + 1}/{len(new_match_ids)}")
        match_data = get_match_data_by_id(match_id)
        if match_data:
            raw_match_data.append(match_data)

    print(f"Extraction complete. Fetched detail for {len(raw_match_data)} new matches.")

    # --- 2. TRANSFORM ---
    print("\n--- Phase: TRANSFORM ---")
    matches, participant_stats = transform_raw_match_data(raw_match_data)

    # --- 3. LOAD ---
    print("\n--- Phase: LOAD ---")
    if not load_matches_to_db(matches) or not load_data_to_db(participant_stats):
        print(
            "\n--- Match History ETL Pipeline FAILED during LOAD. "
            "Skipping crawl-state update and insight refresh so a partial "
            "load isn't treated as a completed crawl. ---"
        )
        return False

    mark_puuids_crawled(player_puuids)
    prune_old_matches(retention_days=MATCH_RETENTION_DAYS)
    refresh_champion_stats_by_tier()
    refresh_champion_stats_by_patch()

    print("\n--- Match History ETL Pipeline Finished. ---")
    return True


if __name__ == "__main__":
    run_player_leaderboard_update()
    if not run_etl_pipeline():
        sys.exit(1)
