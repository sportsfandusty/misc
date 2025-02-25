# ===========================
# Section: Config
# Description: Contains configuration settings for the live odds microservice.
# ===========================
import logging

DEBUG_MODE = True  # Set to False for general info mode.
LOG_LEVEL = logging.DEBUG if DEBUG_MODE else logging.INFO
logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s", level=LOG_LEVEL)

MATCHES_TO_SCRAPE = 2  # Number of days to scrape (today and tomorrow)
URL_TEMPLATE = "http://www.tennisexplorer.com/matches/?type=all&year={year}&month={month}&day={day}"

# Toggle to filter out lower-level tournaments by default.
FILTER_LOW_LEVEL_TOURNAMENTS = True
LOWER_LEVEL_KEYWORDS = ['UTR', 'ITF', 'Challenger', 'Futures']

# Toggle to save snapshot data to a SQLite database.
SAVE_TO_DB = False  # Set to True to persist data, False to disable while testing

# Toggle to prompt for fuzzy match confirmation and update the mapping CSV.
CONFIRM_FUZZY_MATCHES = True  # Set to True to enable interactive confirmation.

# Toggle to print sample data rows for one day (for testing).
PRINT_SAMPLE_DATA = True

# Global lists for logging fuzzy matches and unmapped tournament surfaces.
FUZZY_MATCHES = []
UNMAPPED_SURFACE_MATCHES = []


# ===========================
# Section: Helpers
# Description: Provides helper functions for string normalization and other utilities.
# ===========================
import string

def normalize_name(name):
    """
    Normalize a string by stripping whitespace, lowering case, and removing punctuation.
    
    Args:
        name (str): The input string.
    Returns:
        str: The normalized string.
    """
    return name.strip().lower().translate(str.maketrans('', '', string.punctuation))


# ===========================
# Section: Data Processing Subservice
# Description: Functions to load tournament surfaces, name mappings, and calculate implied win percentages.
# ===========================
import pandas as pd
from datetime import datetime

def load_surface_map(filename="surface_map.csv"):
    """
    Load the surface mapping from a CSV file with columns 'tournament' and 'surface'.
    Tries several encodings if needed.
    
    Returns:
        dict: Mapping from normalized tournament names to their surface.
    """
    logging.info(f"Attempting to load surface map from: {filename}")
    encodings_to_try = ["utf-8", "utf-8-sig", "cp1252", "latin-1"]
    df = None
    last_exception = None
    for enc in encodings_to_try:
        try:
            df = pd.read_csv(filename, encoding=enc)
            logging.debug(f"Successfully loaded surface map file with encoding='{enc}'")
            break
        except Exception as e:
            last_exception = e
            logging.debug(f"Failed with encoding='{enc}': {e}")
    if df is None:
        logging.error(f"All encoding attempts failed for {filename}. Last error: {last_exception}")
        return {}
    logging.debug(f"Surface map columns: {df.columns.tolist()}")
    mapping = {}
    try:
        for _, row in df.iterrows():
            tournament = normalize_name(str(row['tournament']))
            surface = str(row['surface']).strip()
            mapping[tournament] = surface
        return mapping
    except KeyError as ke:
        logging.error(f"Error: Missing expected column in {filename}: {ke}")
        return {}
    except Exception as e:
        logging.error(f"Error processing surface map data from {filename}: {e}")
        return {}

from thefuzz import process

