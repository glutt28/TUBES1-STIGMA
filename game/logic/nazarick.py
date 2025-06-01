from game.logic.base import BaseLogic
from game import models
from typing import Optional, Tuple
import random

from game.logic.NazarickSublogic.nazarick_config import BotConfig
from game.logic.NazarickSublogic import nazarick_targetfinder as tf
from game.logic.NazarickSublogic import nazarick_movement as mv
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


class NazarickNPC(BaseLogic):
    def __init__(self):
        self.config = BotConfig()
        self.last_position: Optional[models.Position] = None
        self.stuck_counter: int = 0
        self.committed_target_info: Optional[UtilityScore] = None

    def _is_stuck(self, current_position: models.Position) -> bool:
        if self.last_position and position_equals(self.last_position, current_position):
            self.stuck_counter += 1
        else:
            self.stuck_counter = 0
        self.last_position = models.Position(x=current_position.x, y=current_position.y)
        return self.stuck_counter >= self.config.STUCK_THRESHOLD

    def next_move(
        self, board_bot: models.GameObject, board: models.Board
    ) -> Tuple[int, int]:
        current_pos = board_bot.position
        properties = board_bot.properties

        if not properties or not properties.base:
            return (0, 0)

        if self._is_stuck(current_pos):
            self.committed_target_info = None
            return mv.get_random_valid_move(current_pos, board)

        best_utility_score = tf.find_best_actionable_target(
            board_bot, board, self.config.WEIGHTS, self.committed_target_info
        )

        if not best_utility_score:
            self.committed_target_info = None
            return (0, 0)

        self.committed_target_info = best_utility_score
        best_immediate_target_pos = best_utility_score.immediate_target_pos

        if position_equals(current_pos, best_immediate_target_pos):
            self.committed_target_info = None
            return (0, 0)

        move_dx, move_dy = mv.calculate_next_step(
            current_pos, best_immediate_target_pos, board
        )

        return move_dx, move_dy
