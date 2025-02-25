#!/usr/bin/env python3
"""
This script generates the tennis_sim package.
It creates the following directory structure:

tennis_sim/
    __init__.py
    player.py         # Contains the TennisPlayer class
    serve.py          # Contains the ServeSimulator class (with ace variance adjustments)
    rally.py          # Contains the RallySimulator class (using weighted rally-length brackets)
    point.py          # Contains the PointSimulator class (combining serve and rally)
    expected.py       # Contains the compute_expected_outcomes() function
    run_sim.py        # A sample script to simulate 5000 points and print a detailed summary

Run this script to generate the package files.
"""

import os

# Define package directory name
package_dir = "tennis_sim"

# Create directory if it doesn't exist
os.makedirs(package_dir, exist_ok=True)

# Define file names and their contents
files = {
    "__init__.py": '''"""
tennis_sim package: Contains simulation components for tennis matches.
"""

from .player import TennisPlayer
from .serve import ServeSimulator
from .rally import RallySimulator
from .point import PointSimulator
from .expected import compute_expected_outcomes
''',

    "player.py": '''"""
player.py: Contains the TennisPlayer class.
"""

class TennisPlayer:
    def __init__(self, name, elo, stats):
        """
        :param name: str, player's name.
        :param elo: int or float, player's Elo rating.
        :param stats: dict, player's performance statistics.
        """
        self.name = name
        self.elo = elo
        self.stats = stats
        # Tracking events during simulation.
        self.point_stats = {
            'Aces': 0,
            'Double Faults': 0,
            'Serve & Volley Wins': 0,
            'Serve & Volley Losses': 0,
            'Points Won on Serve': 0,         # Immediate wins (ace or S&V win)
            'Rally Wins as Server': 0,         # Rally wins when serving
            'Rally Wins as Receiver': 0,       # Rally wins when receiving
        }
''',

    "serve.py": '''"""
serve.py: Contains the ServeSimulator class.
This module simulates first and second serves with Elo adjustments
and introduces variance into the ace chance calculation.
"""

import random

from .player import TennisPlayer
LEAGUE_AVG_ELO = 1500
ELO_ADJUSTMENT_FACTOR = 0.05

class ServeSimulator:
    @staticmethod
    def simulate_first_serve(server: TennisPlayer, receiver: TennisPlayer):
        if random.random() * 100 < server.stats['first_serve_in_pct']:
            # First serve is in.
            base_ace = server.stats['ace_rate_1st']
            elo_factor = 1 + ELO_ADJUSTMENT_FACTOR * ((server.elo - receiver.elo) / LEAGUE_AVG_ELO)
            # Introduce variance and subtract only a fraction of the receiver's defensive stat.
            effective_ace_chance = base_ace * elo_factor - 0.5 * receiver.stats.get('ace_rate_against', 0)
            variance = random.uniform(0.9, 1.1)
            effective_ace_chance *= variance
            # Floor at a minimum chance (e.g., 0.5%)
            effective_ace_chance = max(0.5, effective_ace_chance)
            if random.random() * 100 < effective_ace_chance:
                server.point_stats['Aces'] += 1
                return 'ace'
            # Check serve-and-volley option.
            base_snv_freq = server.stats['serve_and_volley_freq']
            effective_snv_freq = base_snv_freq * elo_factor
            if random.random() * 100 < effective_snv_freq:
                base_snv_win = server.stats['serve_and_volley_win_pct']
                effective_snv_win = base_snv_win * elo_factor
                if random.random() * 100 < effective_snv_win:
                    server.point_stats['Serve & Volley Wins'] += 1
                    return 'serve_and_volley_win'
                else:
                    server.point_stats['Serve & Volley Losses'] += 1
                    return 'serve_and_volley_loss'
            return 'in_play'
        else:
            return None  # First serve fault.

    @staticmethod
    def simulate_second_serve(server: TennisPlayer, receiver: TennisPlayer):
        if random.random() * 100 < server.stats['double_fault_pct']:
            server.point_stats['Double Faults'] += 1
            return 'double_fault'
        base_ace_2nd = server.stats['ace_rate_2nd']
        elo_factor = 1 + ELO_ADJUSTMENT_FACTOR * ((server.elo - receiver.elo) / LEAGUE_AVG_ELO)
        effective_ace_chance_2nd = base_ace_2nd * elo_factor - 0.5 * receiver.stats.get('ace_rate_against', 0)
        variance = random.uniform(0.9, 1.1)
        effective_ace_chance_2nd *= variance
        effective_ace_chance_2nd = max(0.5, effective_ace_chance_2nd)
        if random.random() * 100 < effective_ace_chance_2nd:
            server.point_stats['Aces'] += 1
            return 'ace_2nd'
        return 'in_play'
''',

    "rally.py": '''"""
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
''',

    "point.py": '''"""
point.py: Contains the PointSimulator class.
This module integrates serve and rally phases to simulate a complete point.
"""

from .serve import ServeSimulator
from .rally import RallySimulator

class PointSimulator:
    @staticmethod
    def simulate_point(server, receiver):
        outcome = ServeSimulator.simulate_first_serve(server, receiver)
        if outcome is None:
            outcome = ServeSimulator.simulate_second_serve(server, receiver)
        if outcome in ['ace', 'ace_2nd', 'serve_and_volley_win']:
            server.point_stats['Points Won on Serve'] += 1
            return server.name
        elif outcome in ['double_fault', 'serve_and_volley_loss']:
            return receiver.name
        else:
            rally_winner, _ = RallySimulator.simulate_rally(server, receiver)
            if rally_winner == server.name:
                server.point_stats['Rally Wins as Server'] += 1
            else:
                receiver.point_stats['Rally Wins as Receiver'] += 1
            return rally_winner
''',

    "expected.py": '''"""
expected.py: Contains the compute_expected_outcomes function.
This module calculates the expected (base) outcome percentages for a serving player,
using a weighted rally-length distribution and adjustments.
"""

def compute_expected_outcomes(server, receiver):
    stats = server.stats
    elo_factor = 1 + 0.05 * ((server.elo - receiver.elo) / 1500)
    p_in = stats['first_serve_in_pct'] / 100.0

    # Effective ace chance on first serve.
    ace_first = max(0, stats['ace_rate_1st'] * elo_factor - stats.get('ace_rate_against', 0)) / 100.0
    expected_aces_first = p_in * ace_first

    # Effective ace chance on second serve.
    ace_second = max(0, stats['ace_rate_2nd'] * elo_factor - stats.get('ace_rate_against', 0)) / 100.0
    expected_aces_second = (1 - p_in) * (1 - stats['double_fault_pct'] / 100.0) * ace_second

    expected_aces = expected_aces_first + expected_aces_second
    expected_double_faults = (1 - p_in) * (stats['double_fault_pct'] / 100.0)

    effective_snv_freq = stats['serve_and_volley_freq'] * elo_factor / 100.0
    effective_snv_win = stats['serve_and_volley_win_pct'] * elo_factor / 100.0
    expected_snv_wins = p_in * effective_snv_freq * effective_snv_win
    expected_snv_losses = p_in * effective_snv_freq * (1 - effective_snv_win)

    expected_points_on_serve = (expected_aces + expected_snv_wins) * 100  # in %

    p_brackets = {'1-3': 0.30, '4-6': 0.40, '7-9': 0.20, '10+': 0.10}
    weighted_rally = (
        p_brackets['1-3'] * stats['rally_1_3_win'] +
        p_brackets['4-6'] * stats['rally_4_6_win'] +
        p_brackets['7-9'] * stats['rally_7_9_win'] +
        p_brackets['10+'] * stats['rally_10plus_win']
    )
    effective_rally_win = ((weighted_rally + (100 - stats['return_RiPW'])) / 2.0) * elo_factor / 100.0
    prob_rally = 1 - (expected_aces + expected_snv_wins + expected_double_faults + expected_snv_losses)
    expected_rally_win = prob_rally * effective_rally_win * 100

    return {
        'Aces': expected_aces * 100,
        'Double Faults': expected_double_faults * 100,
        'Serve & Volley Wins': expected_snv_wins * 100,
        'Serve & Volley Losses': expected_snv_losses * 100,
        'Points Won on Serve': expected_points_on_serve,
        'Rally Wins as Server': expected_rally_win,
    }
''',

    "run_sim.py": '''"""
run_sim.py: A sample script to run the point simulation.
This script simulates 5,000 points with alternating serves between two players
(using real-life stats for Iga Swiatek and Aryna Sabalenka) and prints a detailed summary.
"""

from tennis_sim.player import TennisPlayer
from tennis_sim.point import PointSimulator
from tennis_sim.expected import compute_expected_outcomes

def main():
    # Real-life stats for Iga Swiatek (subset)
    iga_stats = {
        'first_serve_in_pct': 63.3,
        'ace_rate_1st': 5.7,
        'ace_rate_2nd': 2.0,
        'double_fault_pct': 4.0,
        'serve_and_volley_freq': 0.0,
        'serve_and_volley_win_pct': 0.0,
        'rally_1_3_win': 54.2,
        'rally_4_6_win': 57.0,
        'rally_7_9_win': 55.2,
        'rally_10plus_win': 63.1,
        'ace_rate_against': 4.4,
        'return_RiPW': 50.5,
    }

    # Real-life stats for Aryna Sabalenka (subset)
    sabalenka_stats = {
        'first_serve_in_pct': 65.7,
        'ace_rate_1st': 3.2,
        'ace_rate_2nd': 1.2,
        'double_fault_pct': 2.9,
        'serve_and_volley_freq': 0.5,
        'serve_and_volley_win_pct': 66.7,
        'rally_1_3_win': 52.6,
        'rally_4_6_win': 56.4,
        'rally_7_9_win': 50.3,
        'rally_10plus_win': 54.2,
        'ace_rate_against': 4.3,
        'return_RiPW': 58.6,
    }

    # Create players with Elo ratings.
    iga = TennisPlayer("Iga Swiatek", elo=2050, stats=iga_stats)
    aryna = TennisPlayer("Aryna Sabalenka", elo=2000, stats=sabalenka_stats)

    total_points = 5000
    serves_per_player = total_points / 2  # 2,500 serves per player

    total_points_iga = 0
    total_points_aryna = 0

    # Simulate 5,000 points with alternating serve.
    for i in range(total_points):
        if i % 2 == 0:
            winner = PointSimulator.simulate_point(iga, aryna)
            if winner == iga.name:
                total_points_iga += 1
            else:
                total_points_aryna += 1
        else:
            winner = PointSimulator.simulate_point(aryna, iga)
            if winner == aryna.name:
                total_points_aryna += 1
            else:
                total_points_iga += 1

    # Compute simulated per-serve percentages.
    def simulated_rate(player):
        return {
            'Aces': (player.point_stats['Aces'] / serves_per_player) * 100,
            'Double Faults': (player.point_stats['Double Faults'] / serves_per_player) * 100,
            'Serve & Volley Wins': (player.point_stats['Serve & Volley Wins'] / serves_per_player) * 100,
            'Serve & Volley Losses': (player.point_stats['Serve & Volley Losses'] / serves_per_player) * 100,
            'Points Won on Serve': (player.point_stats['Points Won on Serve'] / serves_per_player) * 100,
            'Rally Wins as Server': (player.point_stats['Rally Wins as Server'] / serves_per_player) * 100,
        }
    
    sim_rates_iga = simulated_rate(iga)
    sim_rates_aryna = simulated_rate(aryna)

    expected_iga = compute_expected_outcomes(iga, aryna)
    expected_aryna = compute_expected_outcomes(aryna, iga)

    def print_summary(player_name, expected, simulated):
        print(f"{player_name}:")
        print(f"{'Event':<25}{'Base Rate (%)':>15}{'Simulated (%)':>20}{'Difference (%)':>20}")
        print("-" * 80)
        for event in expected.keys():
            base_rate = expected[event]
            sim_rate = simulated.get(event, 0)
            diff = sim_rate - base_rate
            print(f"{event:<25}{base_rate:15.2f}{sim_rate:20.2f}{diff:20.2f}")
        print("\n")
    
    print("\n--- Summary of 5,000 Points (Per-Serve Rates) ---\n")
    print_summary(f"Iga Swiatek (Serving vs Aryna Sabalenka, Elo: {iga.elo})", expected_iga, sim_rates_iga)
    print_summary(f"Aryna Sabalenka (Serving vs Iga Swiatek, Elo: {aryna.elo})", expected_aryna, sim_rates_aryna)
    
    print("Overall Points Won:")
    print(f"  Iga Swiatek: {total_points_iga} points")
    print(f"  Aryna Sabalenka: {total_points_aryna} points\n")
    
    print("Detailed Point Stats (Absolute counts):")
    print(f"Iga Swiatek: {iga.point_stats}")
    print(f"Aryna Sabalenka: {aryna.point_stats}")
    
    print("\\nNote: Base rates are computed from the input stats (adjusted by Elo and opposing stats),")
    print("and the rally calculations now use a weighted distribution of rally lengths.")

if __name__ == "__main__":
    main()
''',
}

# Write out each file
for filename, content in files.items():
    filepath = os.path.join(package_dir, filename)
    with open(filepath, "w") as f:
        f.write(content)
    print(f"Created {filepath}")

print("\nPackage 'tennis_sim' created successfully!")
