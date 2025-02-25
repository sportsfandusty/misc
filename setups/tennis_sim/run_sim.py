"""
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
        print("
")
    
    print("
--- Summary of 5,000 Points (Per-Serve Rates) ---
")
    print_summary(f"Iga Swiatek (Serving vs Aryna Sabalenka, Elo: {iga.elo})", expected_iga, sim_rates_iga)
    print_summary(f"Aryna Sabalenka (Serving vs Iga Swiatek, Elo: {aryna.elo})", expected_aryna, sim_rates_aryna)
    
    print("Overall Points Won:")
    print(f"  Iga Swiatek: {total_points_iga} points")
    print(f"  Aryna Sabalenka: {total_points_aryna} points
")
    
    print("Detailed Point Stats (Absolute counts):")
    print(f"Iga Swiatek: {iga.point_stats}")
    print(f"Aryna Sabalenka: {aryna.point_stats}")
    
    print("\nNote: Base rates are computed from the input stats (adjusted by Elo and opposing stats),")
    print("and the rally calculations now use a weighted distribution of rally lengths.")

if __name__ == "__main__":
    main()
