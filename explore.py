from schema import AVAILABLE_METRICS
from data import get_competitions, get_matches, load_match_events


if __name__ == "__main__":
    comps = get_competitions()
    print(f"{len(comps)} competition/season combos available")

    # just grab the first one for now to see what the data looks like
    comp = comps[0]
    competition_id = comp["competition_id"]
    season_id = comp["season_id"]
    print(f"using: {comp['competition_name']} {comp['season_name']}")

    matches = get_matches(competition_id, season_id)
    print(f"\n{len(matches)} matches in this competition/season")

    match = matches[0]
    match_id = match["match_id"]
    print(f"loading events for match {match_id}: "
          f"{match['home_team']['home_team_name']} vs {match['away_team']['away_team_name']}")

    df = load_match_events(match_id)

    print(f"\n{len(df)} events loaded")

    # this is what we'd actually show the user on the frontend -
    # not the 117 raw columns, just what they can ask about
    print("\nyou can ask about:")
    for metric in AVAILABLE_METRICS:
        print(f"  - {metric}")