def load_name_map(filename="name_map.csv"):
    """
    Load the name mapping from a CSV file.
    Expected columns are 'name1' (standardized name) and 'name2' (alternate name).
    
    Returns:
        dict: Mapping from normalized alternate names to a dict with:
              - 'standardized': the standardized name,
              - 'raw': the original CSV value,
              - 'row': the row index in the CSV.
    """
    logging.info(f"Attempting to load name map from: {filename}")
    try:
        try:
            df = pd.read_csv(filename)
            logging.debug(f"Successfully loaded name map (comma-delimited): {filename}")
        except Exception as e:
            logging.debug(f"Comma delimiter failed: {e}. Trying tab-delimited...")
            df = pd.read_csv(filename, sep='\t')
            logging.debug(f"Successfully loaded name map (tab-delimited): {filename}")
        logging.debug(f"Name map columns: {df.columns.tolist()}")
        mapping = {}
        for idx, row in df.iterrows():
            standardized = str(row['name1']).strip()
            alternate = str(row['name2']).strip()
            alternate_norm = normalize_name(alternate)
            mapping[alternate_norm] = {"standardized": standardized,
                                       "raw": alternate,
                                       "row": idx}
        logging.info(f"Name map loaded. Total keys: {len(mapping)}")
        return mapping
    except Exception as e:
        logging.error(f"Error loading name map from {filename}: {e}")
        return {}

def calculate_implied_win_percentages(odds1, odds2):
    """
    Calculate implied win percentages from decimal odds.
    
    Returns a tuple: (win_pct_player1, win_pct_player2)
    """
    try:
        prob1 = 1 / odds1
        prob2 = 1 / odds2
        total = prob1 + prob2
        win_pct1 = (prob1 / total)
        win_pct2 = (prob2 / total)
        return round(win_pct1, 3), round(win_pct2, 3)
    except ZeroDivisionError:
        return None, None


# ===========================
# Section: Name Mapping – Fuzzy Confirmation
# Description: Prompt the user for fuzzy match confirmation and update the CSV file.
# ===========================
def update_name_mapping_csv(new_entry, filename="name_map.csv"):
    """
    Append a new row to the name mapping CSV with:
      - name1 = standardized name,
      - name2 = scraped original name.
    """
    try:
        try:
            df = pd.read_csv(filename)
        except Exception:
            df = pd.DataFrame(columns=["name1", "name2"])
        new_row = {"name1": new_entry["mapping_standardized"],
                   "name2": new_entry["scraped_original"]}
        new_row_df = pd.DataFrame([new_row])
        df = pd.concat([df, new_row_df], ignore_index=True)
        df.to_csv(filename, index=False)
        logging.info(f"Updated {filename} with new mapping: {new_entry['scraped_original']} -> {new_entry['mapping_standardized']}")
    except Exception as e:
        logging.error(f"Error updating {filename}: {e}")

def apply_name_mapping(name, name_map, score_cutoff=90):
    """
    Convert an alternate name to its standardized version using the name_map.
    First, try an exact normalized lookup. If not found, do a fuzzy match.
    
    Returns:
        str: Standardized name if a match is found; otherwise, the original name.
    """
    name_lower = normalize_name(name)
    if name_lower in name_map:
        return name_map[name_lower]["standardized"]
    best_match = process.extractOne(name_lower, list(name_map.keys()), score_cutoff=score_cutoff)
    if best_match:
        matched_key, score = best_match
        mapping_info = name_map[matched_key]
        fuzzy_entry = {
            "scraped_normalized": name_lower,
            "scraped_original": name,
            "matched_key": matched_key,
            "mapping_raw": mapping_info["raw"],
            "mapping_standardized": mapping_info["standardized"],
            "csv_row": mapping_info["row"],
            "score": score
        }
        FUZZY_MATCHES.append(fuzzy_entry)
        logging.info(f"Fuzzy match: Scraped '{name}' (normalized: '{name_lower}') matched with mapping CSV row {mapping_info['row']} - CSV value: '{mapping_info['raw']}' (standardized: '{mapping_info['standardized']}') (score: {score})")
        return mapping_info["standardized"]
    return name


# ===========================
# Section: Odds Calculations (continued)
# Description: Creating unique match IDs.
# ===========================
def extract_last_name(full_name):
    """
    Extract the last name from the player's name using everything before the final space.
    
    Returns:
        str: The lowercase result.
    """
    full_name = full_name.strip()
    if " " not in full_name:
        return full_name.lower()
    tokens = full_name.split()
    return " ".join(tokens[:-1]).lower()

