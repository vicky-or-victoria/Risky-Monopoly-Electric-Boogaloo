# NPC Stock Market System - Fluctuates randomly

import discord
import random
import asyncio
from typing import TYPE_CHECKING, Dict, List
from datetime import datetime

import database as db

if TYPE_CHECKING:
    from discord.ext import commands

# Stock market companies (NPCs)
STOCK_COMPANIES = {
    'TECH': {
        'name': 'TechCorp Industries',
        'symbol': 'TECH',
        'initial_price': 1000,
        'volatility': 0.08,  # 8% max change per update
        'sector': 'Technology',
        'emoji': '💻'
    },
    'AUTO': {
        'name': 'AutoDrive Motors',
        'symbol': 'AUTO',
        'initial_price': 850,
        'volatility': 0.06,
        'sector': 'Automotive',
        'emoji': '🚗'
    },
    'AERO': {
        'name': 'AeroSpace Dynamics',
        'symbol': 'AERO',
        'initial_price': 1500,
        'volatility': 0.10,
        'sector': 'Aerospace',
        'emoji': '✈️'
    },
    'BANK': {
        'name': 'Global Banking Corp',
        'symbol': 'BANK',
        'initial_price': 500,
        'volatility': 0.04,
        'sector': 'Finance',
        'emoji': '🏦'
    },
    'ENRG': {
        'name': 'EnergyMax Solutions',
        'symbol': 'ENRG',
        'initial_price': 750,
        'volatility': 0.12,
        'sector': 'Energy',
        'emoji': '⚡'
    },
    'FOOD': {
        'name': 'FoodChain Global',
        'symbol': 'FOOD',
        'initial_price': 400,
        'volatility': 0.05,
        'sector': 'Food & Beverage',
        'emoji': '🍔'
    },
    'PHARM': {
        'name': 'PharmaLife Inc',
        'symbol': 'PHARM',
        'initial_price': 1200,
        'volatility': 0.09,
        'sector': 'Pharmaceutical',
        'emoji': '💊'
    },
    'PROP': {
        'name': 'PropertyPlus Real Estate',
        'symbol': 'PROP',
        'initial_price': 950,
        'volatility': 0.07,
        'sector': 'Real Estate',
        'emoji': '🏢'
    },
    'MEDIA': {
        'name': 'MediaStream Networks',
        'symbol': 'MEDIA',
        'initial_price': 600,
        'volatility': 0.11,
        'sector': 'Media & Entertainment',
        'emoji': '📺'
    },
    'RETAIL': {
        'name': 'RetailMart Chain',
        'symbol': 'RETAIL',
        'initial_price': 350,
        'volatility': 0.06,
        'sector': 'Retail',
        'emoji': '🛒'
    }
}

async def update_stock_prices(bot: 'commands.Bot'):
    """Update all stock prices with random fluctuations"""
    try:
        # Get current prices from database
        current_prices = await db.get_all_stock_prices()
        
        # Initialize prices if not set
        if not current_prices:
            for symbol, data in STOCK_COMPANIES.items():
                await db.set_stock_price(symbol, data['initial_price'])
            current_prices = await db.get_all_stock_prices()
        
        # Update each stock
        updates = []
        for symbol, data in STOCK_COMPANIES.items():
            current_price = current_prices.get(symbol, data['initial_price'])
            
            # Calculate price change (-volatility to +volatility)
            change_percent = random.uniform(-data['volatility'], data['volatility'])
            price_change = int(current_price * change_percent)
            new_price = max(50, current_price + price_change)  # Minimum $50
            
            # Update in database
            await db.set_stock_price(symbol, new_price)
            
            # Log the change
            await db.log_stock_price_change(symbol, current_price, new_price, change_percent * 100)
            
            updates.append({
                'symbol': symbol,
                'old_price': current_price,
                'new_price': new_price,
                'change': price_change,
                'change_percent': change_percent * 100
            })
        
        # Update stock market channels in all guilds
        for guild in bot.guilds:
            try:
                stock_channel_id = await db.get_stock_market_channel(str(guild.id))
                stock_message_id = await db.get_stock_market_message(str(guild.id))
                
                if stock_channel_id and stock_message_id:
                    try:
                        channel = bot.get_channel(int(stock_channel_id))
                        if not channel:
                            channel = await bot.fetch_channel(int(stock_channel_id))
                        
                        if channel:
                            message = await channel.fetch_message(int(stock_message_id))
                            
                            # Create updated embed
                            embed = create_stock_market_embed(updates)
                            await message.edit(embed=embed)
                    except Exception as e:
                        print(f"Error updating stock market display for guild {guild.id}: {e}")
            except Exception as e:
                print(f"Error processing stock updates for guild {guild.id}: {e}")
        
        print(f"📈 Updated {len(updates)} stock prices")
        
    except Exception as e:
        print(f"Error in update_stock_prices: {e}")
        import traceback
        traceback.print_exc()

def create_stock_market_embed(updates: List[Dict] = None) -> discord.Embed:
    """Create stock market display embed"""
    embed = discord.Embed(
        title="📊 NPC Stock Market",
        description="Live stock prices updated every 3 minutes",
        color=discord.Color.blue()
    )
    
    if updates:
        for update in updates:
            symbol = update['symbol']
            data = STOCK_COMPANIES[symbol]
            
            # Determine color indicator
            if update['change'] > 0:
                indicator = "📈"
                change_str = f"+${update['change']:,} (+{update['change_percent']:.2f}%)"
            elif update['change'] < 0:
                indicator = "📉"
                change_str = f"-${abs(update['change']):,} ({update['change_percent']:.2f}%)"
            else:
                indicator = "➡️"
                change_str = "No change"
            
            embed.add_field(
                name=f"{data['emoji']} {symbol} - {data['name']}",
                value=f"**${update['new_price']:,}** {indicator}\n{change_str}",
                inline=False
            )
    else:
        for symbol, data in STOCK_COMPANIES.items():
            embed.add_field(
                name=f"{data['emoji']} {symbol} - {data['name']}",
                value=f"**${data['initial_price']:,}**\nSector: {data['sector']}",
                inline=False
            )
    
    embed.set_footer(text="Use /buy-stock and /sell-stock to trade")
    embed.timestamp = discord.utils.utcnow()
    
    return embed

def schedule_stock_updates(bot: 'commands.Bot'):
    """Schedule automatic stock price updates"""
    
    async def stock_update_loop():
        await bot.wait_until_ready()
        
        # Initialize stock prices
        try:
            for symbol, data in STOCK_COMPANIES.items():
                current = await db.get_stock_price(symbol)
                if current is None:
                    await db.set_stock_price(symbol, data['initial_price'])
        except Exception as e:
            print(f"Error initializing stock prices: {e}")
        
        while not bot.is_closed():
            try:
                # Update stock prices
                await update_stock_prices(bot)
                
                # Wait for the configured interval (default 3 minutes = 180 seconds)
                # This can be made configurable per guild if needed
                await asyncio.sleep(180)
                
            except Exception as e:
                print(f"Error in stock update loop: {e}")
                await asyncio.sleep(180)
    
    # Start the loop
    bot.loop.create_task(stock_update_loop())
