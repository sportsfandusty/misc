import requests
import pandas as pd
import os
import sys
import json  # Import json module for handling JSON data
from requests.adapters import HTTPAdapter

# Constants
DEBUG_MODE = os.getenv("DEBUG_MODE", "False") == "True"
SAVE_TO_CSV = False          # Set to True to save draftables data to CSV files
SAVE_RAW_JSON = True         # Set to True to save raw JSON responses to files
SAVE_RAW_DRAFTGROUPS = True # Set to True to save raw draft groups response per sport

# Desired Game Types
DESIRED_GAME_TYPES = ["Classic", "Showdown"]  # Add other desired game types here

# Directory configurations
RAW_JSON_DIR = "raw_json_responses"                 # Directory to save raw JSON files for draft groups
RAW_DRAFTGROUP_JSON_DIR = "raw_draftgroup_json_responses"  # Directory to save raw JSON files for individual draft groups
CSV_OUTPUT_DIR = "csv_outputs"                       # Directory to save CSV files

# Endpoint URLs
SPORTS_ENDPOINT = "https://api.draftkings.com/sites/US-DK/sports/v1/sports?format=json"
CONTESTS_ENDPOINT = "https://www.draftkings.com/lobby/getcontests?sport={sport}"
DRAFTABLES_ENDPOINT = "https://api.draftkings.com/draftgroups/v1/draftgroups/{draftgroup_id}/draftables"

# Session setup with retry mechanism
def get_session():
    """Create a session with retry mechanism for handling transient errors."""
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=3)
    session.mount("https://", adapter)
    return session

# Use session to make requests
session = get_session()

# Debugging
def debug_log(message):
    if DEBUG_MODE:
        print(f"[DEBUG] {message}")

def fetch_sports():
    """Fetch all sports with their regionAbbreviatedSportName."""
    try:
        response = session.get(SPORTS_ENDPOINT, timeout=10)
        response.raise_for_status()
        sports_data = response.json()
        return [sport['regionAbbreviatedSportName'] for sport in sports_data.get('sports', [])]
    except requests.RequestException as e:
        print(f"Error fetching sports: {e}")
        return []

def fetch_draftables(draftgroup_id):
    """Fetch draftable players for a specific draft group, only returning players with a non-null salary."""
    url = DRAFTABLES_ENDPOINT.format(draftgroup_id=draftgroup_id)
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        # Only return players with a non-null salary, using a dictionary to remove duplicates
        players = {
            player['displayName']: {
                'displayName': player['displayName'],
                'salary': player['salary'],
                'teamAbbreviation': player['teamAbbreviation']
            }
            for player in data.get('draftables', [])
            if player.get('salary') is not None  # Ensure salary is not null
        }
        debug_log(f"Fetched {len(players)} unique players with salary for DraftGroupId {draftgroup_id}.")
        return list(players.values())  # Convert back to list to return unique players
    except requests.RequestException as e:
        print(f"Error fetching draftables for DraftGroupId {draftgroup_id}: {e}")
        return []

def fetch_draftgroups(sport):
    """Fetch draft groups for a specific sport, filtering for featured groups with desired GameTypes and salaried players."""
    url = CONTESTS_ENDPOINT.format(sport=sport)
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Save the raw draft groups response per sport
        if SAVE_RAW_DRAFTGROUPS:
            save_raw_draftgroups(sport, data)
        
        # Filter to include only draft groups that:
        # - Are tagged as "Featured"
        # - Have a desired GameType
        # - Contain at least one player with a non-null salary
        draftgroups = []
        excluded_game_types = 0
        for group in data.get('Contests', []):  # Changed from 'DraftGroups' to 'Contests'
            if group.get("DraftGroupTag") == "Featured":
                game_type = group.get('gameType', 'Unknown')
                if game_type not in DESIRED_GAME_TYPES:
                    excluded_game_types += 1
                    debug_log(f"DraftGroupId {group['dg']} excluded due to GameType: {game_type}")
                    continue  # Skip this draft group as its GameType is not desired
                
                draftgroup_id = group['dg']  # Assuming 'dg' is DraftGroupId
                contest_type_id = group['pt']  # Assuming 'pt' is ContestTypeId
                game_count = group.get('cs', '')  # Assuming 'cs' is GameCount
                start_time_suffix = group.get('sdstring', '')
                
                # Fetch draftables for this draftgroup_id and check for salary
                players = fetch_draftables(draftgroup_id)
                if players:  # Only add if there's at least one player with a salary
                    draftgroups.append({
                        'DraftGroupId': draftgroup_id,
                        'ContestTypeId': contest_type_id,
                        'GameCount': game_count,
                        'ContestStartTimeSuffix': start_time_suffix,
                        'GameType': game_type,
                        'Players': players
                    })
                    debug_log(f"DraftGroupId {draftgroup_id} added (GameType: {game_type}, contains salaried players).")
                else:
                    debug_log(f"DraftGroupId {draftgroup_id} skipped (no salaried players).")
        
        if excluded_game_types > 0:
            print(f"Excluded {excluded_game_types} draft group(s) due to undesired GameTypes.")
        
        debug_log(f"Found {len(draftgroups)} featured draft groups with desired GameTypes and salaried players for {sport}.")
        return draftgroups
    except requests.RequestException as e:
        print(f"Error fetching draft groups for {sport}: {e}")
        return []

