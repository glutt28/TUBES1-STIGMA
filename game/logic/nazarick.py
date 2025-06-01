from game.logic.base import BaseLogic
from game import models
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
import random

from game.logic.NazarickSublogic import nazarick_datafunction as ndf


@dataclass
class UtilityScore:
    total: float
    distance_penalty: float
    reward_value: float
    risk_penalty: float
    urgency_bonus: float
    target_type: str
    immediate_target_pos: models.Position


class NazarickNPC(BaseLogic):
    def __init__(self):
        self.weights = {
            "distance": -1.0,
            "diamond_value": 10.0,
            "enemy_risk": -20.0,
            "base_return": 15.0,
            "tackle_opportunity": 25.0,
            "inventory_urgency": 5.0,
            "teleporter_usage_cost": -0.5,
            "reset_button_base_reward": 20.0,
            "reset_button_urgency_factor": 10.0,
            "reset_penalty_time_low": -50.0,
            "reset_penalty_diamonds_ok": -30.0,
        }
        self.last_position: Optional[models.Position] = None
        self.stuck_counter: int = 0

    def calculate_utility(
        self,
        immediate_target_pos: models.Position,
        final_target_type: str,
        final_target_obj: Optional[models.GameObject],
        full_path_distance: int,
        board_bot: models.GameObject,
        board: models.Board,
        is_via_teleporter: bool = False,
    ) -> UtilityScore:
        current_pos = board_bot.position
        properties = board_bot.properties

        distance_penalty = self.weights["distance"] * full_path_distance
        if is_via_teleporter:
            distance_penalty += self.weights["teleporter_usage_cost"]

        diamonds_carried = properties.diamonds if properties.diamonds is not None else 0
        inventory_size = (
            properties.inventory_size if properties.inventory_size is not None else 5
        )
        can_tackle = (
            properties.can_tackle if properties.can_tackle is not None else False
        )

        reward_value = 0.0
        risk_penalty = 0.0
        urgency_bonus = 0.0

        if final_target_type == "base":
            if diamonds_carried > 0:
                reward_value = self.weights["base_return"] * (diamonds_carried**1.5)
                inventory_ratio = diamonds_carried / inventory_size
                urgency_bonus = self.weights["inventory_urgency"] * inventory_ratio * 10
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
                reward_value = self.weights["diamond_value"] * diamond_points
                space_ratio = (inventory_size - diamonds_carried) / inventory_size
                urgency_bonus = space_ratio * 3.0 * (diamond_points / 5.0)

        elif final_target_type == "enemy" and final_target_obj:
            enemy_props = final_target_obj.properties
            if enemy_props:
                enemy_diamonds = (
                    enemy_props.diamonds if enemy_props.diamonds is not None else 0
                )
                if can_tackle and enemy_diamonds > 0:
                    reward_value = self.weights["tackle_opportunity"] * enemy_diamonds
                    if diamonds_carried + enemy_diamonds <= inventory_size:
                        urgency_bonus = 5.0
                elif not can_tackle and enemy_diamonds > 0:
                    reward_value = -1.0
                else:
                    reward_value = -15.0

        elif final_target_type == "diamond_button" and final_target_obj:
            num_diamonds_on_board = len(board.diamonds)
            beneficial_to_reset = num_diamonds_on_board < 4

            if beneficial_to_reset:
                reward_value = self.weights["reset_button_base_reward"]
                if num_diamonds_on_board == 0:
                    urgency_bonus = self.weights["reset_button_urgency_factor"] * 3
                elif num_diamonds_on_board < 2:
                    urgency_bonus = self.weights["reset_button_urgency_factor"] * 1.5
                else:
                    urgency_bonus = self.weights["reset_button_urgency_factor"] * (
                        (4 - num_diamonds_on_board) / 4.0
                    )
            else:
                reward_value = self.weights["reset_penalty_diamonds_ok"]

            if properties.milliseconds_left and properties.milliseconds_left < 25000:
                reward_value += self.weights["reset_penalty_time_low"]

        enemies_on_board = [
            bot
            for bot in board.bots
            if bot.properties and properties.name != bot.properties.name
        ]
        for enemy_obj in enemies_on_board:
            if not enemy_obj.properties:
                continue
            enemy_distance_to_immediate_target = ndf.howManyStepNeeded(
                immediate_target_pos, enemy_obj.position
            )
            if enemy_distance_to_immediate_target <= 2:
                if (
                    enemy_obj.properties.can_tackle
                    if enemy_obj.properties.can_tackle is not None
                    else False
                ):
                    risk_multiplier = 1 + (diamonds_carried * 0.5)
                    risk_penalty += (
                        self.weights["enemy_risk"]
                        * (3 - enemy_distance_to_immediate_target)
                        * risk_multiplier
                    )

        if final_target_type != "base" and final_target_type != "diamond_button":
            if diamonds_carried >= inventory_size:
                reward_value = -100.0
                urgency_bonus = 0.0
            elif diamonds_carried >= inventory_size * 0.7:
                reward_value *= 0.2
                urgency_bonus *= 0.2

        total_utility = reward_value + distance_penalty + risk_penalty + urgency_bonus

        return UtilityScore(
            total=total_utility,
            distance_penalty=distance_penalty,
            reward_value=reward_value,
            risk_penalty=risk_penalty,
            urgency_bonus=urgency_bonus,
            target_type=final_target_type,
            immediate_target_pos=immediate_target_pos,
        )

    def get_smart_move(
        self, current: models.Position, target: models.Position, board: models.Board
    ) -> Tuple[int, int]:
        dx_target = target.x - current.x
        dy_target = target.y - current.y
        preferred_moves: List[Tuple[int, int]] = []
        if abs(dx_target) >= abs(dy_target):
            if dx_target > 0:
                preferred_moves.append((1, 0))
            elif dx_target < 0:
                preferred_moves.append((-1, 0))
            if dy_target > 0:
                preferred_moves.append((0, 1))
            elif dy_target < 0:
                preferred_moves.append((0, -1))
        else:
            if dy_target > 0:
                preferred_moves.append((0, 1))
            elif dy_target < 0:
                preferred_moves.append((0, -1))
            if dx_target > 0:
                preferred_moves.append((1, 0))
            elif dx_target < 0:
                preferred_moves.append((-1, 0))
        all_possible_cardinal_moves = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        for move in all_possible_cardinal_moves:
            if move not in preferred_moves:
                preferred_moves.append(move)
        for move_dx, move_dy in preferred_moves:
            if board.is_valid_move(current, move_dx, move_dy):
                return (move_dx, move_dy)
        return (0, 0)

    def is_stuck(self, current_position: models.Position) -> bool:
        if (
            self.last_position
            and self.last_position.x == current_position.x
            and self.last_position.y == current_position.y
        ):
            self.stuck_counter += 1
        else:
            self.stuck_counter = 0
        self.last_position = models.Position(x=current_position.x, y=current_position.y)
        return self.stuck_counter >= 3

    def next_move(
        self, board_bot: models.GameObject, board: models.Board
    ) -> Tuple[int, int]:
        current_pos = board_bot.position
        properties = board_bot.properties

        if not properties or not properties.base:
            return (0, 0)

        diamonds_carried = properties.diamonds if properties.diamonds is not None else 0
        inventory_size = (
            properties.inventory_size if properties.inventory_size is not None else 5
        )

        if self.is_stuck(current_pos):
            possible_moves = [(1, 0), (0, 1), (-1, 0), (0, -1)]
            random.shuffle(possible_moves)
            for dx_rand, dy_rand in possible_moves:
                if board.is_valid_move(current_pos, dx_rand, dy_rand):
                    return (dx_rand, dy_rand)
            return (0, 0)

        final_target_candidates: List[Tuple[models.GameObject, str]] = []
        base_game_obj = models.GameObject(
            id=-1, position=properties.base, type="BaseGameObject", properties=None
        )
        final_target_candidates.append((base_game_obj, "base"))

        if diamonds_carried < inventory_size:
            for diamond_obj in board.diamonds:
                final_target_candidates.append((diamond_obj, "diamond"))

        all_game_objects = board.game_objects if board.game_objects else []
        diamond_button_objects: List[models.GameObject] = [
            obj for obj in all_game_objects if obj.type == "DiamondButtonGameObject"
        ]
        diamond_button: Optional[models.GameObject] = (
            diamond_button_objects[0] if diamond_button_objects else None
        )

        if diamond_button:
            final_target_candidates.append((diamond_button, "diamond_button"))

        if properties.can_tackle if properties.can_tackle is not None else False:
            for enemy_obj in board.bots:
                if (
                    enemy_obj.properties
                    and properties.name != enemy_obj.properties.name
                ):
                    enemy_diamonds = (
                        enemy_obj.properties.diamonds
                        if enemy_obj.properties.diamonds is not None
                        else 0
                    )
                    if enemy_diamonds > 0:
                        final_target_candidates.append((enemy_obj, "enemy"))

        if not final_target_candidates:
            return (0, 0)

        all_teleporter_objects = [
            obj for obj in all_game_objects if obj.type == "TeleportGameObject"
        ]
        entry_tp_obj, exit_tp_obj, dist_to_entry_tp = (
            ndf.determineTargetAndExitTeleporters(all_teleporter_objects, current_pos)
        )
        best_utility_score: Optional[UtilityScore] = None
        evaluated_paths_for_final_target: Set[Tuple[int, int, str]] = set()

        for final_target_obj, final_target_type in final_target_candidates:
            final_target_pos = final_target_obj.position

            if final_target_type == "diamond_button":
                dist_to_button = ndf.howManyStepNeeded(current_pos, final_target_pos)
                utility_button = self.calculate_utility(
                    final_target_pos,
                    final_target_type,
                    final_target_obj,
                    dist_to_button,
                    board_bot,
                    board,
                    is_via_teleporter=False,
                )
                if (
                    best_utility_score is None
                    or utility_button.total > best_utility_score.total
                ):
                    best_utility_score = utility_button
            else:
                path_key_direct = (
                    final_target_pos.x,
                    final_target_pos.y,
                    "direct_to_" + final_target_type,
                )
                if path_key_direct not in evaluated_paths_for_final_target:
                    dist_direct = ndf.howManyStepNeeded(current_pos, final_target_pos)
                    utility_direct = self.calculate_utility(
                        final_target_pos,
                        final_target_type,
                        final_target_obj,
                        dist_direct,
                        board_bot,
                        board,
                        is_via_teleporter=False,
                    )
                    if (
                        best_utility_score is None
                        or utility_direct.total > best_utility_score.total
                    ):
                        best_utility_score = utility_direct
                    evaluated_paths_for_final_target.add(path_key_direct)

                if entry_tp_obj and exit_tp_obj and final_target_type != "enemy":
                    path_key_teleporter = (
                        final_target_pos.x,
                        final_target_pos.y,
                        "tp_to_" + final_target_type,
                    )
                    if path_key_teleporter not in evaluated_paths_for_final_target:
                        dist_exit_to_final_target = ndf.howManyStepNeeded(
                            exit_tp_obj.position, final_target_pos
                        )
                        full_dist_via_tp = (
                            dist_to_entry_tp + 1 + dist_exit_to_final_target
                        )

                        dist_direct_temp = ndf.howManyStepNeeded(
                            current_pos, final_target_pos
                        )
                        consider_tp_path = (
                            full_dist_via_tp < dist_direct_temp * 1.2
                        ) or (
                            final_target_type == "base"
                            and diamonds_carried >= inventory_size * 0.8
                        )

                        if consider_tp_path:
                            utility_via_tp = self.calculate_utility(
                                entry_tp_obj.position,
                                final_target_type,
                                final_target_obj,
                                full_dist_via_tp,
                                board_bot,
                                board,
                                is_via_teleporter=True,
                            )
                            if (
                                best_utility_score is None
                                or utility_via_tp.total > best_utility_score.total
                            ):
                                best_utility_score = utility_via_tp
                            evaluated_paths_for_final_target.add(path_key_teleporter)

        if not best_utility_score:
            return (0, 0)

        best_immediate_target_pos = best_utility_score.immediate_target_pos
        move_dx, move_dy = self.get_smart_move(
            current_pos, best_immediate_target_pos, board
        )

        return move_dx, move_dy
