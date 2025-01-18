import os
import logging
from datetime import datetime
from alpaca_trade_api.rest import REST
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    filename=f'logs/trading_{datetime.now().strftime("%Y%m%d")}.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load environment variables
load_dotenv()

class TradingBot:
    def __init__(self):
        self.api = REST(
            key_id=os.getenv('ALPACA_API_KEY'),
            secret_key=os.getenv('ALPACA_SECRET_KEY'),
            base_url='https://paper-api.alpaca.markets'  # Paper trading URL
        )
        
    def check_market_hours(self):
        """Check if the market is open"""
        clock = self.api.get_clock()
        return clock.is_open
    
    def run(self):
        """Main trading logic"""
        try:
            if not self.check_market_hours():
                logging.info("Market is closed")
                return
                
            # Get account information
            account = self.api.get_account()
            logging.info(f"Current balance: ${float(account.equity)}")
            
            # Your trading logic here
            # This is where you'd implement your strategy
            
        except Exception as e:
            logging.error(f"Error in trading bot: {str(e)}")
            raise

if __name__ == "__main__":
    bot = TradingBot()
    bot.run()