def fetch_draftgroup_raw(draftgroup_id):
    """Fetch the raw JSON response for a specific draft group."""
    url = DRAFTABLES_ENDPOINT.format(draftgroup_id=draftgroup_id)
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching raw data for DraftGroupId {draftgroup_id}: {e}")
        return None

def save_raw_json(draftgroup_id, raw_data, draftgroup_type):
    """Save the raw JSON data for a draft group to a file."""
    if not os.path.exists(RAW_DRAFTGROUP_JSON_DIR):
        os.makedirs(RAW_DRAFTGROUP_JSON_DIR)
        debug_log(f"Created directory for individual draft group JSON responses: {RAW_DRAFTGROUP_JSON_DIR}")
    
    filename = f"DraftGroup_{draftgroup_id}_{draftgroup_type}.json"
    file_path = os.path.join(RAW_DRAFTGROUP_JSON_DIR, filename)
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(raw_data, f, indent=4)
        debug_log(f"Raw JSON for DraftGroupId {draftgroup_id} saved to {file_path}.")
        print(f"Raw JSON response saved to: {file_path}")
    except IOError as e:
        print(f"Error saving raw JSON for DraftGroupId {draftgroup_id}: {e}")

def save_raw_draftgroups(sport, raw_data):
    """Save the raw draft groups response for a sport to a file."""
    if not os.path.exists(RAW_JSON_DIR):
        os.makedirs(RAW_JSON_DIR)
        debug_log(f"Created directory for draft groups JSON responses: {RAW_JSON_DIR}")
    
    filename = f"DraftGroups_{sport}.json"
    file_path = os.path.join(RAW_JSON_DIR, filename)
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(raw_data, f, indent=4)
        debug_log(f"Raw draft groups JSON for {sport} saved to {file_path}.")
        print(f"Raw draft groups JSON response saved to: {file_path}")
    except IOError as e:
        print(f"Error saving raw draft groups JSON for {sport}: {e}")

def determine_draftgroup_type(draftgroup_info, raw_data):
    """
    Determine the draft group type based on the 'GameType' field.
    """
    game_type = draftgroup_info.get('GameType', 'Unknown')
    debug_log(f"DraftGroupId {draftgroup_info.get('DraftGroupId')} has GameType: {game_type}")
    
    # Use 'GameType' directly as 'draftgroup_type'
    draftgroup_type = game_type if game_type else "Unknown"
    
    return draftgroup_type

def save_or_print_data(sport, draftgroup_info, draftgroup_type):
    """Save each draft group's data to a CSV file or print it based on SAVE_TO_CSV setting."""
    draftgroup_id = draftgroup_info['DraftGroupId']
    contest_type_id = draftgroup_info['ContestTypeId']
    game_count = draftgroup_info['GameCount']
    start_time_suffix = draftgroup_info['ContestStartTimeSuffix']
    players = draftgroup_info['Players']
    
    # Determine filename based on Draft Group Type
    file_name = f"{draftgroup_type} - {sport} - {draftgroup_id}.csv"
    
    if SAVE_TO_CSV:
        # Create output directory if it does not exist
        if not os.path.exists(CSV_OUTPUT_DIR):
            os.makedirs(CSV_OUTPUT_DIR)
            debug_log(f"Created directory for CSV outputs: {CSV_OUTPUT_DIR}")
        
        # Convert to DataFrame and save as CSV in the output directory
        df = pd.DataFrame(players)
        file_path = os.path.join(CSV_OUTPUT_DIR, file_name)
        try:
            df.to_csv(file_path, index=False)
            debug_log(f"Data for DraftGroupId {draftgroup_id} saved to {file_path}.")
            print(f"DraftGroupId {draftgroup_id} data saved to: {file_path}")
        except IOError as e:
            print(f"Error saving CSV for DraftGroupId {draftgroup_id}: {e}")
    else:
        # Print data to terminal instead of saving
        print(f"\nData for {sport} - DraftGroupId {draftgroup_id} - {draftgroup_type}")
        df = pd.DataFrame(players)
        print(df.to_string(index=False))

