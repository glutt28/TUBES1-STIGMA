from typing import Dict, List, Optional, Tuple
from game import models
from .nazarick_config import BotConfig
from . import nazarick_datafunction as ndf
from game.util import position_equals
from dataclasses import dataclass


@dataclass
class UtilityScore:
    total: float
    distance_penalty: float
    reward_value: float
    risk_penalty: float
    urgency_bonus: float
    target_type: str
    immediate_target_pos: models.Position


def calculate_utility(
    immediate_target_pos: models.Position,
    final_target_type: str,
    final_target_obj: Optional[models.GameObject],
    full_path_distance: int,
    board_bot: models.GameObject,
    board: models.Board,
    weights: Dict[str, float],
    committed_target_info: Optional[UtilityScore],
    is_via_teleporter: bool = False,
) -> UtilityScore:
    current_pos = board_bot.position
    properties = board_bot.properties

    distance_penalty = weights["distance"] * full_path_distance
    if is_via_teleporter:
        distance_penalty += weights["teleporter_usage_cost"]

    diamonds_carried = properties.diamonds if properties.diamonds is not None else 0
    inventory_size = (
        properties.inventory_size
        if properties.inventory_size is not None
        else BotConfig.MAX_INVENTORY_DEFAULT
    )
    can_tackle = properties.can_tackle if properties.can_tackle is not None else False

    reward_value = 0.0
    risk_penalty = 0.0
    urgency_bonus = 0.0

    if final_target_type == "base":
        if diamonds_carried > 0:
            reward_value = weights["base_return"] * (diamonds_carried**1.5)
            if inventory_size > 0:
                inventory_ratio = diamonds_carried / inventory_size
                urgency_bonus = weights["inventory_urgency"] * inventory_ratio * 10
        else:
            reward_value = -5.0

    elif final_target_type == "diamond" and final_target_obj:
        if diamonds_carried >= inventory_size:
            reward_value = -100.0
        else:
            diamond_points = (
                final_target_obj.properties.points
                if final_target_obj.properties
                and final_target_obj.properties.points is not None
                else 1
            )
            reward_value = weights["diamond_value"] * diamond_points
            if inventory_size > 0:
                space_ratio = (inventory_size - diamonds_carried) / inventory_size
                urgency_bonus = (
                    space_ratio
                    * 3.0
                    * (diamond_points / 5.0 if diamond_points > 0 else 0.1)
                )

    elif final_target_type == "enemy" and final_target_obj:
        enemy_props = final_target_obj.properties
        if enemy_props:
            enemy_diamonds = (
                enemy_props.diamonds if enemy_props.diamonds is not None else 0
            )
            if can_tackle and enemy_diamonds > 0:
                reward_value = weights["tackle_opportunity"] * enemy_diamonds
                if (
                    inventory_size > 0
                    and diamonds_carried + enemy_diamonds <= inventory_size
                ):
                    urgency_bonus = 5.0
            elif not can_tackle and enemy_diamonds > 0:
                reward_value = -1.0
            else:
                reward_value = -15.0

    elif final_target_type == "diamond_button" and final_target_obj:
        num_diamonds_on_board = len(board.diamonds) if board.diamonds else 0
        beneficial_to_reset = (
            num_diamonds_on_board < BotConfig.LOW_DIAMOND_COUNT_THRESHOLD
        )

        if beneficial_to_reset:
            reward_value = weights["reset_button_base_reward"]
            if num_diamonds_on_board == 0:
                urgency_bonus = weights["reset_button_urgency_factor"] * 3
            elif num_diamonds_on_board < 2:
                urgency_bonus = weights["reset_button_urgency_factor"] * 1.5
            else:
                urgency_bonus = weights["reset_button_urgency_factor"] * (
                    (BotConfig.LOW_DIAMOND_COUNT_THRESHOLD - num_diamonds_on_board)
                    / float(BotConfig.LOW_DIAMOND_COUNT_THRESHOLD)
                )
        else:
            reward_value = weights["reset_penalty_diamonds_ok"]

        if (
            properties.milliseconds_left
            and properties.milliseconds_left < BotConfig.MIN_TIME_FOR_RESET_BENEFIT_MS
        ):
            reward_value += weights["reset_penalty_time_low"]

    enemies_on_board = (
        [
            bot
            for bot in board.bots
            if bot.properties and properties.name != bot.properties.name
        ]
        if board.bots
        else []
    )

    for enemy_obj in enemies_on_board:
        if not enemy_obj.properties:
            continue
        enemy_distance_to_immediate_target = ndf.howManyStepNeeded(
            immediate_target_pos, enemy_obj.position
        )
        if enemy_distance_to_immediate_target <= BotConfig.ENEMY_DANGER_RADIUS:
            if (
                enemy_obj.properties.can_tackle
                if enemy_obj.properties.can_tackle is not None
                else False
            ):
                risk_multiplier = 1 + (diamonds_carried * 0.5)
                risk_penalty += (
                    weights["enemy_risk"]
                    * (
                        (BotConfig.ENEMY_DANGER_RADIUS + 1)
                        - enemy_distance_to_immediate_target
                    )
                    * risk_multiplier
                )

    if final_target_type != "base" and final_target_type != "diamond_button":
        if diamonds_carried >= inventory_size:
            reward_value = -100.0
            urgency_bonus = 0.0
        elif (
            diamonds_carried
            >= inventory_size * BotConfig.CONSIDER_TP_PATH_URGENT_BASE_INVENTORY_RATIO
        ):
            reward_value *= 0.2
            urgency_bonus *= 0.2

    total_utility = reward_value + distance_penalty + risk_penalty + urgency_bonus

    if (
        committed_target_info
        and position_equals(
            immediate_target_pos, committed_target_info.immediate_target_pos
        )
        and final_target_type == committed_target_info.target_type
    ):
        total_utility += weights["commitment_bonus"]

    return UtilityScore(
        total=total_utility,
        distance_penalty=distance_penalty,
        reward_value=reward_value,
        risk_penalty=risk_penalty,
        urgency_bonus=urgency_bonus,
        target_type=final_target_type,
        immediate_target_pos=immediate_target_pos,
    )
