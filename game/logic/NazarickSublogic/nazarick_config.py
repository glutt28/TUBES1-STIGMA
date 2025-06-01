class BotConfig:
    MAX_INVENTORY_DEFAULT = 5
    STUCK_THRESHOLD = 3
    ENEMY_DANGER_RADIUS = 2

    LOW_DIAMOND_COUNT_THRESHOLD = 4
    MIN_TIME_FOR_RESET_BENEFIT_MS = 25000
    CONSIDER_TP_PATH_DISTANCE_FACTOR = 1.2
    CONSIDER_TP_PATH_URGENT_BASE_INVENTORY_RATIO = 0.8

    WEIGHTS = {
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
        "commitment_bonus": 2.0,
    }

