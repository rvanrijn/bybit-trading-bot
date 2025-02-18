import websocket
import json
import threading
import time
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
        self.is_running = True
        self.reconnect_delay = 5  # Start with 5 second delay
        self.max_reconnect_delay = 300  # Maximum delay of 5 minutes
        
    def start(self):
        """Start the WebSocket connection"""
        self.is_running = True
        self._connect()
        
    def stop(self):
        """Stop the WebSocket connection"""
        self.is_running = False
        if self.ws:
            self.ws.close()
            
    def _connect(self):
        """Establish WebSocket connection with retry mechanism"""
        ws_url = "wss://stream.bybit.com/v5/public/linear"
        
        # Configure WebSocket
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open
        )
        
        # Start WebSocket connection in a separate thread
        wst = threading.Thread(target=self._run_websocket)
        wst.daemon = True
        wst.start()
    
    def _run_websocket(self):
        """Run WebSocket with automatic reconnection"""
        while self.is_running:
            try:
                self.ws.run_forever()
                if self.is_running:  # Only reconnect if we're still supposed to run
                    logger.info(f"WebSocket disconnected. Reconnecting in {self.reconnect_delay} seconds...")
                    time.sleep(self.reconnect_delay)
                    # Implement exponential backoff
                    self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
            except Exception as e:
                logger.error(f"WebSocket run error: {e}")
                time.sleep(self.reconnect_delay)
    
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
                
                # Reset reconnect delay on successful message
                self.reconnect_delay = 5
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def _on_error(self, ws, error):
        """Handle WebSocket errors"""
        logger.error(f"WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection close"""
        logger.info(f"WebSocket connection closed. Status code: {close_status_code}, Message: {close_msg}")
    
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