import websocket
import json
import threading
import time
from typing import Callable
import pandas as pd
import logging
from datetime import datetime
from pybit.unified_trading import HTTP

logger = logging.getLogger(__name__)

class DataFeed:
    def __init__(self, symbol: str, strategy_callback: Callable):
        self.symbol = symbol
        self.strategy_callback = strategy_callback
        self.ws = None
        self.data_buffer = []
        self.is_running = True
        self.reconnect_delay = 5
        self.max_reconnect_delay = 300
        self.ws_lock = threading.Lock()
        self.session = HTTP(testnet=True)
        logger.info(f"[{symbol}] DataFeed initialized")
        
    def fetch_historical_data(self):
        """Fetch historical kline data"""
        try:
            logger.info(f"[{self.symbol}] Fetching historical kline data...")
            
            # Get last 50 candles (more than we need, just to be safe)
            response = self.session.get_kline(
                category="linear",
                symbol=self.symbol,
                interval=15,
                limit=50
            )
            
            if 'result' in response and 'list' in response['result']:
                # Bybit returns newest first, so reverse to get chronological order
                candles = reversed(response['result']['list'])
                
                for candle in candles:
                    self.data_buffer.append({
                        'datetime': pd.to_datetime(int(candle[0]), unit='ms'),
                        'open': float(candle[1]),
                        'high': float(candle[2]),
                        'low': float(candle[3]),
                        'close': float(candle[4]),
                        'volume': float(candle[5])
                    })
                
                logger.info(f"[{self.symbol}] Successfully loaded {len(self.data_buffer)} historical candles")
                
                # Initial analysis with historical data
                df = pd.DataFrame(self.data_buffer)
                df.set_index('datetime', inplace=True)
                self.strategy_callback(df)
            
        except Exception as e:
            logger.error(f"[{self.symbol}] Error fetching historical data: {e}")
    
    def start(self):
        """Start the WebSocket connection"""
        self.is_running = True
        # First get historical data
        self.fetch_historical_data()
        # Then connect to WebSocket for real-time updates
        self._connect()
        
    def stop(self):
        """Stop the WebSocket connection"""
        self.is_running = False
        with self.ws_lock:
            if self.ws:
                self.ws.close()
                self.ws = None
            
    def _connect(self):
        """Establish WebSocket connection with retry mechanism"""
        with self.ws_lock:
            if self.ws:
                logger.info(f"[{self.symbol}] Closing existing WebSocket connection")
                self.ws.close()
                self.ws = None
            
            ws_url = "wss://stream-testnet.bybit.com/v5/public/linear"
            
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
                with self.ws_lock:
                    if self.ws:
                        self.ws.run_forever()
                
                if self.is_running:
                    logger.info(f"[{self.symbol}] WebSocket disconnected. Reconnecting in {self.reconnect_delay} seconds...")
                    time.sleep(self.reconnect_delay)
                    # Implement exponential backoff
                    self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
                    self._connect()
            except Exception as e:
                logger.error(f"[{self.symbol}] WebSocket run error: {e}")
                time.sleep(self.reconnect_delay)
    
    def _on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            if 'topic' in data and data['topic'] == f'kline.15m.{self.symbol}':
                kline = data['data']
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"[{self.symbol}] Received new kline data at {current_time}")
                logger.info(f"[{self.symbol}] Candle: Open: ${float(kline['open']):,.2f}, Close: ${float(kline['close']):,.2f}, " +
                           f"High: ${float(kline['high']):,.2f}, Low: ${float(kline['low']):,.2f}")
                
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
                
                logger.info(f"[{self.symbol}] Current buffer size: {len(self.data_buffer)} candles")
                
                # Convert to DataFrame and pass to strategy
                df = pd.DataFrame(self.data_buffer)
                df.set_index('datetime', inplace=True)
                self.strategy_callback(df)
                
                # Reset reconnect delay on successful message
                self.reconnect_delay = 5
                
        except Exception as e:
            logger.error(f"[{self.symbol}] Error processing message: {e}")
    
    def _on_error(self, ws, error):
        """Handle WebSocket errors"""
        logger.error(f"[{self.symbol}] WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection close"""
        logger.info(f"[{self.symbol}] WebSocket connection closed. Status code: {close_status_code}, Message: {close_msg}")
    
    def _on_open(self, ws):
        """Handle WebSocket connection open"""
        logger.info(f"[{self.symbol}] WebSocket connection opened")
        # Subscribe to kline data
        subscribe_message = {
            "op": "subscribe",
            "args": [f"kline.15m.{self.symbol}"]
        }
        ws.send(json.dumps(subscribe_message))
        logger.info(f"[{self.symbol}] Subscribed to kline data")