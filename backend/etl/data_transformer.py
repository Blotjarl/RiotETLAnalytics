from datetime import datetime, timezone


def transform_raw_match_data(raw_match_data_list):
    """
    Transforms a list of raw match-v5 responses from the Riot API into
    (matches, participant_stats) ready for loading:
      - matches: one row per match (match-level metadata)
      - participant_stats: one row per player per match

    Uses the real Riot match id (metadata.matchId, e.g. "NA1_1234567890")
    rather than the legacy numeric gameId, since gameId isn't globally
    unique across platforms. Uses riotIdGameName/riotIdTagline since
    summonerName is deprecated by Riot on match participants.
    """
    matches_list = []
    participant_stats_list = []

    print(f"Transforming data for {len(raw_match_data_list)} matches...")

    for match_data in raw_match_data_list:
        metadata = match_data.get("metadata", {})
        match_info = match_data.get("info", {})
        match_id = metadata.get("matchId")
        if not match_id or not match_info:
            continue  # Skip malformed match data

        game_creation_ms = match_info.get("gameCreation")
        matches_list.append({
            "matchId": match_id,
            "platformId": match_info.get("platformId"),
            "queueId": match_info.get("queueId"),
            "gameCreation": (
                datetime.fromtimestamp(game_creation_ms / 1000, tz=timezone.utc)
                if game_creation_ms else None
            ),
            "gameDuration": match_info.get("gameDuration"),
            "gameVersion": match_info.get("gameVersion"),
            "gameMode": match_info.get("gameMode"),
        })

        for p_data in match_info.get("participants", []):
            participant_stats_list.append({
                "matchId": match_id,
                "puuid": p_data.get("puuid"),
                "riotIdGameName": p_data.get("riotIdGameName") or p_data.get("summonerName"),
                "riotIdTagline": p_data.get("riotIdTagline"),
                "championName": p_data.get("championName"),
                "win": p_data.get("win"),
                "kills": p_data.get("kills"),
                "deaths": p_data.get("deaths"),
                "assists": p_data.get("assists"),
                # teamPosition can come back as "" (not just missing) on some
                # remakes/edge cases even in ranked solo/duo; normalize to NULL.
                "teamPosition": p_data.get("teamPosition") or None,
                "teamId": p_data.get("teamId"),
                "item0": p_data.get("item0"),
                "item1": p_data.get("item1"),
                "item2": p_data.get("item2"),
                "item3": p_data.get("item3"),
                "item4": p_data.get("item4"),
                "item5": p_data.get("item5"),
                "item6": p_data.get("item6"),
                "summoner1Id": p_data.get("summoner1Id"),
                "summoner2Id": p_data.get("summoner2Id"),
                "goldEarned": p_data.get("goldEarned"),
                "totalMinionsKilled": p_data.get("totalMinionsKilled"),
                "visionScore": p_data.get("visionScore"),
                "totalDamageDealtToChampions": p_data.get("totalDamageDealtToChampions"),
                "perks": p_data.get("perks"),
                "firstBloodKill": p_data.get("firstBloodKill", False),
            })

    print("Transformation complete.")
    return matches_list, participant_stats_list
