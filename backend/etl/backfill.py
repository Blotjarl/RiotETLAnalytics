import os
import sys

from .riot_api import get_match_data_by_id
from .data_transformer import transform_raw_match_data
from .db_loader import get_match_ids_missing_rich_fields, load_matches_to_db, load_data_to_db

# One workflow_dispatch run processes at most this many matches, bounded by
# Riot's rate limit and the job's timeout. Re-trigger the workflow to process
# the next slice -- get_match_ids_missing_rich_fields is naturally resumable.
BACKFILL_BATCH_LIMIT = int(os.getenv("BACKFILL_BATCH_LIMIT", "8000"))


def run_backfill():
    """
    One-off backfill for matches/participant_stats rows stored before Phase 1
    added rich per-participant fields (role, items, gold, vision, etc.).
    Re-fetches full match-v5 JSON for matches missing those fields and
    re-loads them -- load_data_to_db's ON CONFLICT DO UPDATE fills in the new
    columns on the already-stored rows.
    """
    print("\n--- Starting Rich-Field Backfill ---")
    match_ids = get_match_ids_missing_rich_fields(limit=BACKFILL_BATCH_LIMIT)
    if not match_ids:
        print("No matches need backfilling.")
        return True

    raw_match_data = []
    for i, match_id in enumerate(match_ids):
        if (i + 1) % 25 == 0:
            print(f"  ...progress: {i + 1}/{len(match_ids)}")
        match_data = get_match_data_by_id(match_id)
        if match_data:
            raw_match_data.append(match_data)

    matches, participant_stats = transform_raw_match_data(raw_match_data)

    if not load_matches_to_db(matches) or not load_data_to_db(participant_stats):
        print("\n--- Backfill FAILED during LOAD. ---")
        return False

    print(f"\n--- Backfill Finished: {len(participant_stats)} participant rows across {len(matches)} matches. ---")
    return True


if __name__ == "__main__":
    if not run_backfill():
        sys.exit(1)