def create_match_id(player1, player2, match_date_obj):
    """
    Create a match ID formatted as: {first_last}-{second_last}-{mmddyy}
    """
    last1 = extract_last_name(player1)
    last2 = extract_last_name(player2)
    sorted_names = sorted([last1, last2])
    date_str = match_date_obj.strftime("%m%d%y")
    return f"{sorted_names[0]}-{sorted_names[1]}-{date_str}"


# ===========================
# Section: Scraper
# Description: Scrapes tennis match data from the given URL, applies surface and name mappings.
# ===========================
import requests
from bs4 import BeautifulSoup

def scrape_tennis_matches(url, match_date, processed_matches, match_date_obj, surface_map, name_map):
    """
    Scrape tennis match data from the URL.
    Returns a list of match dictionaries.
    """
    try:
        response = requests.get(url)
    except Exception as e:
        logging.error(f"Request error for URL {url}: {e}")
        return []
    if response.status_code != 200:
        logging.error(f"Error: Failed to retrieve URL {url} (Status code: {response.status_code})")
        return []
    soup = BeautifulSoup(response.text, 'html.parser')
    match_tables = soup.find_all('table', {'class': 'result'})
    matches = []
    current_tournament = None
    for match_table in match_tables:
        rows = match_table.find_all('tr')
        for row in rows:
            row_classes = row.get('class', [])
            if 'flags' in row_classes or 'head' in row_classes:
                tournament_element = row.find('td', class_='t-name')
                if tournament_element:
                    current_tournament = tournament_element.get_text(strip=True)
                    norm_tournament = normalize_name(current_tournament)
                    if FILTER_LOW_LEVEL_TOURNAMENTS:
                        if any(keyword.lower() in norm_tournament for keyword in [kw.lower() for kw in LOWER_LEVEL_KEYWORDS]):
                            current_tournament = None
                            continue
                continue
            if not current_tournament:
                continue
            row_id = row.get('id')
            if not row_id or 'b' in row_id:
                continue
            result_td = row.find('td', class_='result')
            if result_td and result_td.get_text(strip=True):
                continue
            player1_selector = f"#{row_id} > td:nth-child(2) > a:nth-child(1)"
            player2_selector = f"#{row_id}b > td:nth-child(1) > a:nth-child(1)"
            player1_element = soup.select_one(player1_selector)
            player2_element = soup.select_one(player2_selector)
            player1 = player1_element.get_text(strip=True) if player1_element else "Unknown Player"
            player2 = player2_element.get_text(strip=True) if player2_element else "Unknown Player"
            if '/' in player1 or '/' in player2:
                continue
            match_identifier = tuple(sorted([player1, player2]))
            if match_identifier in processed_matches:
                continue
            processed_matches.add(match_identifier)
            cells = row.find_all('td')
            if len(cells) > 10:
                odds_text_1 = cells[9].get_text(strip=True)
                odds_text_2 = cells[10].get_text(strip=True)
                if odds_text_1 and odds_text_2:
                    try:
                        moneyline_odds_player1 = float(odds_text_1)
                        moneyline_odds_player2 = float(odds_text_2)
                    except ValueError:
                        continue
                    win_pct1, win_pct2 = calculate_implied_win_percentages(moneyline_odds_player1, moneyline_odds_player2)
                    if win_pct1 is None or win_pct2 is None:
                        continue
                    norm_tournament = normalize_name(current_tournament)
                    surface = surface_map.get(norm_tournament, "Unknown")
                    if surface == "Unknown":
                        UNMAPPED_SURFACE_MATCHES.append(current_tournament)
                    player1_raw = player1
                    player2_raw = player2
                    standardized_player1 = apply_name_mapping(player1, name_map)
                    standardized_player2 = apply_name_mapping(player2, name_map)
                    match_data = {
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'date': match_date,
                        'tournament': current_tournament,
                        'surface': surface,
                        'player1': standardized_player1,
                        'player1_raw': player1_raw,
                        'player2': standardized_player2,
                        'player2_raw': player2_raw,
                        'implied_win_pct_player1': win_pct1,
                        'implied_win_pct_player2': win_pct2
                    }
                    matches.append(match_data)
    return matches


