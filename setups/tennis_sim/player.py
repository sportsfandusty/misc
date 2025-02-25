"""
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
