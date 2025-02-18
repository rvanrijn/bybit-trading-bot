from pybit.unified_trading import HTTP
from typing import Dict
import yaml
import logging

logger = logging.getLogger(__name__)

class BybitClient:
    def __init__(self, config_path: str):
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        
        self.client = HTTP(
            testnet=config['bybit']['testnet'],
            api_key=config['bybit']['api_key'],
            api_secret=config['bybit']['api_secret']
        )
        self.symbol = config['trading']['symbol']
        
    def place_order(self, side: str, qty: float, stop_loss: float, take_profit: float) -> Dict:
        """Place a new order with stop loss and take profit"""
        try:
            # Place main order
            order = self.client.place_order(
                category="linear",
                symbol=self.symbol,
                side=side,
                orderType="Market",
                qty=qty,
                stopLoss=stop_loss,
                takeProfit=take_profit
            )
            logger.info(f"Placed {side} order: {order}")
            return order
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None

    def get_position(self) -> Dict:
        """Get current position information"""
        try:
            position = self.client.get_positions(
                category="linear",
                symbol=self.symbol
            )
            return position
        except Exception as e:
            logger.error(f"Error getting position: {e}")
            return None
            
    def close_position(self) -> Dict:
        """Close any open position"""
        try:
            position = self.get_position()
            if position and float(position['size']) != 0:
                side = "Sell" if position['side'] == "Buy" else "Buy"
                order = self.client.place_order(
                    category="linear",
                    symbol=self.symbol,
                    side=side,
                    orderType="Market",
                    qty=abs(float(position['size'])),
                    reduceOnly=True
                )
                logger.info(f"Closed position: {order}")
                return order
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return None