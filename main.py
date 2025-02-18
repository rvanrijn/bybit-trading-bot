import logging
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
    # Initialize strategy
    logger.info("Initializing trading strategy...")
    strategy = TradingStrategy('config/config.yaml')
    
    # Initialize and start data feed
    logger.info("Starting data feed...")
    data_feed = DataFeed('BTCUSDT', strategy.on_new_data)
    data_feed.start()
    
    # Keep the main thread running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down bot...")

if __name__ == "__main__":
    main()