# ===========================
# Section: Data Preparation
# Description: Prepares daily DataFrames from the scraped match data.
# ===========================
from datetime import timedelta

def prepare_daily_dataframes(surface_map, name_map):
    """
    For each day, fetch match data and convert it to a DataFrame.
    Returns a tuple: (daily_dataframes, successful_match_count, total_match_count)
    """
    today = datetime.today()
    processed_matches = set()
    daily_dataframes = {}
    successful_match_count = 0
    total_match_count = 0
    for i in range(MATCHES_TO_SCRAPE):
        day = today + timedelta(days=i)
        match_date = day.strftime("%Y-%m-%d")
        url = URL_TEMPLATE.format(year=day.year, month=day.month, day=day.day)
        logging.info(f"Fetching data for {match_date} from URL: {url}")
        day_matches = scrape_tennis_matches(url, match_date, processed_matches, day, surface_map, name_map)
        total_match_count += len(day_matches)
        for match in day_matches:
            if (normalize_name(match['player1_raw']) != normalize_name(match['player1']) and
                normalize_name(match['player2_raw']) != normalize_name(match['player2']) and
                match['surface'] != "Unknown"):
                successful_match_count += 1
        if not day_matches:
            daily_dataframes[match_date] = pd.DataFrame(columns=[
                'match_id', 'snapshot_time', 'date', 'tournament', 'surface',
                'player', 'opponent', 'player win%', 'opponent win%'
            ])
            continue
        rows = []
        for match in day_matches:
            match_id = create_match_id(match['player1'], match['player2'], day)
            snapshot_time = match['timestamp']
            row1 = {
                'match_id': match_id,
                'snapshot_time': snapshot_time,
                'date': match['date'],
                'tournament': match['tournament'],
                'surface': match['surface'],
                'player': match['player1'],
                'opponent': match['player2'],
                'player win%': match['implied_win_pct_player1'],
                'opponent win%': match['implied_win_pct_player2']
            }
            row2 = {
                'match_id': match_id,
                'snapshot_time': snapshot_time,
                'date': match['date'],
                'tournament': match['tournament'],
                'surface': match['surface'],
                'player': match['player2'],
                'opponent': match['player1'],
                'player win%': match['implied_win_pct_player2'],
                'opponent win%': match['implied_win_pct_player1']
            }
            rows.extend([row1, row2])
        daily_df = pd.DataFrame(rows, columns=[
            'match_id', 'snapshot_time', 'date', 'tournament', 'surface',
            'player', 'opponent', 'player win%', 'opponent win%'
        ])
        daily_dataframes[match_date] = daily_df
    return daily_dataframes, successful_match_count, total_match_count


# ===========================
# Section: Database Persistence
# Description: Saves snapshot data into a SQLite database.
# ===========================
import sqlite3

def save_to_db(daily_dataframes, db_filename="odds.db"):
    """
    Saves each snapshot from the daily dataframes to a SQLite database.
    """
    conn = sqlite3.connect(db_filename)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS odds_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id TEXT,
            snapshot_time TEXT,
            date TEXT,
            tournament TEXT,
            surface TEXT,
            player TEXT,
            opponent TEXT,
            player_win_pct REAL,
            opponent_win_pct REAL
        )
    """)
    conn.commit()
    for match_date, df in daily_dataframes.items():
        if df.empty:
            continue
        for _, row in df.iterrows():
            cursor.execute("""
                INSERT INTO odds_snapshots (match_id, snapshot_time, date, tournament, surface, player, opponent, player_win_pct, opponent_win_pct)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row['match_id'],
                row['snapshot_time'],
                row['date'],
                row['tournament'],
                row['surface'],
                row['player'],
                row['opponent'],
                row['player win%'],
                row['opponent win%']
            ))
    conn.commit()
    conn.close()
    logging.info(f"Snapshot data saved to database '{db_filename}'.")


