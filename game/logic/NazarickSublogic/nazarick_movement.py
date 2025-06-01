from typing import Tuple, List
from game import models
import random


def calculate_next_step(
    current: models.Position, target: models.Position, board: models.Board
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


def get_random_valid_move(
    current: models.Position, board: models.Board
) -> Tuple[int, int]:
    possible_moves = [(1, 0), (0, 1), (-1, 0), (0, -1)]
    random.shuffle(possible_moves)
    for dx_rand, dy_rand in possible_moves:
        if board.is_valid_move(current, dx_rand, dy_rand):
            return (dx_rand, dy_rand)
    return (0, 0)
