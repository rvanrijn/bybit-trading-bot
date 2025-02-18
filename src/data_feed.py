import websocket
import json
import threading
from typing import Callable
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class DataFeed:
    def __init__(self, symbol: str, strategy_callback: Callable):
        """
        Initialize the data feed handler
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            strategy_callback: Callback function to handle new data
        """
        self.symbol = symbol
        self.strategy_callback = strategy_callback
        self.ws = None
        self.data_buffer = []
        
    def start(self):
        """Start the WebSocket connection"""
        ws_url = "wss://stream.bybit.com/v5/public/linear"
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open
        )
        
        wst = threading.Thread(target=self.ws.run_forever)
        wst.daemon = True
        wst.start()
    
    def _on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            if 'topic' in data and data['topic'] == f'kline.15m.{self.symbol}':
                kline = data['data']
                self.data_buffer.append({
                    'datetime': pd.to_datetime(kline['timestamp'], unit='ms'),
                    'open': float(kline['open']),
                    'high': float(kline['high']),
                    'low': float(kline['low']),
                    'close': float(kline['close']),
                    'volume': float(kline['volume'])
                })
                
                # Keep last 100 candles for analysis
                if len(self.data_buffer) > 100:
                    self.data_buffer.pop(0)
                
                # Convert to DataFrame and pass to strategy
                df = pd.DataFrame(self.data_buffer)
                df.set_index('datetime', inplace=True)
                self.strategy_callback(df)
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def _on_error(self, ws, error):
        """Handle WebSocket errors"""
        logger.error(f"WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection close"""
        logger.info("WebSocket connection closed")
    
    def _on_open(self, ws):
        """Handle WebSocket connection open"""
        logger.info("WebSocket connection opened")
        # Subscribe to kline data
        subscribe_message = {
            "op": "subscribe",
            "args": [f"kline.15m.{self.symbol}"]
        }
        ws.send(json.dumps(subscribe_message))
        logger.info(f"Subscribed to {self.symbol} kline data")