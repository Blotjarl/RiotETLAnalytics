def transform_raw_match_data(raw_match_data_list):
    """
    Transforms a list of raw match data from the Riot API into a structured format
    containing match details and participant stats.
    """
    participant_stats_list = []

    print(f"Transforming data for {len(raw_match_data_list)} matches...")

    for match_data in raw_match_data_list:
        # The actual data is nested inside the 'info' key
        match_info = match_data.get('info', {})
        if not match_info:
            continue # Skip if the match data is malformed

        # Loop through each participant in the match
        for p_data in match_info.get('participants', []):
            # Extract the stats we care about for each player
            player_stats = {
                "matchId": match_info.get('gameId'),
                "puuid": p_data.get('puuid'),
                "summonerName": p_data.get('summonerName'),
                "championName": p_data.get('championName'),
                "win": p_data.get('win'),
                "kills": p_data.get('kills'),
                "deaths": p_data.get('deaths'),
                "assists": p_data.get('assists'),
                "lp": 0,  # Placeholder for LP
                "ladderRank": 0, # Placeholder for ladder rank
            }
            participant_stats_list.append(player_stats)

    print("Transformation complete.")
    return participant_stats_list