import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'smarttrade-guard-safety-key-2026')
    DATABASE = os.path.join(BASE_DIR, 'smarttrade.db')
    DEBUG = True

    # Risk Engine Component Weights (Sum = 100%)
    RISK_WEIGHTS = {
        'loss_chasing': 0.30,
        'overtrading': 0.20,
        'fomo': 0.20,
        'risk_escalation': 0.15,
        'personal_rule': 0.10,
        'emotion': 0.05
    }

    # Score Thresholds
    RISK_LEVEL_LOW_MAX = 29
    RISK_LEVEL_MEDIUM_MAX = 59
    # 60 - 100 is HIGH RISK

    # Default Rule Thresholds
    LOSS_CHASING_WINDOW_MINUTES = 30
    OVERTRADING_BURST_MINUTES = 15
    OVERTRADING_BURST_THRESHOLD = 5
    CONSECUTIVE_LOSSES_TRIGGER = 3
    ESCALATION_LOOKBACK = 3

    # Cooling Off Durations (in seconds for countdown, displayed in minutes)
    COOLING_OFF_DEFAULT_SECONDS = 1800  # 30 minutes
    COOLING_OFF_OVERTRADING_SECONDS = 900  # 15 minutes
    COOLING_OFF_EMERGENCY_SECONDS = 1800  # 30 minutes
