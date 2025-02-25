import requests
from pprint import pprint

# API Configuration
BASE_URL = "https://api.bettingpros.com/v3"
BASE_URL_EVENTS = f"{BASE_URL}/events"
BASE_URL_OFFERS = f"{BASE_URL}/offers"
API_KEY = "CHi8Hy5CEE4khd46XNYL23dCFX96oUdw6qOt1Dnh"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "x-api-key": API_KEY,
}

BOOKIE_MAP = {
    0: "BettingPros",
    10: "Fanduel",
    12: "DraftKings",
    13: "Caesars",
    18: "BetRivers",
    19: "BetMGM",
    24: "Bet365",
    33: "ESPNBet",
}

MARKET_CONFIG = {
    'game_lines': {
        'moneyline': 1,
        'spread': 3,
        'total': 2
    },
    'props': {
        102: "Passing Touchdowns",
        103: "Passing Yards",
        333: "Pass Attempts",
        100: "Completions",
        101: "Interceptions",
        106: "Rush Attempts",
        107: "Rush Yards",
        104: "Receptions",
        105: "Receiving Yards",
        253: "Fantasy Points",
    }
}

class BettingAPI:
    def fetch_events(self, sport="NFL", week=19, season=2024):
        params = {
            "sport": sport,
            "week": week,
            "season": season
        }
        try:
            response = requests.get(BASE_URL_EVENTS, headers=HEADERS, params=params)
            response.raise_for_status()
            events = response.json().get('events', [])
            return [str(event['id']) for event in events]  # Removed slicing to get all events
        except Exception as e:
            print(f"Error fetching events: {e}")
            return []

    def fetch_all_offers(self, market_id, event_ids):
        if not event_ids:
            return []
        
        offers = []
        # Assuming the API supports pagination, you might need to handle it here.
        # For simplicity, we'll fetch without a limit parameter to get all offers.
        params = {
            "sport": "NFL",
            "market_id": market_id,
            "event_id": ','.join(event_ids),
            "location": "OH",
            # Removed 'limit': 1 to fetch all offers
        }
        try:
            response = requests.get(BASE_URL_OFFERS, headers=HEADERS, params=params)
            response.raise_for_status()
            data = response.json()
            offers.extend(data.get('offers', []))
            # If the API uses pagination, handle additional pages here
            return offers
        except Exception as e:
            print(f"Error fetching offers: {e}")
            return []

class MarketPrinter:
    def __init__(self):
        self.api = BettingAPI()
        self.event_ids = self.api.fetch_events()

    def print_game_lines(self, market_name, market_id):
        print(f"\n{market_name.upper()} (Market ID: {market_id})")
        print("-" * 40)
        
        offers = self.api.fetch_all_offers(market_id, self.event_ids)
        if offers:
            for offer in offers:
                # Print teams
                teams = [p['name'] for p in offer.get('participants', [])]
                if teams:
                    print(f"Teams: {' vs '.join(teams)}")
                
                # Print lines for each book
                for selection in offer.get('selections', []):
                    for book in selection.get('books', []):
                        bookie = BOOKIE_MAP.get(book['id'], str(book['id']))
                        for line in book.get('lines', []):
                            if line.get('active') and not line.get('replaced'):
                                odds = line.get('cost')
                                line_value = line.get('line')
                                
                                if market_name == 'total':
                                    print(f"{bookie}: {selection['label']} {line_value} ({odds})")
                                else:
                                    print(f"{bookie}: {selection['label']} {f'{line_value} ' if line_value != 1 else ''}({odds})")
                print("-" * 40)  # Separator between offers
        else:
            print("No offers found for this market.")

    def print_props(self, market_name, market_id):
        print(f"\n{market_name} (Market ID: {market_id})")
        print("-" * 40)
        
        offers = self.api.fetch_all_offers(market_id, self.event_ids)
        if offers:
            for offer in offers:
                # Print player info
                if offer.get('participants'):
                    player = offer['participants'][0].get('player', {})
                    print(f"Player: {player.get('first_name', '')} {player.get('last_name', '')} "
                          f"({player.get('position', '')}) - {player.get('team', '')}")
                
                # Print lines for each book
                for selection in offer.get('selections', []):
                    for book in selection.get('books', []):
                        bookie = BOOKIE_MAP.get(book['id'], str(book['id']))
                        for line in book.get('lines', []):
                            if line.get('active') and not line.get('replaced'):
                                odds = line.get('cost')
                                line_value = line.get('line')
                                print(f"{bookie}: {selection['label']} {line_value} ({odds})")
                print("-" * 40)  # Separator between offers
        else:
            print("No offers found for this market.")

    def print_all_markets(self):
        # Print game lines markets
        print("\nGAME LINES MARKETS")
        print("=" * 50)
        for market_name, market_id in MARKET_CONFIG['game_lines'].items():
            self.print_game_lines(market_name, market_id)
            
        # Print props markets
        print("\nPROPS MARKETS")
        print("=" * 50)
        for market_id, market_name in MARKET_CONFIG['props'].items():
            self.print_props(market_name, market_id)

def main():
    printer = MarketPrinter()
    printer.print_all_markets()

if __name__ == "__main__":
    main()
