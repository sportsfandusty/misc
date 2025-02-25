# optimizer.py

import pandas as pd
import random
import logging
import sys
from pulp import (
    LpProblem,
    LpMaximize,
    LpVariable,
    lpSum,
    LpStatus,
    PULP_CBC_CMD,
)
from collections import defaultdict

# Include the get_logger function and necessary settings
DEBUG = True

LOG_FILE = "nfl_app.log"
LOG_LEVEL = logging.DEBUG if DEBUG else logging.INFO

def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    # Avoid adding multiple handlers if the logger already has them
    if not logger.handlers:
        file_handler = logging.FileHandler(LOG_FILE)
        file_handler.setLevel(LOG_LEVEL)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(LOG_LEVEL)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger

logger = get_logger(__name__)

def optimize_lineups(optimizer_config, progress_bar=None, status_text=None):
    """
    Generates optimized lineups based on provided configurations.

    Parameters:
        optimizer_config (dict): Configuration parameters for optimization.
        progress_bar (object): Streamlit progress bar object (optional).
        status_text (object): Streamlit status text object (optional).

    Returns:
        list: A list of optimized lineups.
    """
    logger.debug("Starting optimize_lineups function.")
    df_showdown = optimizer_config["df"].copy()
    logger.debug(f"Initial df_showdown shape: {df_showdown.shape}")

    # Extract optimization parameters
    num_lineups = optimizer_config["num_lineups"]
    salary_cap = optimizer_config["salary_cap"]
    projection_column = optimizer_config["projection_column"]
    player_correlations = optimizer_config.get("player_correlations", {})
    apply_variance_flag = optimizer_config.get("apply_variance", False)
    mode = optimizer_config.get("mode", "optimal").lower()
    COLUMN_CONFIG = optimizer_config["COLUMN_CONFIG"]
    min_unique_players = optimizer_config.get("min_unique_players", 1)

    logger.debug(f"Number of lineups to generate: {num_lineups}")
    logger.debug(f"Salary cap: {salary_cap}")
    logger.debug(f"Projection column: {projection_column}")
    logger.debug(f"Apply variance flag: {apply_variance_flag}")
    logger.debug(f"Mode: {mode.capitalize()}")
    logger.debug(f"Minimum unique players between lineups: {min_unique_players}")

    # Reset index to ensure alignment
    df_showdown.reset_index(drop=True, inplace=True)
    logger.debug("Reset index of df_showdown.")

    # Ensure required columns exist
    required_columns = [
        'player_id',
        COLUMN_CONFIG['role'],
        COLUMN_CONFIG['name'],
        COLUMN_CONFIG['position'],
        COLUMN_CONFIG['salary'],
        projection_column,
        COLUMN_CONFIG['team'],
    ]
    missing_columns = [col for col in required_columns if col not in df_showdown.columns]
    if missing_columns:
        logger.error(f"Missing required columns in df_showdown: {missing_columns}")
        sys.exit(f"Error: Missing required columns in data: {missing_columns}")

    # Create 'player_id' by combining 'name' and 'role' if not already present
    if 'player_id' not in df_showdown.columns:
        df_showdown["player_id"] = df_showdown[COLUMN_CONFIG['name']].astype(str) + "|" + df_showdown[COLUMN_CONFIG['role']]
        logger.debug("Created 'player_id' column.")

    roster_size = 6
    logger.debug(f"Roster size set to: {roster_size}")

    lineups = []
    solver = PULP_CBC_CMD(msg=False)

    for i in range(num_lineups):
        logger.debug(f"Generating lineup {i + 1}/{num_lineups}.")

        # Update progress bar
        if progress_bar is not None:
            progress = (i + 1) / num_lineups
            progress_bar.progress(progress)

        # Update status text
        if status_text is not None:
            status_text.text(f"Generating lineup {i + 1}/{num_lineups}")

        if apply_variance_flag:
            logger.debug("Applying variance to projections.")
            df_current = apply_variance_to_projections(df_showdown, player_correlations, projection_column, COLUMN_CONFIG)
        else:
            df_current = df_showdown.copy()
            logger.debug("Not applying variance to projections.")

        df_current = df_current.reset_index(drop=True)

        players = df_current["player_id"].tolist()
        logger.debug(f"Number of players: {len(players)}")

        # Create decision variables
        positions_vars = {player: LpVariable(f"{player}_pos_{i}", cat="Binary") for player in players}
        logger.debug("Created decision variables for players.")

        # Initialize optimization problem
        problem = LpProblem(f"Showdown_Lineup_{i+1}", LpMaximize)
        logger.debug(f"Initialized optimization problem for lineup {i + 1}.")

        # Objective: Maximize total projections
        problem += lpSum(
            df_current.loc[j, projection_column] * positions_vars[players[j]] for j in range(len(players))
        ), "Total_Projected_Points"
        logger.debug("Set objective to maximize total projected points.")

        # Constraint: Salary cap
        problem += (
            lpSum(
                df_current.loc[j, COLUMN_CONFIG['salary']] * positions_vars[players[j]] for j in range(len(players))
            ) <= salary_cap,
            "Salary_Cap"
        )
        logger.debug("Added salary cap constraint.")

        # Constraint: Roster size
        problem += (
            lpSum(positions_vars[player] for player in players) == roster_size,
            "Roster_Size"
        )
        logger.debug("Added roster size constraint.")

        # Constraint: Exactly one Captain
        problem += (
            lpSum(positions_vars[player] for player in players if player.endswith("|Captain")) == 1,
            "One_Captain"
        )
        logger.debug("Added Captain role constraint.")

        # Constraint: Exactly five Flex players
        problem += (
            lpSum(positions_vars[player] for player in players if player.endswith("|Flex")) == 5,
            "Five_Flex"
        )
        logger.debug("Added Flex role constraint.")

        # Constraint: Unique players (no duplicate players in lineup)
        for name in df_current[COLUMN_CONFIG['name']].unique():
            player_variants = [player for player in players if player.startswith(name + "|")]
            problem += (
                lpSum(positions_vars[player] for player in player_variants) <= 1,
                f"Unique_Player_{name}"
            )
            logger.debug(f"Added unique player constraint for {name}.")

        # Constraint: Minimum unique players between lineups
        for j, existing_lineup in enumerate(lineups):
            overlap = lpSum(positions_vars[player] for player in existing_lineup)
            problem += (
                overlap <= roster_size - min_unique_players,
                f"Min_Unique_Players_Constraint_{i+1}_{j+1}"
            )
            logger.debug(f"Added minimum unique players constraint between lineup {i + 1} and lineup {j + 1}.")

        # Solve the optimization problem
        logger.debug(f"Solving optimization problem for lineup {i + 1}.")
        problem.solve(solver)
        logger.debug(f"Optimization Status: {LpStatus[problem.status]}")

        if LpStatus[problem.status] == "Optimal":
            selected_lineup = [player for player in players if positions_vars[player].varValue == 1]
            logger.debug(f"Selected lineup {i + 1}: {selected_lineup}")
            lineups.append(selected_lineup)
            logger.debug(f"Lineup {i + 1} generated successfully.")
        else:
            logger.warning(f"No optimal solution found for lineup {i + 1}.")
            break

    logger.debug("Completed optimize_lineups function.")
    return lineups

