import logging
import yaml
from src.strategy import TradingStrategy
from src.data_feed import DataFeed
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    # Load config
    with open('config/config.yaml', 'r') as file:
        config = yaml.safe_load(file)
    
    config_path = 'config/config.yaml'
    
    # Initialize strategies and data feeds for each asset
    strategies = {}
    data_feeds = {}
    
    logger.info("Starting multi-asset trading bot...")
    
    # Create strategy and data feed for each enabled asset
    for asset in config['assets']:
        if asset['enabled']:
            symbol = asset['symbol']
            logger.info(f"Initializing strategy for {symbol}...")
            
            # Create strategy instance for this asset
            strategies[symbol] = TradingStrategy(config_path, symbol)
            
            # Create data feed for this asset
            logger.info(f"Starting data feed for {symbol}...")
            data_feeds[symbol] = DataFeed(symbol, strategies[symbol].on_new_data)
            data_feeds[symbol].start()
    
    # Keep the main thread running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down bot...")
        # Stop all data feeds
        for symbol, feed in data_feeds.items():
            logger.info(f"Stopping data feed for {symbol}...")
            feed.stop()

if __name__ == "__main__":
    main()