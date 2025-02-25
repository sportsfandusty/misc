"""
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
