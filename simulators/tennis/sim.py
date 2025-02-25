# File: tennis_simulator_with_variance_and_momentum.py
# Description: Simulates a best-of-3 tennis match between Jannik Sinner and Carlos Alcaraz
#              while incorporating daily (good day/bad day) variation and in-match momentum.
#              Daily stats are generated from base stats using random multipliers,
#              and momentum is updated at break events and applied point-by-point.
#              Finally, the match result is scored using DraftKings fantasy scoring.

import random
import math

# -------------------------------
# Helper functions
# -------------------------------
def clip(value, min_value, max_value):
    """Ensure that value is between min_value and max_value."""
    return max(min_value, min(value, max_value))

def generate_daily_stats(base_stats):
    """
    Generate today's stats for a player based on their base_stats,
    applying random variation (good day/bad day effects).
    
    We use separate multipliers for serving and returning.
    For serving, a higher multiplier boosts AcePercentage, FirstServeWon% and SecondServeWon%,
    while reducing DoubleFaultPercentage.
    """
    # Draw multipliers from a normal distribution (mean 1.0, std dev 0.1), then clip.
    serve_form = clip(random.gauss(1.0, 0.1), 0.7, 1.3)
    return_form = clip(random.gauss(1.0, 0.1), 0.7, 1.3)
    
    daily = base_stats.copy()
    # Adjust serve-related stats
    daily['AcePercentage'] = clip(base_stats['AcePercentage'] * serve_form, 0, 1)
    daily['FirstServeWonPercentage'] = clip(base_stats['FirstServeWonPercentage'] * serve_form, 0, 1)
    daily['SecondServeWonPercentage'] = clip(base_stats['SecondServeWonPercentage'] * serve_form, 0, 1)
    # For first serve percentage, we assume it stays roughly constant
    daily['FirstServePercentage'] = base_stats['FirstServePercentage']
    # Inverse relation for double faults: better serve form => fewer DFs.
    daily['DoubleFaultPercentage'] = clip(base_stats['DoubleFaultPercentage'] / serve_form, 0, 1)
    
    # Adjust return-related stats
    daily['ReturnPointsWonPercentage'] = clip(base_stats['ReturnPointsWonPercentage'] * return_form, 0, 1)
    daily['BreakPointsConvertedPercentage'] = clip(base_stats['BreakPointsConvertedPercentage'] * return_form, 0, 1)
    
    # (Other stats remain as base stats for now)
    return daily

def apply_momentum_to_stats(daily_stats, momentum):
    """
    Adjust the player's daily stats based on current momentum.
    
    For a positive momentum, we slightly boost key percentages (e.g., Ace%,
    FirstServeWon%, SecondServeWon%) and reduce DoubleFault%.
    For a negative momentum, the reverse applies.
    """
    # Use a factor of 2% per momentum point.
    factor = 1.0 + 0.02 * momentum

    effective = daily_stats.copy()
    effective['AcePercentage'] = clip(daily_stats['AcePercentage'] * factor, 0, 1)
    effective['FirstServeWonPercentage'] = clip(daily_stats['FirstServeWonPercentage'] * factor, 0, 1)
    effective['SecondServeWonPercentage'] = clip(daily_stats['SecondServeWonPercentage'] * factor, 0, 1)
    # For double faults, if momentum is positive, we expect fewer DFs.
    # We divide by the same factor (ensuring factor is never 0).
    effective['DoubleFaultPercentage'] = clip(daily_stats['DoubleFaultPercentage'] / factor, 0, 1)
    
    # Other stats remain unchanged.
    effective['FirstServePercentage'] = daily_stats['FirstServePercentage']
    effective['ReturnPointsWonPercentage'] = daily_stats['ReturnPointsWonPercentage']
    effective['BreakPointsConvertedPercentage'] = daily_stats['BreakPointsConvertedPercentage']
    
    return effective