def main():
    # Step 1: Fetch sports
    sports = fetch_sports()
    if not sports:
        print("No sports data available.")
        sys.exit(1)
    
    # Step 2: For each sport, fetch the number of available slates (draft groups)
    sport_slate_counts = {}
    sport_draftgroups_map = {}  # To store draftgroups for each sport
    for sport in sports:
        debug_log(f"Processing sport: {sport}")
        draftgroups = fetch_draftgroups(sport)
        sport_slate_counts[sport] = len(draftgroups)
        sport_draftgroups_map[sport] = draftgroups  # Store draftgroups for later use
    
    # Step 3: Display the list of sports with their respective slate counts
    print("\nAvailable Sports and Number of Slates:")
    print("-------------------------------------")
    for idx, (sport, count) in enumerate(sport_slate_counts.items(), start=1):
        print(f"{idx}. {sport} - {count} slate(s)")
    
    # Step 4: Prompt the user to select a sport
    while True:
        try:
            selection = int(input("\nEnter the number corresponding to the sport you want to select (or 0 to exit): "))
            if selection == 0:
                print("Exiting the program.")
                sys.exit(0)
            if 1 <= selection <= len(sport_slate_counts):
                selected_sport = list(sport_slate_counts.keys())[selection - 1]
                break
            else:
                print(f"Please enter a number between 1 and {len(sport_slate_counts)}, or 0 to exit.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")
    
    # Step 5: Fetch draft groups for the selected sport
    print(f"\nFetching draft groups for {selected_sport}...")
    selected_draftgroups = sport_draftgroups_map[selected_sport]
    num_draftgroups = len(selected_draftgroups)
    
    # Step 6: Display the number of draft groups and their draft IDs with GameType
    print(f"\n{selected_sport} has {num_draftgroups} draft group(s).")
    if num_draftgroups > 0:
        print("Draft Group IDs and Types:")
        for idx, dg in enumerate(selected_draftgroups, start=1):
            print(f"{idx}. {dg['DraftGroupId']} - {dg['GameType']}")
    else:
        print("No draft groups available for this sport.")
        sys.exit(0)
    
    # Step 7: Prompt the user to select a draft group
    while True:
        try:
            draft_selection = int(input("\nEnter the number corresponding to the draft group you want to view (or 0 to exit): "))
            if draft_selection == 0:
                print("Exiting the program.")
                sys.exit(0)
            if 1 <= draft_selection <= num_draftgroups:
                selected_draftgroup = selected_draftgroups[draft_selection - 1]
                selected_draftgroup_id = selected_draftgroup['DraftGroupId']
                break
            else:
                print(f"Please enter a number between 1 and {num_draftgroups}, or 0 to exit.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")
    
    # Step 8: Fetch and save the raw JSON response for the selected draft group
    print(f"\nFetching raw data for DraftGroupId {selected_draftgroup_id}...")
    raw_data = fetch_draftgroup_raw(selected_draftgroup_id)
    if raw_data:
        # Determine draft group type based on 'GameType'
        draftgroup_type = determine_draftgroup_type(selected_draftgroup, raw_data)
        
        if SAVE_RAW_JSON:
            save_raw_json(selected_draftgroup_id, raw_data, draftgroup_type)
        else:
            print("\nRaw JSON Response:")
            print(json.dumps(raw_data, indent=4))  # Pretty-print the JSON
        
        # Optionally, save or print draftables data
        save_or_print_data(selected_sport, selected_draftgroup, draftgroup_type)
        
        # Display the draft group type
        print(f"\nDraft Group Type: {draftgroup_type}")
    else:
        print("Failed to retrieve raw data for the selected draft group.")

if __name__ == "__main__":
    main()
