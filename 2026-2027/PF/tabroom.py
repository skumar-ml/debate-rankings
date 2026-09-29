"""Fetch and parse Tabroom tournament JSON for PF rankings."""

import json
import os
import re
import time
import urllib.error
import urllib.request

DOWNLOAD_URL = "https://www.tabroom.com/api/download_data.mhtml?tourn_id={tourn_id}"
MAX_FETCH_ATTEMPTS = 5
BAD_GATEWAY_RETRY_SECONDS = 2

EXCLUDED_EVENT = re.compile(
    r"\b(jv|novice|ms|middle|junior\s+varsity|round\s+robin|rr|silver)\b",
    re.IGNORECASE,
)
PREFERRED_EVENT = ("gold", "varsity", "open", "championship", "toc")
PRELIM_TYPES = {"prelim", "highlow"}
ELIM_TYPES = {"elim", "final"}


def cache_path(cache_dir, tourn_id):
    return os.path.join(cache_dir, f"{tourn_id}.json")


def fetch_tournament(tourn_id, cache_dir, refresh=False):
    """Load tournament JSON from cache or Tabroom."""
    path = cache_path(cache_dir, tourn_id)
    if not refresh and os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    url = DOWNLOAD_URL.format(tourn_id=tourn_id)
    request = urllib.request.Request(
        url, headers={"User-Agent": "PFRankings/2026-2027"}
    )
    raw = None
    for attempt in range(1, MAX_FETCH_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request) as response:
                raw = response.read()
            break
        except urllib.error.HTTPError as exc:
            if exc.code == 502 and attempt < MAX_FETCH_ATTEMPTS:
                print(
                    f"  Tabroom 502 for tourn_id={tourn_id}, "
                    f"retry {attempt}/{MAX_FETCH_ATTEMPTS}"
                )
                time.sleep(BAD_GATEWAY_RETRY_SECONDS)
                continue
            raise Exception(f"Failed to fetch tournament {tourn_id}: {exc}") from exc
        except urllib.error.URLError as exc:
            raise Exception(f"Failed to fetch tournament {tourn_id}: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise Exception(
            f"Tabroom did not return JSON for tournament {tourn_id}."
        ) from exc

    os.makedirs(cache_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle)

    return data


def _event_name(event):
    return str(event.get("name") or "").strip()


def _is_pf_event(name):
    lowered = name.lower()
    if "pf" not in lowered and "public forum" not in lowered:
        return False
    if EXCLUDED_EVENT.search(lowered):
        return False
    return True


def _event_preference(name):
    lowered = name.lower()
    for index, token in enumerate(PREFERRED_EVENT):
        if token in lowered:
            return index
    return len(PREFERRED_EVENT)


def _all_events(data):
    events = list(data.get("events") or [])
    for category in data.get("categories") or []:
        events.extend(category.get("events") or [])
    return events


def find_pf_event(data, event_id=None):
    events = _all_events(data)
    if event_id is not None:
        for event in events:
            if str(event.get("id")) == str(event_id):
                return event
        raise Exception(f"Event id {event_id} not found.")

    matches = [event for event in events if _is_pf_event(_event_name(event))]
    if not matches:
        raise Exception("No Varsity PF event found.")
    matches.sort(key=lambda event: _event_preference(_event_name(event)))
    return matches[0]


def normalize_pf_name(name):
    """Alphabetize partner last names: 'Chavez & Bhattacharya' -> 'Bhattacharya & Chavez'."""
    cleaned = str(name or "").replace("&nbsp;", "")
    parts = [part.strip() for part in cleaned.split("&")]
    parts = [part for part in parts if part]
    if len(parts) >= 2:
        parts = sorted(parts, key=str.lower)
        return " & ".join(parts)
    return " ".join(cleaned.split())


def _winloss(ballot):
    if not ballot:
        return None
    for score in ballot.get("scores") or []:
        if score.get("tag") == "winloss":
            return score.get("value")
    return None


