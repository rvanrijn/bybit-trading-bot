import pandas as pd
import numpy as np
from typing import Tuple, Dict
import yaml
import logging
from .bybit_client import BybitClient

logger = logging.getLogger(__name__)

class TradingStrategy:
    def __init__(self, config_path: str):
        """Initialize the trading strategy with configuration"""
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        
        # Initialize strategy parameters
        strategy_config = config['strategy']
        self.fast_ema = strategy_config['fast_ema']
        self.slow_ema = strategy_config['slow_ema']
        self.stoch_period = strategy_config['stoch_period']
        self.stoch_k_period = strategy_config['stoch_k_period']
        
        # Initialize trading parameters
        trading_config = config['trading']
        self.risk_reward_ratio = trading_config['risk_reward_ratio']
        self.position_size = trading_config['position_size']
        self.atr_multiplier = trading_config['atr_multiplier']
        
        # Initialize Bybit client
        self.client = BybitClient(config_path)
        
        # Track current position
        self.current_position = None
        
        logger.info(f"Strategy initialized with parameters: Fast EMA: {self.fast_ema}, Slow EMA: {self.slow_ema}, "
                   f"Stoch Period: {self.stoch_period}, Stoch K: {self.stoch_k_period}")
    
    def calculate_ema(self, data: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average"""
        return data.ewm(span=period, adjust=False).mean()
    
    def calculate_stochastic(self, high: pd.Series, low: pd.Series, close: pd.Series) -> Tuple[pd.Series, pd.Series]:
        """Calculate Stochastic Oscillator"""
        lowest_low = low.rolling(window=self.stoch_period).min()
        highest_high = high.rolling(window=self.stoch_period).max()
        k_line = 100 * (close - lowest_low) / (highest_high - lowest_low)
        d_line = k_line.rolling(window=self.stoch_k_period).mean()
        return k_line, d_line
    
    def calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()
    
    def generate_signals(self, data: pd.DataFrame) -> Dict:
        """Generate trading signals from market data"""
        try:
            df = data.copy()
            
            # Calculate indicators
            df['ema_fast'] = self.calculate_ema(df['close'], self.fast_ema)
            df['ema_slow'] = self.calculate_ema(df['close'], self.slow_ema)
            df['stoch_k'], df['stoch_d'] = self.calculate_stochastic(
                df['high'], df['low'], df['close']
            )
            df['atr'] = self.calculate_atr(df['high'], df['low'], df['close'])
            
            # Calculate volume filter
            df['volume_sma'] = df['volume'].rolling(window=20).mean()
            df['volume_std'] = df['volume'].rolling(window=20).std()
            volume_filter = df['volume'] > (df['volume_sma'] + df['volume_std'])
            
            # Get latest data point
            current = df.iloc[-1]
            previous = df.iloc[-2]
            
            # Log current market conditions
            logger.info(f"Current price: {current['close']:.2f}, "
                       f"Fast EMA: {current['ema_fast']:.2f}, "
                       f"Slow EMA: {current['ema_slow']:.2f}, "
                       f"Stoch K: {current['stoch_k']:.2f}")
            
            if not volume_filter.iloc[-1]:
                logger.info("Volume filter not satisfied - no trade signal")
                return {'signal': 0}
            
            current_price = current['close']
            current_atr = current['atr']
            
            # Generate trading signals
            signal = 0
            stop_loss = None
            take_profit = None
            
            # Buy signal conditions
            buy_conditions = (
                current_price > current['ema_fast'] and
                current_price > current['ema_slow'] and
                previous['stoch_k'] < 20 and current['stoch_k'] > 20
            )
            
            # Sell signal conditions
            sell_conditions = (
                current_price < current['ema_fast'] and
                current_price < current['ema_slow'] and
                previous['stoch_k'] > 80 and current['stoch_k'] < 80
            )
            
            # Log conditions evaluation
            logger.info(f"Signal conditions - Buy: {buy_conditions}, Sell: {sell_conditions}")
            
            # Buy signal
            if buy_conditions:
                signal = 1
                stop_loss = current_price - (current_atr * self.atr_multiplier)
                take_profit = current_price + (current_atr * self.atr_multiplier * self.risk_reward_ratio)
                
                logger.info(f"BUY SIGNAL - Entry: {current_price:.2f}, "
                           f"Stop Loss: {stop_loss:.2f}, "
                           f"Take Profit: {take_profit:.2f}")
            
            # Sell signal
            elif sell_conditions:
                signal = -1
                stop_loss = current_price + (current_atr * self.atr_multiplier)
                take_profit = current_price - (current_atr * self.atr_multiplier * self.risk_reward_ratio)
                
                logger.info(f"SELL SIGNAL - Entry: {current_price:.2f}, "
                           f"Stop Loss: {stop_loss:.2f}, "
                           f"Take Profit: {take_profit:.2f}")
            
            return {
                'signal': signal,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'current_price': current_price
            }
            
        except Exception as e:
            logger.error(f"Error generating signals: {e}")
            return {'signal': 0}
    
    def on_new_data(self, df: pd.DataFrame):
        """Handle new market data updates"""
        try:
            # Check if we have enough data
            if len(df) < max(self.fast_ema, self.slow_ema, self.stoch_period):
                logger.info(f"Not enough data yet. Have {len(df)} candles, need at least "
                           f"{max(self.fast_ema, self.slow_ema, self.stoch_period)}")
                return
            
            # Generate signals from new data
            signal_data = self.generate_signals(df)
            
            # Check if we should enter a new position
            if signal_data['signal'] != 0 and self.current_position is None:
                # Determine position side and size
                side = "Buy" if signal_data['signal'] == 1 else "Sell"
                
                # Place the order
                order = self.client.place_order(
                    side=side,
                    qty=self.position_size,
                    stop_loss=signal_data['stop_loss'],
                    take_profit=signal_data['take_profit']
                )
                
                if order:
                    self.current_position = {
                        'side': side,
                        'entry_price': signal_data['current_price'],
                        'stop_loss': signal_data['stop_loss'],
                        'take_profit': signal_data['take_profit']
                    }
                    logger.info(f"Entered {side} position at {signal_data['current_price']}")
        
        except Exception as e:
            logger.error(f"Error handling new data: {e}")