# ===========================
# Section: Fuzzy Match Confirmation
# Description: Prompts the user to confirm fuzzy matches and updates the name mapping CSV if confirmed.
# ===========================
def confirm_fuzzy_matches(mapping_csv="name_map.csv"):
    """
    For each fuzzy match logged, prompt the user whether to update the mapping file.
    If confirmed, append a new row to the CSV mapping file.
    """
    for entry in FUZZY_MATCHES:
        prompt = (f"\nFuzzy Match Detected:\n"
                  f"Scraped Name: '{entry['scraped_original']}' (normalized: '{entry['scraped_normalized']}')\n"
                  f"Mapping CSV row {entry['csv_row']}: '{entry['mapping_raw']}' (standardized: '{entry['mapping_standardized']}')\n"
                  f"Fuzzy Score: {entry['score']}\n"
                  f"Do you want to add a new mapping so that '{entry['scraped_original']}' maps exactly to '{entry['mapping_standardized']}'? (y/N): ")
        response = input(prompt)
        if response.lower() == "y":
            update_name_mapping_csv(entry, filename=mapping_csv)


# ===========================
# Section: Main Entry Point
# Description: Entry point for the live odds microservice.
# ===========================
import os

def main():
    logging.info(f"Current working directory: {os.getcwd()}")
    for item in os.listdir():
        logging.debug(f"Found file: {item}")
    
    surface_map = load_surface_map("surface_map.csv")
    name_map = load_name_map("name_map.csv")
    
    if not surface_map:
        logging.warning("Surface map is empty or failed to load. Surfaces will be 'Unknown'.")
    if not name_map:
        logging.warning("Name map is empty or failed to load. Player names will remain as scraped.")
    
    daily_dataframes, success_count, total_count = prepare_daily_dataframes(surface_map, name_map)
    
    if PRINT_SAMPLE_DATA:
        sample_day = list(daily_dataframes.keys())[0]
        logging.info(f"Sample data for {sample_day}:")
        logging.info(f"\n{daily_dataframes[sample_day].head(5)}")
    
    if SAVE_TO_DB:
        save_to_db(daily_dataframes)
    else:
        logging.info("SAVE_TO_DB is disabled. Snapshot data was not saved to the database.")
    
    # Summary Report
    logging.info("\n===== Summary Report =====")
    logging.info(f"Total matches scraped: {total_count}")
    logging.info(f"Successfully processed matches (standardized names and valid surface): {success_count}")
    
    if FUZZY_MATCHES:
        logging.info("\nFuzzy Matches (logged for review):")
        for entry in FUZZY_MATCHES:
            logging.info(f"  Scraped '{entry['scraped_original']}' (normalized: '{entry['scraped_normalized']}') -> "
                         f"Mapping CSV row {entry['csv_row']}: '{entry['mapping_raw']}' (standardized: '{entry['mapping_standardized']}') "
                         f"(score: {entry['score']})")
        if CONFIRM_FUZZY_MATCHES:
            confirm_fuzzy_matches(mapping_csv="name_map.csv")
    else:
        logging.info("\nNo fuzzy matches were recorded.")
    
    if UNMAPPED_SURFACE_MATCHES:
        logging.info("\nMatches with unmapped tournament surfaces:")
        for tournament in set(UNMAPPED_SURFACE_MATCHES):
            logging.info(f"  {tournament}")
    else:
        logging.info("\nAll tournaments were successfully mapped to a surface.")
    
if __name__ == "__main__":
    main()