def update_momentum(player, event):
    """
    Update a player's momentum based on an event.
    
    For a break (winning on serve when not serving), add +1.
    For losing a break, subtract 1.
    We cap momentum between -3 and +3.
    """
    if event == 'win_break':
        player['momentum'] = clip(player['momentum'] + 1, -3, 3)
    elif event == 'lose_break':
        player['momentum'] = clip(player['momentum'] - 1, -3, 3)
    # Additional events (e.g., winning a tie-break) could also be added.
    return

# -------------------------------
# Simulation functions
# -------------------------------
def simulate_point(player):
    """
    Simulate a single point from the perspective of the server.
    The player's effective stats (daily stats adjusted by momentum) are used.
    
    Returns a tuple: (point_won, is_ace, is_double_fault)
    """
    # Compute effective stats for this point.
    stats = apply_momentum_to_stats(player['daily_stats'], player['momentum'])
    
    df_prob = stats['DoubleFaultPercentage']
    ace_prob = stats['AcePercentage']
    first_serve_pct = stats['FirstServePercentage']
    first_serve_win_pct = stats['FirstServeWonPercentage']
    second_serve_win_pct = stats['SecondServeWonPercentage']

    roll = random.random()
    # Check for double fault first.
    if roll < df_prob:
        return (False, False, True)
    
    # Then check for ace.
    roll2 = random.random()
    if roll2 < ace_prob:
        return (True, True, False)
    
    # Otherwise, use a weighted chance based on whether first serve was in.
    # Assume the server gets first serve with probability first_serve_pct.
    p_win = first_serve_pct * first_serve_win_pct + (1 - first_serve_pct) * second_serve_win_pct
    return (random.random() < p_win, False, False)

def simulate_game(server, receiver):
    """
    Simulate a single game.
    
    The server and receiver are dictionaries that hold their current daily stats and momentum.
    Returns a dictionary:
      {
         'winner': 'server' or 'receiver',
         'server_aces': int,
         'server_double_faults': int
      }
    """
    server_points = 0
    receiver_points = 0
    server_aces = 0
    server_double_faults = 0

    while True:
        point_won, is_ace, is_df = simulate_point(server)
        if point_won:
            server_points += 1
            if is_ace:
                server_aces += 1
        else:
            receiver_points += 1
        if is_df:
            server_double_faults += 1
        
        # Check if game is decided (win by 2 and at least 4 points)
        if (server_points >= 4 or receiver_points >= 4) and abs(server_points - receiver_points) >= 2:
            if server_points > receiver_points:
                return {'winner': 'server', 'server_aces': server_aces, 'server_double_faults': server_double_faults}
            else:
                return {'winner': 'receiver', 'server_aces': server_aces, 'server_double_faults': server_double_faults}

def simulate_tiebreak(server, receiver):
    """
    Simulate a tie-break (first to 7, win by 2).
    Serving rotates: first point by 'server', then every 2 points.
    Returns a dict similar to simulate_game.
    """
    server_points = 0
    receiver_points = 0
    server_aces = 0
    server_double_faults = 0

    current_server = 'server'
    point_count = 0

    while True:
        if current_server == 'server':
            point_won, is_ace, is_df = simulate_point(server)
            if point_won:
                server_points += 1
                if is_ace:
                    server_aces += 1
            else:
                receiver_points += 1
            if is_df:
                server_double_faults += 1
        else:
            # Receiver serves; use receiver's effective stats.
            point_won, is_ace, is_df = simulate_point(receiver)
            if point_won:
                receiver_points += 1
            else:
                server_points += 1
            # We track aces/DF only for the player whose stats we are tracking (here, for clarity, we track only when a given player is serving).
        
        point_count += 1
        if point_count == 1 or (point_count > 1 and (point_count - 1) % 4 == 0):
            current_server = 'receiver' if current_server == 'server' else 'server'
        
        if (server_points >= 7 or receiver_points >= 7) and abs(server_points - receiver_points) >= 2:
            if server_points > receiver_points:
                return {'winner': 'server', 'server_aces': server_aces, 'server_double_faults': server_double_faults}
            else:
                return {'winner': 'receiver', 'server_aces': server_aces, 'server_double_faults': server_double_faults}

