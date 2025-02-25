"""
rally.py: Contains the RallySimulator class.
This module simulates the rally phase using a weighted distribution of rally lengths.
"""

import random
from .player import TennisPlayer
LEAGUE_AVG_ELO = 1500
ELO_ADJUSTMENT_FACTOR = 0.05

class RallySimulator:
    @staticmethod
    def simulate_rally(server: TennisPlayer, receiver: TennisPlayer):
        # Define rally-length brackets: (label, low, high, probability)
        brackets = [
            ("1-3", 1, 3, 0.30),
            ("4-6", 4, 6, 0.40),
            ("7-9", 7, 9, 0.20),
            ("10+", 10, 15, 0.10)
        ]
        r = random.random()
        cumulative = 0
        selected_bracket = None
        for label, low, high, prob in brackets:
            cumulative += prob
            if r < cumulative:
                selected_bracket = (label, low, high)
                break
        if selected_bracket is None:
            selected_bracket = ("10+", 10, 15)
        label, low, high = selected_bracket
        rally_length = random.randint(low, high)
        # Select the base rally win percentage from server's stats based on bracket.
        if label == "1-3":
            base_rally_win = server.stats['rally_1_3_win']
        elif label == "4-6":
            base_rally_win = server.stats['rally_4_6_win']
        elif label == "7-9":
            base_rally_win = server.stats['rally_7_9_win']
        else:
            base_rally_win = server.stats['rally_10plus_win']
        receiver_defense = 100 - receiver.stats.get('return_RiPW', 50)
        elo_factor = 1 + ELO_ADJUSTMENT_FACTOR * ((server.elo - receiver.elo) / LEAGUE_AVG_ELO)
        effective_rally_win = ((base_rally_win + receiver_defense) / 2) * elo_factor / 100.0
        if random.random() < effective_rally_win:
            return server.name, rally_length
        else:
            return receiver.name, rally_length
