import os
import time
import collections
import requests
from dotenv import load_dotenv

load_dotenv()
# .strip() guards against a trailing newline/whitespace in the secret value
# (e.g. from copy-pasting), which `requests` rejects as an invalid header.
RIOT_API_KEY = os.getenv("RIOT_API_KEY", "").strip()
if not RIOT_API_KEY:
    print("Warning: RIOT_API_KEY is not set.")

PLATFORM_REGION = "na1"
ROUTING_REGION = "americas"

# Riot's default app rate limit (applies to both development and personal
# API keys): 20 requests per 1 second, 100 requests per 2 minutes.
RATE_LIMIT_WINDOWS = [(20, 1), (100, 120)]

HEADERS = {"X-Riot-Token": RIOT_API_KEY}


class RateLimiter:
    """Sliding-window limiter that respects Riot's per-second and per-2-minute caps."""

    def __init__(self, windows):
        self._windows = windows
        self._timestamps = {limit: collections.deque() for limit, _ in windows}

    def wait_for_slot(self):
        while True:
            now = time.monotonic()
            longest_wait = 0
            for limit, period in self._windows:
                dq = self._timestamps[limit]
                while dq and now - dq[0] >= period:
                    dq.popleft()
                if len(dq) >= limit:
                    longest_wait = max(longest_wait, period - (now - dq[0]))
            if longest_wait <= 0:
                break
            time.sleep(longest_wait)

    def record_request(self):
        now = time.monotonic()
        for limit, _ in self._windows:
            self._timestamps[limit].append(now)


_rate_limiter = RateLimiter(RATE_LIMIT_WINDOWS)


def _get(url, params=None, max_retries=3):
    """Rate-limited GET with automatic retry on 429 (respecting Retry-After)."""
    for attempt in range(max_retries + 1):
        _rate_limiter.wait_for_slot()
        try:
            response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        except requests.exceptions.RequestException as e:
            print(f"Request error for {url}: {e}")
            return None
        finally:
            _rate_limiter.record_request()

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 1))
            print(f"Rate limited by Riot API, sleeping {retry_after}s (attempt {attempt + 1}/{max_retries + 1})...")
            time.sleep(retry_after)
            continue

        try:
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Request failed for {url}: {e}")
            return None

        return response.json()

    print(f"Giving up on {url} after {max_retries + 1} attempts (still rate limited).")
    return None


def _get_apex_league(tier, endpoint):
    """
    Fetches a full apex league (Challenger/Grandmaster/Master) in one call.
    Returns None (distinct from an empty list) if the request itself failed,
    so callers can tell "fetch failed" apart from "league is empty".
    """
    url = f"https://{PLATFORM_REGION}.api.riotgames.com/lol/league/v4/{endpoint}/by-queue/RANKED_SOLO_5x5"
    print(f"Fetching {tier} player list...")
    league_data = _get(url)
    if league_data is None:
        print(f"Could not fetch {tier} list.")
        return None
    entries = league_data.get("entries", [])
    for entry in entries:
        entry["tier"] = tier
    return entries


def get_top_apex_player_data():
    """
    Fetches the full Challenger + Grandmaster + Master pool (~1,500-3,000
    players on NA), each in a single API call, and ranks them by LP.

    Returns [] if ANY of the three league fetches failed, not just if all
    three did. A partial result would make load_player_data_to_db() (which
    deletes any player not present in the returned list) wrongly delete every
    real player from the tier that failed to fetch.
    """
    print("--- Starting Apex Player Data Fetch ---")

    leagues = {
        "CHALLENGER": _get_apex_league("CHALLENGER", "challengerleagues"),
        "GRANDMASTER": _get_apex_league("GRANDMASTER", "grandmasterleagues"),
        "MASTER": _get_apex_league("MASTER", "masterleagues"),
    }
    if any(entries is None for entries in leagues.values()):
        failed = [tier for tier, entries in leagues.items() if entries is None]
        print(f"Aborting leaderboard update: failed to fetch {', '.join(failed)}.")
        return []

    all_entries = leagues["CHALLENGER"] + leagues["GRANDMASTER"] + leagues["MASTER"]

    all_entries.sort(key=lambda x: x.get("leaguePoints", 0), reverse=True)

    processed_player_data = []
    for i, player_data in enumerate(all_entries):
        if "puuid" not in player_data:
            print(f"  -> Skipping an entry at rank {i + 1}, 'puuid' is missing.")
            continue

        processed_player_data.append({
            "puuid": player_data["puuid"],
            "platform": PLATFORM_REGION,
            "tier": player_data["tier"],
            "leaderboardRank": i + 1,
            "leaguePoints": player_data.get("leaguePoints", 0),
            "rank": player_data.get("rank", "N/A"),
            "wins": player_data.get("wins", 0),
            "losses": player_data.get("losses", 0),
            "veteran": player_data.get("veteran", False),
            "inactive": player_data.get("inactive", False),
            "freshBlood": player_data.get("freshBlood", False),
            "hotStreak": player_data.get("hotStreak", False),
        })

    print(f"--- Successfully processed {len(processed_player_data)} apex players. ---")
    return processed_player_data


RANKED_SOLO_DUO_QUEUE_ID = 420


def get_match_ids_by_puuid(puuid, count=20):
    """
    Fetches a list of recent Ranked Solo/Duo match IDs for a given PUUID.
    Filtered to queue 420 so champion_stats_by_tier reflects the apex-tier
    ranked meta, not a blend with whatever ARAM/normals/Arena games these
    players happened to have in their recent history.
    """
    url = f"https://{ROUTING_REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
    params = {"start": 0, "count": count, "queue": RANKED_SOLO_DUO_QUEUE_ID}
    return _get(url, params=params) or []


def get_match_data_by_id(match_id):
    """Fetches the detailed data for a single match."""
    url = f"https://{ROUTING_REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    return _get(url)
