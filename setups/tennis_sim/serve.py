"""
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