def simulate_set(player1, player2, starting_server):
    """
    Simulate one set.
    
    'starting_server' is 1 or 2 (which player serves first).
    Alternates server each game.
    
    Returns a dict with set results and cumulative stats:
      {
        'winner': player1 or player2,
        'games_won_by_p1': int,
        'games_won_by_p2': int,
        'aces_by_p1': int,
        'aces_by_p2': int,
        'df_by_p1': int,
        'df_by_p2': int
      }
    Also updates players' momentum based on break events.
    """
    games_p1 = 0
    games_p2 = 0
    aces_p1 = 0
    aces_p2 = 0
    df_p1 = 0
    df_p2 = 0

    next_server = starting_server

    while True:
        if next_server == 1:
            # Player1 serves; if server wins, that's a hold.
            game_info = simulate_game(player1, player2)
            if game_info['winner'] == 'server':
                games_p1 += 1
            else:
                games_p2 += 1
                # Break: update momentum: receiver (player2) gains; server (player1) loses.
                update_momentum(player2, 'win_break')
                update_momentum(player1, 'lose_break')
            aces_p1 += game_info['server_aces']
            df_p1 += game_info['server_double_faults']
        else:
            # Player2 serves.
            game_info = simulate_game(player2, player1)
            if game_info['winner'] == 'server':
                games_p2 += 1
            else:
                games_p1 += 1
                update_momentum(player1, 'win_break')
                update_momentum(player2, 'lose_break')
            aces_p2 += game_info['server_aces']
            df_p2 += game_info['server_double_faults']

        # Check if set is won (6+ games with at least 2-game lead)
        if (games_p1 >= 6 or games_p2 >= 6) and abs(games_p1 - games_p2) >= 2:
            winner = player1 if games_p1 > games_p2 else player2
            return {
                'winner': winner,
                'games_won_by_p1': games_p1,
                'games_won_by_p2': games_p2,
                'aces_by_p1': aces_p1,
                'aces_by_p2': aces_p2,
                'df_by_p1': df_p1,
                'df_by_p2': df_p2
            }
        
        # Tie-break if 6-6
        if games_p1 == 6 and games_p2 == 6:
            if next_server == 1:
                tb_info = simulate_tiebreak(player1, player2)
                aces_p1 += tb_info['server_aces']
                df_p1 += tb_info['server_double_faults']
                if tb_info['winner'] == 'server':
                    games_p1 += 1
                else:
                    games_p2 += 1
                    update_momentum(player2, 'win_break')
                    update_momentum(player1, 'lose_break')
            else:
                tb_info = simulate_tiebreak(player2, player1)
                aces_p2 += tb_info['server_aces']
                df_p2 += tb_info['server_double_faults']
                if tb_info['winner'] == 'server':
                    games_p2 += 1
                else:
                    games_p1 += 1
                    update_momentum(player1, 'win_break')
                    update_momentum(player2, 'lose_break')
            winner = player1 if games_p1 > games_p2 else player2
            return {
                'winner': winner,
                'games_won_by_p1': games_p1,
                'games_won_by_p2': games_p2,
                'aces_by_p1': aces_p1,
                'aces_by_p2': aces_p2,
                'df_by_p1': df_p1,
                'df_by_p2': df_p2
            }
        
        next_server = 1 if next_server == 2 else 2

