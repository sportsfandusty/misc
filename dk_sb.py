import requests
import json
import time

# Define headers for requests
headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "Priority": "u=0"
}

# Base URL components
BASE_URL = "https://sportsbook-nash.draftkings.com/api/sportscontent/dkusoh/v1/leagues/{leagueId}/categories/{categoryId}/subcategories/{subcategoryId}"

# Main function to extract data
def fetch_and_save_selections(league_id, categories, subcategories):
    all_data = {}

    for subcategory in subcategories:
        category_id = subcategory.get("categoryId")
        subcategory_id = subcategory.get("id")
        subcategory_name = subcategory.get("name", "Unknown Subcategory")

        # Construct endpoint for each subcategory
        endpoint = BASE_URL.format(leagueId=league_id, categoryId=category_id, subcategoryId=subcategory_id)
        print(f"Fetching data from URL: {endpoint}")

        # Fetch data from constructed endpoint
        response = requests.get(endpoint, headers=headers)
        if response.status_code == 200:
            print(f"Received status code 200 for subcategory {subcategory_name} (ID: {subcategory_id})")
            data = response.json()

            # Debug: Print the raw JSON structure to examine
            print("Raw JSON data received:")
            print(json.dumps(data, indent=4))  # Only for troubleshooting, remove after verifying structure

            # Extract selections data
            extracted_selections = extract_selections_data(data)
            if extracted_selections:
                all_data[f"{category_id}_{subcategory_id}"] = extracted_selections
            else:
                print(f"No selections data found for subcategory {subcategory_name} (ID: {subcategory_id})")

            # Add delay to avoid rate limiting
            time.sleep(1)
        else:
            print(f"Failed to fetch data for {subcategory_name} (ID: {subcategory_id}). Status code: {response.status_code}")

    # Save data to a JSON file
    output_filename = f"league_{league_id}_selections_data.json"
    with open(output_filename, 'w') as f:
        json.dump(all_data, f, indent=4)
    print(f"Data successfully saved to {output_filename}")

# Extract selections data from API response
def extract_selections_data(data):
    selections_data = []

    # Debug: Print key access points
    if "events" not in data:
        print("No 'events' key found in data.")
        return selections_data

    for event in data.get("events", []):
        event_id = event.get("eventId")
        event_name = event.get("name", "Unknown Event")
        participants = {p["id"]: p.get("name", "Unknown") for p in event.get("participants", [])}

        for market in event.get("markets", []):
            market_id = market.get("id")
            market_name = market.get("name", "Unknown Market")

            for selection in market.get("selections", []):
                selection_data = {
                    "event_id": event_id,
                    "event_name": event_name,
                    "market_id": market_id,
                    "market_name": market_name,
                    "selection_id": selection.get("id"),
                    "label": selection.get("label"),
                    "odds": selection.get("displayOdds", {}),
                    "outcome_type": selection.get("outcomeType"),
                    "points": selection.get("points"),
                    "participants": [
                        participants.get(p["id"], "Unknown") for p in selection.get("participants", [])
                    ]
                }
                selections_data.append(selection_data)

            # Debug: Log empty markets or selections if not found
            if not market.get("selections"):
                print(f"No selections found in market '{market_name}' (Market ID: {market_id}) for event '{event_name}' (Event ID: {event_id})")

    return selections_data

# Sample categories and subcategories input (Normally, you'd retrieve these from another API call)
categories = [
    {"id": 492, "name": "Game Lines"},
]
subcategories = [
    {"id": 13195, "categoryId": 492, "name": "Alternate Spread"},
]

# Run the main function
if __name__ == "__main__":
    league_id = 88808  # NFL League ID as an example
    fetch_and_save_selections(league_id, categories, subcategories)
