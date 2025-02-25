import requests
import json
import sys
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Constants
DEBUG_MODE = False  # Set to True to enable debug logs

# Endpoint URLs
CONTESTS_ENDPOINT = "https://www.draftkings.com/lobby/getcontests?sport=NBA"
DRAFTABLES_ENDPOINT = "https://api.draftkings.com/draftgroups/v1/draftgroups/{draftgroup_id}/draftables"

# Session setup with retry mechanism
def get_session():
    """Create a session with retry mechanism for handling transient errors."""
    session = requests.Session()
    retries = Retry(
        total=3,  # Total number of retries
        backoff_factor=0.3,  # Wait time between retries
        status_forcelist=[500, 502, 503, 504],  # Retry on these HTTP statuses
        allowed_methods=["GET"]  # Retry only on GET requests
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    return session

# Initialize session
session = get_session()

# Debugging function
def debug_log(message):
    if DEBUG_MODE:
        print(f"DEBUG: {message}")

# Fetch NBA draft groups
def fetch_draftgroups():
    """Fetch all NBA draft groups."""
    try:
        response = session.get(CONTESTS_ENDPOINT, timeout=10)
        response.raise_for_status()
        data = response.json()
        draftgroups = []
        for group in data.get('DraftGroups', []):
            draftgroup_id = group.get("DraftGroupId")
            event_id = group.get("EventId")
            if draftgroup_id and event_id:
                draftgroups.append({
                    'DraftGroupId': draftgroup_id,
                    'EventId': event_id,
                    'ContestTypeId': group.get('ContestTypeId'),
                    'GameCount': group.get('GameCount', ''),
                    'ContestStartTimeSuffix': group.get('ContestStartTimeSuffix', '')
                })
                debug_log(f"Added DraftGroupId {draftgroup_id} with EventId {event_id}.")
        debug_log(f"Total draft groups fetched: {len(draftgroups)}")
        return draftgroups
    except requests.RequestException as e:
        print(f"Error fetching draft groups: {e}")
        sys.exit(1)

# Fetch draftable players for a specific draft group
def fetch_draftables(draftgroup_id):
    """Fetch draftable players for a specific draft group, ensuring they have a valid salary."""
    url = DRAFTABLES_ENDPOINT.format(draftgroup_id=draftgroup_id)
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        players = [
            {
                'displayName': player.get('displayName', 'Unknown'),
                'salary': player.get('salary', 0),
                'teamAbbreviation': player.get('teamAbbreviation', 'Unknown')
            }
            for player in data.get('draftables', [])
            if player.get('salary') is not None
        ]
        debug_log(f"Fetched {len(players)} players with salaries for DraftGroupId {draftgroup_id}.")
        return players
    except requests.RequestException as e:
        print(f"Error fetching draftables for DraftGroupId {draftgroup_id}: {e}")
        return []

# Main function
def main():
    # Step 1: Fetch NBA draft groups
    draftgroups = fetch_draftgroups()
    if not draftgroups:
        print("No NBA draft groups found.")
        sys.exit(0)

    all_players = []

    # Step 2: Iterate through each draft group to fetch players
    for group in draftgroups:
        draftgroup_id = group['DraftGroupId']
        event_id = group['EventId']
        debug_log(f"Processing DraftGroupId: {draftgroup_id}")

        # Fetch players from DraftKings
        players = fetch_draftables(draftgroup_id)
        if not players:
            debug_log(f"No players found for DraftGroupId {draftgroup_id}. Skipping.")
            continue

        # Append players to the overall list
        all_players.extend(players)

    if not all_players:
        print("No players with valid salaries found.")
        sys.exit(0)

    # Optional: Remove duplicate players based on displayName
    unique_players = {player['displayName']: player for player in all_players}.values()

    # Step 3: Print the results as JSON
    print(json.dumps(list(unique_players), indent=4))

if __name__ == "__main__":
    main()