def simulate_match(player1, player2, best_of=3):
    """
    Simulate a best-of-3 match.
    
    Each player dictionary should have these keys:
      - name
      - base_stats (their long-term baseline stats)
      - daily_stats (set at match start via generate_daily_stats)
      - momentum (starting at 0)
      - breaks (ephemeral, used for extra stat tracking)
    
    Returns two dictionaries with final match tallies for player1 and player2.
    """
    # Initialize match stats for each player.
    p1_stats = {
        'sets_won': 0,
        'games_won': 0,
        'aces': 0,
        'double_faults': 0,
        'breaks': 0,
        'clean_sets': 0,
    }
    p2_stats = {
        'sets_won': 0,
        'games_won': 0,
        'aces': 0,
        'double_faults': 0,
        'breaks': 0,
        'clean_sets': 0,
    }
    
    # Each match, players start with momentum = 0.
    player1['momentum'] = 0
    player2['momentum'] = 0
    
    # Generate today's stats for each player.
    player1['daily_stats'] = generate_daily_stats(player1['base_stats'])
    player2['daily_stats'] = generate_daily_stats(player2['base_stats'])
    
    # Determine how many sets to win.
    sets_to_win = best_of // 2 + 1
    next_set_server = 1  # alternate set starting server.
    
    while p1_stats['sets_won'] < sets_to_win and p2_stats['sets_won'] < sets_to_win:
        set_result = simulate_set(player1, player2, next_set_server)
        # Update game, aces, and DF counts.
        p1_stats['games_won'] += set_result['games_won_by_p1']
        p2_stats['games_won'] += set_result['games_won_by_p2']
        p1_stats['aces'] += set_result['aces_by_p1']
        p2_stats['aces'] += set_result['aces_by_p2']
        p1_stats['double_faults'] += set_result['df_by_p1']
        p2_stats['double_faults'] += set_result['df_by_p2']
        
        if set_result['winner'] == player1:
            p1_stats['sets_won'] += 1
            # (Clean set bonus logic could be added here.)
        else:
            p2_stats['sets_won'] += 1
        
        next_set_server = 1 if next_set_server == 2 else 2
    
    # Determine match winner.
    if p1_stats['sets_won'] > p2_stats['sets_won']:
        p1_stats['match_won'] = True
        p2_stats['match_won'] = False
    else:
        p2_stats['match_won'] = True
        p1_stats['match_won'] = False
    
    # For simplicity, we set sets_lost and games_lost.
    p1_stats['sets_lost'] = p2_stats['sets_won']
    p2_stats['sets_lost'] = p1_stats['sets_won']
    p1_stats['games_lost'] = p2_stats['games_won']
    p2_stats['games_lost'] = p1_stats['games_won']
    
    return p1_stats, p2_stats

def calculate_draftkings_score(stats, best_of=3):
    """
    Calculates the DraftKings fantasy score for a player given their match stats,
    assuming best-of-3 scoring.
    """
    # Scoring rules for best-of-3.
    match_played_pts = 30
    game_won_pts = 2.5
    game_lost_pts = -2
    set_won_pts = 6
    set_lost_pts = -3
    match_won_pts = 6
    ace_pts = 0.4
    df_pts = -1
    break_pts = 0.75

    # Bonuses
    clean_set_bonus = 4
    straight_sets_bonus = 6
    no_df_bonus = 2.5
    milestone_10_aces = 2

    sets_won = stats['sets_won']
    sets_lost = stats['sets_lost']
    games_won = stats['games_won']
    games_lost = stats['games_lost']
    aces = stats['aces']
    double_faults = stats['double_faults']
    # For simplicity, breaks are not separately tallied here.
    match_won = stats['match_won']
    clean_sets = stats['clean_sets']

    points = 0
    points += match_played_pts
    points += games_won * game_won_pts
    points += games_lost * game_lost_pts
    points += sets_won * set_won_pts
    points += sets_lost * set_lost_pts
    if match_won:
        points += match_won_pts
    points += aces * ace_pts
    points += double_faults * df_pts
    points += break_pts * 0  # (Breaks bonus could be added if tracked.)
    points += clean_sets * clean_set_bonus
    if match_won and sets_lost == 0:
        points += straight_sets_bonus
    if double_faults == 0:
        points += no_df_bonus
    if aces >= 10:
        points += milestone_10_aces

    return points

