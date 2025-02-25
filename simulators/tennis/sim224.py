#!/usr/bin/env python3
# File: point_simulator_5000.py
# Description: This script simulates 5,000 tennis points between two players (Iga Swiatek and Aryna Sabalenka)
# with alternating serves. It uses detailed serve, rally, and return statistics—with an improved rally logic
# that uses a weighted distribution of rally lengths—and Elo adjustments.
#
# In this version, we separate rally wins achieved when a player is serving ("Rally Wins as Server")
# from those when the player is receiving. We also count the total points each player wins (across both roles).
#
# After simulation, a summary table is printed for each player showing, for each key event:
#    • Base Rate (%) – The expected rate (adjusted by Elo and opposing stats)
#    • Simulated Rate (%) – The rate observed in simulation (per serve)
#    • Difference (%) – (Simulated Rate - Base Rate)
#
# In addition, the overall total points won (when serving or receiving) are printed.
#
# Key events tracked include:
#   • Aces
#   • Double Faults
#   • Serve & Volley Wins
#   • Serve & Volley Losses
#   • Points Won on Serve (immediate wins: ace or serve-&-volley win)
#   • Rally Wins as Server (rally wins when serving)
#
# The expected rally win probability is computed as a weighted average over four rally-length brackets:
#   - 1-3 shots (30% chance)
#   - 4-6 shots (40% chance)
#   - 7-9 shots (20% chance)
#   - 10+ shots (10% chance)
# Each bracket’s base rally win rate is taken from the server’s stats and then adjusted by the receiver’s
# defensive metric (return_RiPW) and an Elo factor.

import random

# Global league parameters
LEAGUE_AVG_ELO = 1500
ELO_ADJUSTMENT_FACTOR = 0.05  # Sensitivity constant for Elo adjustments

# ---------------------------------------------------------------------------
# TennisPlayer: Holds a player's attributes and tracks point-level events.
# ---------------------------------------------------------------------------
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
        # Track events during simulation.
        # We record rally wins separately depending on serving or receiving.
        self.point_stats = {
            'Aces': 0,
            'Double Faults': 0,
            'Serve & Volley Wins': 0,
            'Serve & Volley Losses': 0,
            'Points Won on Serve': 0,         # Immediate wins when serving (ace or S&V win)
            'Rally Wins as Server': 0,         # Rally wins when serving
            'Rally Wins as Receiver': 0,       # Rally wins when receiving
        }

# ---------------------------------------------------------------------------
# ServeSimulator: Handles first and second serve simulations with Elo adjustments.
# ---------------------------------------------------------------------------
# In ServeSimulator.simulate_first_serve, replace the effective ace calculation with:
class ServeSimulator:
    @staticmethod
    def simulate_first_serve(server: TennisPlayer, receiver: TennisPlayer):
        if random.random() * 100 < server.stats['first_serve_in_pct']:
            # First serve is in.
            base_ace = server.stats['ace_rate_1st']
            elo_factor = 1 + ELO_ADJUSTMENT_FACTOR * ((server.elo - receiver.elo) / LEAGUE_AVG_ELO)
            # Instead of subtracting the full receiver's defensive stat, subtract only half,
            # and then multiply by a random variance factor (e.g., between 0.9 and 1.1).
            effective_ace_chance = base_ace * elo_factor - 0.5 * receiver.stats.get('ace_rate_against', 0)
            variance = random.uniform(0.9, 1.1)
            effective_ace_chance *= variance
            # Ensure a floor so that there is always at least a small chance (e.g., 0.5%).
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
# ---------------------------------------------------------------------------
# RallySimulator: Handles simulation of the rally phase using a weighted rally-length distribution.
# ---------------------------------------------------------------------------
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
        # Choose base rally win % from server's stats based on bracket.
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

# ---------------------------------------------------------------------------
# PointSimulator: Integrates serve and rally phases to simulate a complete point.
# ---------------------------------------------------------------------------
class PointSimulator:
    @staticmethod
    def simulate_point(server: TennisPlayer, receiver: TennisPlayer):
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

