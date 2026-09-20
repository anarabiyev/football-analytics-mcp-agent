import requests
import pandas as pd

BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
TIMEOUT_SECONDS = 10

# simple in-memory cache so we don't refetch the same match's events
# every time a question comes in about it
_events_cache = {}


def get_competitions():
    return _fetch_json(f"{BASE}/competitions.json")


def get_matches(competition_id, season_id):
    url = f"{BASE}/matches/{competition_id}/{season_id}.json"
    return _fetch_json(url)


def load_match_events(match_id):
    if match_id not in _events_cache:
        url = f"{BASE}/events/{match_id}.json"
        events = _fetch_json(url)
        _events_cache[match_id] = pd.json_normalize(events, sep=".")
    return _events_cache[match_id]


def _fetch_json(url):
    try:
        response = requests.get(url, timeout=TIMEOUT_SECONDS)
    except requests.exceptions.RequestException as e:
        raise ValueError(f"couldn't reach StatsBomb's data ({e})") from e

    if response.status_code == 404:
        raise ValueError(f"no data found for that id - double check it's correct ({url})")
    response.raise_for_status()

    return response.json()