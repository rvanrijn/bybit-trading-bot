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
        
    def place_order(self, symbol: str, side: str, qty: float, stop_loss: float, take_profit: float) -> Dict:
        """Place a new order with stop loss and take profit"""
        try:
            # Place main order
            order = self.client.place_order(
                category="linear",
                symbol=symbol,
                side=side,
                orderType="Market",
                qty=qty,
                stopLoss=stop_loss,
                takeProfit=take_profit
            )
            logger.info(f"[{symbol}] Placed {side} order: {order}")
            return order
        except Exception as e:
            logger.error(f"[{symbol}] Error placing order: {e}")
            return None

    def get_position(self, symbol: str) -> Dict:
        """Get current position information"""
        try:
            position = self.client.get_positions(
                category="linear",
                symbol=symbol
            )
            return position
        except Exception as e:
            logger.error(f"[{symbol}] Error getting position: {e}")
            return None
            
    def close_position(self, symbol: str) -> Dict:
        """Close any open position"""
        try:
            position = self.get_position(symbol)
            if position and float(position['size']) != 0:
                side = "Sell" if position['side'] == "Buy" else "Buy"
                order = self.client.place_order(
                    category="linear",
                    symbol=symbol,
                    side=side,
                    orderType="Market",
                    qty=abs(float(position['size'])),
                    reduceOnly=True
                )
                logger.info(f"[{symbol}] Closed position: {order}")
                return order
        except Exception as e:
            logger.error(f"[{symbol}] Error closing position: {e}")
            return None