# ---------------------------------------------------------------------------
# compute_expected_outcomes: Computes expected (base) outcome rates for a serving player,
# using a weighted rally-length distribution.
# ---------------------------------------------------------------------------
def compute_expected_outcomes(server: TennisPlayer, receiver: TennisPlayer):
    stats = server.stats
    elo_factor = 1 + ELO_ADJUSTMENT_FACTOR * ((server.elo - receiver.elo) / LEAGUE_AVG_ELO)
    p_in = stats['first_serve_in_pct'] / 100.0

    # Effective ace chance on first serve:
    ace_first = max(0, stats['ace_rate_1st'] * elo_factor - stats.get('ace_rate_against', 0)) / 100.0
    expected_aces_first = p_in * ace_first

    # Effective ace chance on second serve:
    ace_second = max(0, stats['ace_rate_2nd'] * elo_factor - stats.get('ace_rate_against', 0)) / 100.0
    expected_aces_second = (1 - p_in) * (1 - stats['double_fault_pct'] / 100.0) * ace_second

    expected_aces = expected_aces_first + expected_aces_second

    expected_double_faults = (1 - p_in) * (stats['double_fault_pct'] / 100.0)

    effective_snv_freq = stats['serve_and_volley_freq'] * elo_factor / 100.0
    effective_snv_win = stats['serve_and_volley_win_pct'] * elo_factor / 100.0
    expected_snv_wins = p_in * effective_snv_freq * effective_snv_win
    expected_snv_losses = p_in * effective_snv_freq * (1 - effective_snv_win)

    expected_points_on_serve = (expected_aces + expected_snv_wins) * 100  # as percentage

    # For rally, using weighted probabilities for each bracket:
    p_brackets = {'1-3': 0.30, '4-6': 0.40, '7-9': 0.20, '10+': 0.10}
    weighted_rally = (
        p_brackets['1-3'] * stats['rally_1_3_win'] +
        p_brackets['4-6'] * stats['rally_4_6_win'] +
        p_brackets['7-9'] * stats['rally_7_9_win'] +
        p_brackets['10+'] * stats['rally_10plus_win']
    )
    effective_rally_win = ((weighted_rally + (100 - stats['return_RiPW'])) / 2.0) * elo_factor / 100.0
    prob_rally = 1 - (expected_aces + expected_snv_wins + expected_double_faults + expected_snv_losses)
    expected_rally_win = prob_rally * effective_rally_win * 100  # as percentage

    return {
        'Aces': expected_aces * 100,
        'Double Faults': expected_double_faults * 100,
        'Serve & Volley Wins': expected_snv_wins * 100,
        'Serve & Volley Losses': expected_snv_losses * 100,
        'Points Won on Serve': expected_points_on_serve,
        'Rally Wins as Server': expected_rally_win,
    }

# ---------------------------------------------------------------------------
# Main Execution: Simulate 5,000 points with alternating serve and display detailed summary.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Real-life stats for Iga Swiatek (subset from your table)
    iga_stats = {
        'first_serve_in_pct': 63.3,    # 1st In%
        'ace_rate_1st': 5.7,           # Ace%
        'ace_rate_2nd': 2.0,           # Estimated second serve ace rate
        'double_fault_pct': 4.0,       # DF%
        'serve_and_volley_freq': 0.0,  # Iga rarely serves-and-volley
        'serve_and_volley_win_pct': 0.0,
        # Rally win percentages (for different rally lengths)
        'rally_1_3_win': 54.2,
        'rally_4_6_win': 57.0,
        'rally_7_9_win': 55.2,
        'rally_10plus_win': 63.1,
        # Return stats
        'ace_rate_against': 4.4,       # vAce%
        'return_RiPW': 50.5,           # Opponent’s return win %
    }

    # Real-life stats for Aryna Sabalenka (subset from your table)
    sabalenka_stats = {
        'first_serve_in_pct': 65.7,
        'ace_rate_1st': 3.2,
        'ace_rate_2nd': 1.2,
        'double_fault_pct': 2.9,
        'serve_and_volley_freq': 0.5,  # small chance of serve-and-volley
        'serve_and_volley_win_pct': 66.7,
        'rally_1_3_win': 52.6,
        'rally_4_6_win': 56.4,
        'rally_7_9_win': 50.3,
        'rally_10plus_win': 54.2,
        'ace_rate_against': 4.3,
        'return_RiPW': 58.6,
    }
    
    # Create players with Elo ratings (using our advanced stats)
    iga = TennisPlayer("Iga Swiatek", elo=2050, stats=iga_stats)
    aryna = TennisPlayer("Aryna Sabalenka", elo=2000, stats=sabalenka_stats)
    
    total_points = 5000
    serves_per_player = total_points / 2  # 2,500 serves per player

    # Counters for total points won (regardless of serving)
    total_points_iga = 0
    total_points_aryna = 0

    # Alternate serve: even-indexed points => Iga serves; odd-indexed => Aryna serves.
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
    
    # Function to calculate simulated per-serve percentages for a serving player.
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
    
    # Function to print a summary table.
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
    
    print("\nNote: Base rates are computed from the input stats (adjusted by Elo and opposing stats),")
    print("and the rally calculations now use a weighted distribution of rally lengths.")
