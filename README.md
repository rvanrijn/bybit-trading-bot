# Bybit Trading Bot

A Bitcoin trading bot implementing an EMA and Stochastic Oscillator strategy for Bybit paper trading.

## Strategy Overview
The bot implements a trading strategy based on:
- EMA (Exponential Moving Average) crossovers
- Stochastic Oscillator signals
- ATR (Average True Range) for dynamic position sizing
- Volume filters for trade confirmation

## Features
- Real-time trading on Bybit
- Paper trading support (testnet)
- Configurable trading parameters
- Position size management
- Stop-loss and take-profit automation
- Logging and monitoring

## Installation

1. Clone the repository:
```bash
git clone https://github.com/rvanrijn/bybit-trading-bot.git
cd bybit-trading-bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure your settings:
- Copy `config/config.example.yaml` to `config/config.yaml`
- Add your Bybit API credentials
- Adjust trading parameters as needed

4. Run the bot:
```bash
python main.py
```

## Configuration
The bot can be configured through `config/config.yaml`:

```yaml
bybit:
  testnet: true  # Set to false for live trading
  api_key: "your_api_key"
  api_secret: "your_api_secret"

trading:
  symbol: "BTCUSDT"
  leverage: 1
  position_size: 0.001  # Base position size in BTC
  risk_reward_ratio: 2.0
  atr_multiplier: 1.75

strategy:
  fast_ema: 8
  slow_ema: 21
  stoch_period: 10
  stoch_k_period: 2
```

## Disclaimer
This bot is for educational purposes only. Use at your own risk. Cryptocurrency trading involves substantial risk of loss and is not suitable for all investors.

## License
MIT License