def apply_variance_to_projections(df_showdown, player_correlations, projection_column, COLUMN_CONFIG):
    """
    Applies variance to player projections, considering negative correlations
    between offensive players and opposing defenses.

    Parameters:
        df_showdown (pd.DataFrame): DataFrame containing player projections.
        player_correlations (dict): Unused in this context.
        projection_column (str): The projection column to adjust.
        COLUMN_CONFIG (dict): Dictionary containing column configurations.

    Returns:
        pd.DataFrame: DataFrame with adjusted projections.
    """
    logger.debug("Starting apply_variance_to_projections function.")

    df_variance = df_showdown.copy()
    adjusted_players = set()
    team_variance_factors = {}  # Store variance factors for each team
    defense_positions = ['DST', 'Defense', 'D', 'D/ST']  # Adjust based on your data

    # Map team to opponent
    team_opponent_map = dict(zip(df_variance[COLUMN_CONFIG['team']], df_variance[COLUMN_CONFIG['opponent']]))

    for idx, row in df_showdown.iterrows():
        player_name = row[COLUMN_CONFIG['name']]
        position = row[COLUMN_CONFIG['position']]
        team = row[COLUMN_CONFIG['team']]
        opponent = row[COLUMN_CONFIG['opponent']]

        if player_name in adjusted_players:
            continue

        is_defense = position in defense_positions

        if not is_defense:
            # Offensive player
            if team not in team_variance_factors:
                variance_factor = random.uniform(0.9, 1.1)
                team_variance_factors[team] = variance_factor
            else:
                variance_factor = team_variance_factors[team]

            adjusted_players.add(player_name)

            # Apply variance to offensive player
            for role_variant in ['Flex', 'Captain']:
                player_id_variant = f"{player_name}|{role_variant}"
                df_variance.loc[df_variance['player_id'] == player_id_variant, projection_column] *= variance_factor

            # Apply inverse variance to opposing defense
            inverse_variance_factor = 2 - variance_factor  # Inverse of variance_factor
            opponent_defense = df_variance[
                (df_variance[COLUMN_CONFIG['team']] == opponent) &
                (df_variance[COLUMN_CONFIG['position']].isin(defense_positions))
            ]

            for idx_def, def_row in opponent_defense.iterrows():
                def_player_name = def_row[COLUMN_CONFIG['name']]
                if def_player_name in adjusted_players:
                    continue
                adjusted_players.add(def_player_name)
                for role_variant in ['Flex', 'Captain']:
                    def_player_id_variant = f"{def_player_name}|{role_variant}"
                    df_variance.loc[df_variance['player_id'] == def_player_id_variant, projection_column] *= inverse_variance_factor

        else:
            # Defensive player
            if team not in team_variance_factors:
                # If variance factor not set for defense team, set it now
                variance_factor = random.uniform(0.9, 1.1)
                team_variance_factors[team] = variance_factor
            else:
                variance_factor = team_variance_factors[team]

            adjusted_players.add(player_name)

            # Apply variance to defense player
            for role_variant in ['Flex', 'Captain']:
                player_id_variant = f"{player_name}|{role_variant}"
                df_variance.loc[df_variance['player_id'] == player_id_variant, projection_column] *= variance_factor

            # Apply inverse variance to opposing offensive players
            inverse_variance_factor = 2 - variance_factor
            opponent_offense = df_variance[
                (df_variance[COLUMN_CONFIG['team']] == opponent) &
                (~df_variance[COLUMN_CONFIG['position']].isin(defense_positions))
            ]

            for idx_off, off_row in opponent_offense.iterrows():
                off_player_name = off_row[COLUMN_CONFIG['name']]
                if off_player_name in adjusted_players:
                    continue
                adjusted_players.add(off_player_name)
                for role_variant in ['Flex', 'Captain']:
                    off_player_id_variant = f"{off_player_name}|{role_variant}"
                    df_variance.loc[df_variance['player_id'] == off_player_id_variant, projection_column] *= inverse_variance_factor

    logger.debug("Completed apply_variance_to_projections function.")
    return df_variance

    logger.debug("Completed apply_variance_to_projections function.")
    return df_variance

