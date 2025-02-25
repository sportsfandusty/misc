"""
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