# -------------------------------
# Main simulation loop
# -------------------------------
if __name__ == "__main__":
    # Base stats for each player (as provided).
    sinner_base_stats = {
        'DecSetWinPercentage': 0.68421,
        'TieBreaksWonPercentage': 0.75758,
        'ServiceGamesWonPercentage': 0.91468,
        'ReturnGamesWonPercentage': 0.2831,
        'FirstServePercentage': 0.61591,
        'FirstServeWonPercentage': 0.79339,
        'SecondServeWonPercentage': 0.57838,
        'ServicePointsWonPercentage': 0.71081,
        'AcePercentage': 0.09907,
        'AcesPerServiceGame': 0.58929,
        'DoubleFaultPercentage': 0.02402,
        'DoubleFaultsPerServiceGame': 0.14286,
        'AcesPerDoubleFault': 4.125,
        'BreakPointsFacedPerServiceGame': 0.32341,
        'BreakPointsSavedPercentage': 0.7362,
        'FirstServeReturnPointsWonPercentage': 0.31892,
        'SecondServeReturnPointsWonPercentage': 0.55853,
        'ReturnPointsWonPercentage': 0.40875,
        'AceAgainstPercentage': 0.07516,
        'AcesAgainstPerReturnGame': 0.50407,
        'BreakPointChancesPerReturnGame': 0.67006,
        'BreakPointsConvertedPercentage': 0.42249
    }

    alcaraz_base_stats = {
        'DecSetWinPercentage': 0.7,
        'TieBreaksWonPercentage': 0.58065,
        'ServiceGamesWonPercentage': 0.867,
        'ReturnGamesWonPercentage': 0.30893,
        'FirstServePercentage': 0.65509,
        'FirstServeWonPercentage': 0.73643,
        'SecondServeWonPercentage': 0.57715,
        'ServicePointsWonPercentage': 0.6815,
        'AcePercentage': 0.06256,
        'AcesPerServiceGame': 0.37931,
        'DoubleFaultPercentage': 0.02641,
        'DoubleFaultsPerServiceGame': 0.1601,
        'AcesPerDoubleFault': 2.36923,
        'BreakPointsFacedPerServiceGame': 0.37438,
        'BreakPointsSavedPercentage': 0.64474,
        'FirstServeReturnPointsWonPercentage': 0.34418,
        'SecondServeReturnPointsWonPercentage': 0.54378,
        'ReturnPointsWonPercentage': 0.41604,
        'AceAgainstPercentage': 0.05088,
        'AcesAgainstPerReturnGame': 0.34243,
        'BreakPointChancesPerReturnGame': 0.73573,
        'BreakPointsConvertedPercentage': 0.4199
    }

    # Set up player dictionaries. Each player starts with their base stats.
    N = 100  # Number of simulations
    sinner_dk_sum = 0.0
    alcaraz_dk_sum = 0.0

    for _ in range(N):
        # Create fresh player dictionaries (ephemeral properties are reset each match).
        player1 = {
            'name': 'Jannik Sinner',
            'base_stats': sinner_base_stats,
            'momentum': 0,   # will be set in simulate_match
            'daily_stats': {},  # will be generated at match start
            'breaks': 0
        }
        player2 = {
            'name': 'Carlos Alcaraz',
            'base_stats': alcaraz_base_stats,
            'momentum': 0,
            'daily_stats': {},
            'breaks': 0
        }
        
        p1_res, p2_res = simulate_match(player1, player2, best_of=3)
        p1_dk = calculate_draftkings_score(p1_res, best_of=3)
        p2_dk = calculate_draftkings_score(p2_res, best_of=3)
        sinner_dk_sum += p1_dk
        alcaraz_dk_sum += p2_dk

    print(f"After {N} best-of-3 simulations with daily variance and momentum:")
    print(f"Average DK Score for Jannik Sinner: {sinner_dk_sum / N:.2f}")
    print(f"Average DK Score for Carlos Alcaraz: {alcaraz_dk_sum / N:.2f}")
