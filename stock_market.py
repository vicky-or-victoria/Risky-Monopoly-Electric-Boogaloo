# NPC Stock Market System - Fluctuates every 30 seconds

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
        'name': 'Stark Industries',
        'symbol': 'STARK',
        'initial_price': 1000,
        'volatility': 0.08,
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
        'name': 'Locked-In Risk Dynamics',
        'symbol': 'LMRT',
        'initial_price': 1500,
        'volatility': 0.10,
        'sector': 'Aerospace',
        'emoji': '✈️'
    },
    'BANK': {
        'name': 'National Bank of Risk Universalis',
        'symbol': 'RBNK',
        'initial_price': 500,
        'volatility': 0.04,
        'sector': 'Finance',
        'emoji': '🏦'
    },
    'ENRG': {
        'name': 'Mega Risk Energy Company',
        'symbol': 'MREC',
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
    },
    'FINANCE': {
        'name': 'Omn and Arch Associates',
        'symbol': 'OAAF',
        'initial_price': 1250,
        'volatility': 0.25,
        'sector': 'Finance and Accounting',
        'emoji': '💵'
    }
}


async def update_stock_prices(bot: 'commands.Bot'):
    """Update all stock prices with random fluctuations"""
    try:
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

            change_percent = random.uniform(-data['volatility'], data['volatility'])
            price_change = int(current_price * change_percent)
            new_price = max(50, current_price + price_change)  # Minimum $50

            await db.set_stock_price(symbol, new_price)
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
    """
    Create the live stock-market embed.

    Styled to match the wealth & company leaderboards:
      - Gold embed colour
      - Single monospaced code-block table in the description
      - Columns: trend arrow | symbol | company name | price | change
      - Footer with update cadence and trade commands
      - Timestamp auto-set
    """
    rows: List[Dict] = []

    if updates:
        for u in updates:
            data = STOCK_COMPANIES[u['symbol']]
            rows.append({
                'symbol':     u['symbol'],
                'name':       data['name'],
                'price':      u['new_price'],
                'change':     u['change'],
                'change_pct': u['change_percent'],
            })
    else:
        # Fallback when no update data is available (e.g. initial setup)
        for symbol, data in STOCK_COMPANIES.items():
            rows.append({
                'symbol':     symbol,
                'name':       data['name'],
                'price':      data['initial_price'],
                'change':     0,
                'change_pct': 0.0,
            })

    # ── column widths (dynamic so the table stays tight) ────────────
    sym_w   = max(len(r['symbol'])          for r in rows)
    name_w  = max(len(r['name'][:18])       for r in rows)
    price_w = max(len(f"${r['price']:,}")   for r in rows)

    lines: List[str] = []

    # Header row
    lines.append(
        f"  {'SYM':<{sym_w}}  {'COMPANY':<{name_w}}  "
        f"{'PRICE':>{price_w}}  CHANGE"
    )
    # Separator
    lines.append("─" * (sym_w + name_w + price_w + 22))

    # Data rows
    for r in rows:
        if r['change'] > 0:
            arrow = "▲"
            sign  = "+"
        elif r['change'] < 0:
            arrow = "▼"
            sign  = ""   # minus sign already in the formatted number
        else:
            arrow = "─"
            sign  = ""

        price_str = f"${r['price']:,}"

        if r['change'] != 0:
            change_str = f"{sign}${r['change']:,} ({sign}{r['change_pct']:.1f}%)"
        else:
            change_str = "No change"

        lines.append(
            f"{arrow} {r['symbol']:<{sym_w}}  "
            f"{r['name'][:18]:<{name_w}}  "
            f"{price_str:>{price_w}}  {change_str}"
        )

    table = "```\n" + "\n".join(lines) + "\n```"

    # ── assemble embed ───────────────────────────────────────────────
    embed = discord.Embed(
        title="📊 NPC Stock Market",
        description=f"Live stock prices in Risky Monopoly\n{table}",
        color=discord.Color.gold()
    )
    embed.set_footer(text="Updates every 30 seconds • Use /buy-stock and /sell-stock to trade")
    embed.timestamp = discord.utils.utcnow()

    return embed


def schedule_stock_updates(bot: 'commands.Bot'):
    """Schedule automatic stock price updates every 30 seconds"""

    async def stock_update_loop():
        await bot.wait_until_ready()

        # Initialize stock prices on first run
        try:
            for symbol, data in STOCK_COMPANIES.items():
                current = await db.get_stock_price(symbol)
                if current is None:
                    await db.set_stock_price(symbol, data['initial_price'])
        except Exception as e:
            print(f"Error initializing stock prices: {e}")

        while not bot.is_closed():
            try:
                await update_stock_prices(bot)
                # 30-second tick — matches the income-generation loop
                await asyncio.sleep(30)
            except Exception as e:
                print(f"Error in stock update loop: {e}")
                await asyncio.sleep(30)

    bot.loop.create_task(stock_update_loop())
