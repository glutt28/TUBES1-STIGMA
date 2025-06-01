from typing import Dict, List, Optional, Tuple, Set
from game import models
from . import nazarick_datafunction as ndf
from .nazarick_config import BotConfig
from .nazarick_calculations import calculate_utility, UtilityScore
from game.util import position_equals


def find_best_actionable_target(
    board_bot: models.GameObject,
    board: models.Board,
    weights: Dict[str, float],
    committed_target_info: Optional[UtilityScore],
) -> Optional[UtilityScore]:
    current_pos = board_bot.position
    properties = board_bot.properties

    diamonds_carried = properties.diamonds if properties.diamonds is not None else 0
    inventory_size = (
        properties.inventory_size
        if properties.inventory_size is not None
        else BotConfig.MAX_INVENTORY_DEFAULT
    )

    final_target_candidates: List[Tuple[models.GameObject, str]] = []
    base_game_obj = models.GameObject(
        id=-1, position=properties.base, type="BaseGameObject", properties=None
    )
    final_target_candidates.append((base_game_obj, "base"))

    if diamonds_carried < inventory_size:
        if board.diamonds:
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
        if board.bots:
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
        return None

    all_teleporter_objects = [
        obj for obj in all_game_objects if obj.type == "TeleportGameObject"
    ]
    entry_tp_obj, exit_tp_obj, dist_to_entry_tp = ndf.determineTargetAndExitTeleporters(
        all_teleporter_objects, current_pos
    )
    best_utility_score: Optional[UtilityScore] = None

    for final_target_obj, final_target_type in final_target_candidates:
        final_target_pos = final_target_obj.position

        if final_target_type == "diamond_button":
            dist_to_button = ndf.howManyStepNeeded(current_pos, final_target_pos)
            utility_button = calculate_utility(
                final_target_pos,
                final_target_type,
                final_target_obj,
                dist_to_button,
                board_bot,
                board,
                weights,
                committed_target_info,
                False,
            )
            if (
                best_utility_score is None
                or utility_button.total > best_utility_score.total
            ):
                best_utility_score = utility_button
        else:
            dist_direct = ndf.howManyStepNeeded(current_pos, final_target_pos)
            utility_direct = calculate_utility(
                final_target_pos,
                final_target_type,
                final_target_obj,
                dist_direct,
                board_bot,
                board,
                weights,
                committed_target_info,
                False,
            )
            if (
                best_utility_score is None
                or utility_direct.total > best_utility_score.total
            ):
                best_utility_score = utility_direct

            if entry_tp_obj and exit_tp_obj and final_target_type != "enemy":
                dist_exit_to_final_target = ndf.howManyStepNeeded(
                    exit_tp_obj.position, final_target_pos
                )
                full_dist_via_tp = dist_to_entry_tp + 1 + dist_exit_to_final_target
                consider_tp_path = (
                    full_dist_via_tp
                    < dist_direct * BotConfig.CONSIDER_TP_PATH_DISTANCE_FACTOR
                ) or (
                    final_target_type == "base"
                    and diamonds_carried
                    >= inventory_size
                    * BotConfig.CONSIDER_TP_PATH_URGENT_BASE_INVENTORY_RATIO
                )

                if consider_tp_path:
                    utility_via_tp = calculate_utility(
                        entry_tp_obj.position,
                        final_target_type,
                        final_target_obj,
                        full_dist_via_tp,
                        board_bot,
                        board,
                        weights,
                        committed_target_info,
                        True,
                    )
                    if (
                        best_utility_score is None
                        or utility_via_tp.total > best_utility_score.total
                    ):
                        best_utility_score = utility_via_tp

    return best_utility_score
