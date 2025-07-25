import json

CONFIG_FILE = 'trading_strategy_config.json'

DEFAULT_CONFIG = {
    "INITIAL_CAPITAL": 10000.0,
    "CAPITAL_THRESHOLD": 7500.0,
    "PARAMETER_PROFILES": {
        "SWING_BULL": {
            "ASSET_WHITELIST": ["BTC-USD", "ETH-USD", "SOL-USD"],
            "POSITION_SIZE_PERCENT": 0.10,
            "TAKE_PROFIT_THRESHOLD": 0.05,
            "STOP_LOSS_THRESHOLD": 0.02,
            "TRADING_FREQUENCY": 3600,
            "DESCRIPTION": "Optimized for bullish swing trading."
        },
        "DAYTRADE_NEUTRAL": {
            "ASSET_WHITELIST": ["WIF-USD", "PEPE-USD", "BONK-USD", "DOGE-USD"],
            "POSITION_SIZE_PERCENT": 0.05,
            "TAKE_PROFIT_THRESHOLD": 0.15,
            "STOP_LOSS_THRESHOLD": 0.05,
            "TRADING_FREQUENCY": 600,
            "DESCRIPTION": "Designed for high-frequency day trading in neutral markets."
        },
        "BEAR_MARKET_DEFENSIVE": {
            "ASSET_WHITELIST": ["USDT-USD", "USDC-USD"], # Stablecoins for defensive posture
            "POSITION_SIZE_PERCENT": 0.01,
            "TAKE_PROFIT_THRESHOLD": 0.01,
            "STOP_LOSS_THRESHOLD": 0.005,
            "TRADING_FREQUENCY": 7200,
            "DESCRIPTION": "Highly defensive strategy for bear markets, focusing on capital preservation."
        }
    },
    "SAFETY_CHECKS": {
        "MIN_24H_VOLUME_USD": 1000000,
        "MAX_TOP_10_HOLDER_PERCENT": 0.20,
        "MAX_BUY_SELL_TAX": 0.01,
        "VOLUME_ANOMALY_STD_DEV_MULTIPLIER": 5
    },
    "PORTFOLIO_RISK": {
        "MAX_DAILY_DRAWDOWN_PERCENT": 0.05
    }
}

def get_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return DEFAULT_CONFIG

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)
