"""
2026-2027 LD ELO rankings.

Pulls results from the Tabroom download_data API. After a tournament has
published Varsity LD results, append it to TOURNAMENTS below in calendar
order:

    {"name": "Grapevine", "tourn_id": 39477, "bid": 4},  # Quarterfinals

Bid levels: Finals (1), Semifinals (2), Quarterfinals (4), Octofinals (8).
Optional event_id can pin the LD event if auto-detect is wrong.
Competitors are identified by Tabroom entry_code (e.g. "Lynbrook JR"), not name.

Usage (from this directory):
    python LDRankings.py
    python LDRankings.py --refresh
    python LDRankings.py --refresh-id 40342
"""

import argparse
import math
import os

import tabroom

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(SCRIPT_DIR, "cache")

# Append tournaments here after confirming Tabroom has published LD results.
TOURNAMENTS = [
    {"name": "Loyola", "tourn_id": 40342, "bid": 4},  # Quarterfinals
]

K = 30
elos_dict = {}


def add_prelims(parsed, elos_dict, bid):
    """Add prelim debates to the rankings."""
    teams_dict = parsed["entries"]
    for debate in parsed["prelims"]:
        team1, team2 = debate["aff_code"], debate["neg_code"]
        if not debate["winner_is_aff"]:
            team1, team2 = team2, team1
        try:
            team1, team2 = teams_dict[team1], teams_dict[team2]
        except KeyError:
            continue
        code1, code2 = team1[1], team2[1]
        try:
            elo_team1 = elos_dict[code1][0]
        except KeyError:
            elo_team1 = 1500
        try:
            elo_team2 = elos_dict[code2][0]
        except KeyError:
            elo_team2 = 1500
        elo_diff = elo_team1 - elo_team2
        win_prob = 1.0 / (math.pow(10.0, (-elo_diff / 400.0)) + 1.0)
        shift = K * (1 - win_prob) * ((bid / 8) ** 0.5)
        elo_team1 += shift
        elo_team2 -= shift
        elos_dict[code1] = [elo_team1, team1[0]]
        elos_dict[code2] = [elo_team2, team2[0]]
    return elos_dict


def add_elims(parsed, elos_dict, bid):
    """Add elim debates to the rankings."""
    teams_dict = parsed["entries"]
    for debates in parsed["elims"]:
        for debate in debates:
            team1, team2 = debate["aff_code"], debate["neg_code"]
            if not debate["winner_is_aff"]:
                team1, team2 = team2, team1
            try:
                team1, team2 = teams_dict[team1], teams_dict[team2]
            except KeyError:
                continue
            code1, code2 = team1[1], team2[1]
            try:
                elo_team1 = elos_dict[code1][0]
            except KeyError:
                elo_team1 = 1500
            try:
                elo_team2 = elos_dict[code2][0]
            except KeyError:
                elo_team2 = 1500
            elo_diff = elo_team1 - elo_team2
            win_prob = 1.0 / (math.pow(10.0, (-elo_diff / 400.0)) + 1.0)
            shift = K * (1 - win_prob) * ((bid / 8) ** 0.5)
            try:
                shift *= 1 + (int(debate["bw"]) - 1) / (int(debate["bl"]) + 1)
            except (KeyError, TypeError, ValueError, ZeroDivisionError):
                continue
            elo_team1 += shift + bid
            elo_team2 -= shift / 2
            elos_dict[code1] = [elo_team1, team1[0]]
            elos_dict[code2] = [elo_team2, team2[0]]
    return elos_dict


def add_tournament(tournament, refresh=False):
    """Fetch a listed tournament and add it to the rankings."""
    name = tournament["name"]
    tourn_id = tournament["tourn_id"]
    bid = tournament["bid"]
    print(f"Adding {name} (tourn_id={tourn_id}, bid={bid})")
    data = tabroom.fetch_tournament(tourn_id, CACHE_DIR, refresh=refresh)
    parsed = tabroom.parse_ld_tournament(data, event_id=tournament.get("event_id"))
    print(
        f"  {parsed['event_name']}: "
        f"{len(parsed['prelims'])} prelim debates, "
        f"{sum(len(round_debates) for round_debates in parsed['elims'])} elim debates"
    )
    add_prelims(parsed, elos_dict, bid)
    add_elims(parsed, elos_dict, bid)


def write_to_csv(elos_list):
    """Write the rankings to CSV."""
    rows = "Rank,School,Name,Elo\n"
    top_500 = "Rank,School,Name,Elo\n"
    counter = 0
    for code, elo_name in elos_list:
        elo, name = elo_name[0], elo_name[1]
        counter += 1
        name = " ".join(name.split())
        if name in ["Ece Eskici"]:
            continue
        record = (
            str(counter)
            + ","
            + code
            + ","
            + name
            + ","
            + str(round(elo * 1000) / 1000)
            + "\n"
        )
        rows += record
        if counter < 501:
            top_500 += record

    with open(os.path.join(SCRIPT_DIR, "LDRankings.csv"), "w") as handle:
        handle.write(rows[:-1])

    with open(os.path.join(SCRIPT_DIR, "LDRankings_top500.csv"), "w") as handle:
        handle.write(top_500[:-1])


def parse_args():
    parser = argparse.ArgumentParser(description="Compute 2026-2027 LD ELO rankings")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Re-download JSON for every listed tournament",
    )
    parser.add_argument(
        "--refresh-id",
        type=int,
        action="append",
        default=[],
        dest="refresh_ids",
        help="Re-download JSON for a specific tourn_id (repeatable)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    refresh_ids = set(args.refresh_ids or [])
    for tournament in TOURNAMENTS:
        refresh = args.refresh or tournament["tourn_id"] in refresh_ids
        add_tournament(tournament, refresh=refresh)

    elos = sorted(elos_dict.items(), key=lambda item: item[1], reverse=True)
    write_to_csv(elos)
    print(f"Wrote rankings for {len(elos_dict)} competitors")