def _group_ballots_by_side(section):
    by_side = {}
    for ballot in section.get("ballots") or []:
        side = ballot.get("side")
        if side is None:
            continue
        try:
            side = int(side)
        except (TypeError, ValueError):
            continue
        by_side.setdefault(side, []).append(ballot)
    return by_side


def _is_bye_section(section, by_side):
    if section.get("bye"):
        return True
    if set(by_side.keys()) != {1, 2}:
        return True
    for ballots in by_side.values():
        if any(ballot.get("bye") for ballot in ballots):
            return True
        codes = {(ballot.get("entry_code") or "") for ballot in ballots}
        names = {(ballot.get("entry_name") or "") for ballot in ballots}
        if any("BYE" in value.upper() for value in codes | names):
            return True
    return False


def _side_entry(ballots):
    for ballot in ballots:
        code = ballot.get("entry_code")
        name = normalize_pf_name(ballot.get("entry_name"))
        if code and name:
            return code, name
    return None, None


def _count_votes(by_side):
    aff_votes = 0
    neg_votes = 0
    for ballot in by_side.get(1, []):
        result = _winloss(ballot)
        if result == 1:
            aff_votes += 1
        elif result == 0:
            neg_votes += 1
    if aff_votes + neg_votes == 0:
        for ballot in by_side.get(2, []):
            result = _winloss(ballot)
            if result == 1:
                neg_votes += 1
            elif result == 0:
                aff_votes += 1
    return aff_votes, neg_votes


def _debate_from_section(section, is_elim):
    by_side = _group_ballots_by_side(section)
    if _is_bye_section(section, by_side):
        return None

    aff_code, aff_name = _side_entry(by_side[1])
    neg_code, neg_name = _side_entry(by_side[2])
    if not aff_code or not neg_code:
        return None

    aff_votes, neg_votes = _count_votes(by_side)
    if aff_votes + neg_votes == 0 or aff_votes == neg_votes:
        return None

    debate = {
        "aff_code": aff_code,
        "aff_name": aff_name,
        "neg_code": neg_code,
        "neg_name": neg_name,
        "winner_is_aff": aff_votes > neg_votes,
    }
    if is_elim:
        debate["bw"] = max(aff_votes, neg_votes)
        debate["bl"] = min(aff_votes, neg_votes)
    return debate


def _round_is_prelim(round_obj):
    round_type = str(round_obj.get("type") or "").lower()
    protocol = str(round_obj.get("protocol_name") or "").lower()
    if round_type in PRELIM_TYPES:
        return True
    if round_type in ELIM_TYPES:
        return False
    if "elim" in protocol:
        return False
    if "prelim" in protocol:
        return True
    return not round_obj.get("label")


def _add_entry(entries, code, name):
    name = normalize_pf_name(name)
    if code and name and code not in entries:
        entries[code] = [name, code]


def parse_pf_tournament(data, event_id=None):
    """Return entries, prelim debates, and elim rounds for the Varsity PF event."""
    event = find_pf_event(data, event_id=event_id)
    event_id_str = str(event.get("id"))
    entries = {}

    for school in data.get("schools") or []:
        for entry in school.get("entries") or []:
            if str(entry.get("event")) != event_id_str:
                continue
            _add_entry(entries, entry.get("code"), entry.get("name"))

    prelims = []
    elims = []

    for round_obj in event.get("rounds") or []:
        is_prelim = _round_is_prelim(round_obj)
        debates = []
        for section in round_obj.get("sections") or []:
            debate = _debate_from_section(section, is_elim=not is_prelim)
            if not debate:
                continue
            _add_entry(entries, debate["aff_code"], debate["aff_name"])
            _add_entry(entries, debate["neg_code"], debate["neg_name"])
            debates.append(debate)

        if is_prelim:
            prelims.extend(debates)
        elif debates:
            elims.append(debates)

    if not prelims:
        raise Exception("Error in reading prelims from tournament.")
    if not elims:
        raise Exception("Error in reading elims from tournament.")

    return {
        "entries": entries,
        "prelims": prelims,
        "elims": elims,
        "event_name": _event_name(event),
    }
