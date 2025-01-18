import os
import logging
from datetime import datetime
from alpaca_trade_api.rest import REST
from dotenv import load_dotenv
import discord
from discord.webhook import AsyncWebhook
import asyncio
import pandas as pd
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    filename=f'logs/trading_{datetime.now().strftime("%Y%m%d")}.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load environment variables
load_dotenv()

class DiscordNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        
    async def send_message(self, content: str, color: int = 0x00ff00):
        """Send message to Discord channel"""
        async with AsyncWebhook.from_url(self.webhook_url) as webhook:
            embed = discord.Embed(
                description=content,
                color=color,
                timestamp=datetime.now()
            )
            await webhook.send(embed=embed)
    
    async def send_trade_alert(self, trade_info: Dict[str, Any]):
        """Send formatted trade alert"""
        emoji = "🟢" if trade_info['action'] == 'BUY' else "🔴"
        content = f"{emoji} **Trade Alert**\n"
        content += f"Action: {trade_info['action']}\n"
        content += f"Symbol: {trade_info['symbol']}\n"
        content += f"Quantity: {trade_info['quantity']}\n"
        content += f"Price: ${trade_info['price']:.2f}\n"
        content += f"Total: ${trade_info['total']:.2f}"
        
        color = 0x00ff00 if trade_info['action'] == 'BUY' else 0xff0000
        await self.send_message(content, color)
    
    async def send_daily_summary(self, summary: Dict[str, Any]):
        """Send end-of-day summary"""
        content = "📊 **Daily Trading Summary**\n"
        content += f"Date: {summary['date']}\n"
        content += f"Total Trades: {summary['total_trades']}\n"
        content += f"P/L: ${summary['pnl']:.2f} ({summary['pnl_percentage']:.2f}%)\n"
        content += f"Current Balance: ${summary['balance']:.2f}\n"
        content += f"Win Rate: {summary['win_rate']:.1f}%"
        
        color = 0x00ff00 if summary['pnl'] >= 0 else 0xff0000
        await self.send_message(content, color)
    
    async def send_error_alert(self, error_msg: str):
        """Send error notification"""
        content = "⚠️ **Error Alert**\n"
        content += f"Error: {error_msg}\n"
        content += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        await self.send_message(content, 0xff0000)  # Red color for errors

class TradingBot:
    def __init__(self):
        self.api = REST(
            key_id=os.getenv('ALPACA_API_KEY'),
            secret_key=os.getenv('ALPACA_SECRET_KEY'),
            base_url='https://paper-api.alpaca.markets'  # Paper trading URL
        )
        self.discord = DiscordNotifier(os.getenv('DISCORD_WEBHOOK_URL'))
        self.daily_trades = []
        
    def check_market_hours(self) -> bool:
        """Check if the market is open"""
        clock = self.api.get_clock()
        return clock.is_open
    
    async def execute_trade(self, symbol: str, qty: int, side: str, 
                          price: float) -> Dict[str, Any]:
        """Execute trade and send notification"""
        try:
            # Execute trade through Alpaca
            order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side=side,
                type='market',
                time_in_force='gtc'
            )
            
            # Prepare trade info
            trade_info = {
                'action': side.upper(),
                'symbol': symbol,
                'quantity': qty,
                'price': price,
                'total': price * qty
            }
            
            # Send Discord notification
            await self.discord.send_trade_alert(trade_info)
            
            # Add to daily trades list
            self.daily_trades.append(trade_info)
            
            return trade_info
            
        except Exception as e:
            await self.discord.send_error_alert(f"Trade execution failed: {str(e)}")
            raise
    
    async def send_daily_summary(self):
        """Send end-of-day summary to Discord"""
        account = self.api.get_account()
        
        # Calculate daily statistics
        total_trades = len(self.daily_trades)
        pnl = float(account.equity) - float(account.last_equity)
        pnl_percentage = (pnl / float(account.last_equity)) * 100
        
        # Calculate win rate
        winning_trades = sum(1 for trade in self.daily_trades 
                           if (trade['action'] == 'BUY' and trade['price'] < account.equity) or
                              (trade['action'] == 'SELL' and trade['price'] > account.equity))
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        summary = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'total_trades': total_trades,
            'pnl': pnl,
            'pnl_percentage': pnl_percentage,
            'balance': float(account.equity),
            'win_rate': win_rate
        }
        
        await self.discord.send_daily_summary(summary)
    
    async def run(self):
        """Main trading logic"""
        try:
            if not self.check_market_hours():
                await self.discord.send_message("Market is closed")
                return
                
            # Get account information
            account = self.api.get_account()
            await self.discord.send_message(
                f"Trading session started\nCurrent balance: ${float(account.equity)}"
            )
            
            # Your trading logic here
            # This is where you'd implement your strategy
            
            # Send end-of-day summary
            await self.send_daily_summary()
            
        except Exception as e:
            await self.discord.send_error_alert(f"Error in trading bot: {str(e)}")
            logging.error(f"Error in trading bot: {str(e)}")
            raise

if __name__ == "__main__":
    bot = TradingBot()
    asyncio.run(bot.run())
