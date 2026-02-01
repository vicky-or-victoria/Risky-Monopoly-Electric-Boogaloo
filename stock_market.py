# NPC Stock Market System - Fluctuates every 3 minutes

import discord
import random
import asyncio
import io
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple
from datetime import datetime, timedelta, timezone

import matplotlib
matplotlib.use('Agg')  # non-interactive backend — no display needed
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

import database as db

if TYPE_CHECKING:
    from discord.ext import commands

# Stock market companies (NPCs)
STOCK_COMPANIES = {
    'STARK': {
        'name': 'Stark Industries',
        'symbol': 'STARK',
        'initial_price': 800,
        'volatility': 0.08,
        'sector': 'Technology',
        'emoji': '💻'
    },
    'BYD': {
        'name': 'Build Your Dreams',
        'symbol': 'BYD',
        'initial_price': 600,
        'volatility': 0.16,
        'sector': 'Automotive',
        'emoji': '🚗'
    },
    'AERO': {
        'name': 'Lock-in Dynamics',
        'symbol': 'AERO',
        'initial_price': 750,
        'volatility': 0.15,
        'sector': 'Aerospace',
        'emoji': '✈️'
    },
    'RBNK': {
        'name': 'Riskia Bank',
        'symbol': 'RBNK',
        'initial_price': 450,
        'volatility': 0.04,
        'sector': 'Finance',
        'emoji': '🏦'
    },
    'ENRG': {
        'name': 'MegaRisk Energy',
        'symbol': 'ENRG',
        'initial_price': 500,
        'volatility': 0.12,
        'sector': 'Energy',
        'emoji': '⚡'
    },
    'FOOD': {
        'name': 'Jollibee Co.',
        'symbol': 'FOOD',
        'initial_price': 250,
        'volatility': 0.05,
        'sector': 'Food & Beverage',
        'emoji': '🍔'
    },
    'PHARM': {
        'name': 'BigPharma Company',
        'symbol': 'PHARM',
        'initial_price': 600,
        'volatility': 0.09,
        'sector': 'Pharmaceutical',
        'emoji': '💊'
    },
    'PROPTY': {
        'name': 'Risk Properties',
        'symbol': 'PROP',
        'initial_price': 450,
        'volatility': 0.07,
        'sector': 'Real Estate',
        'emoji': '🏢'
    },
    'MEDIA': {
        'name': 'Ursodosal Truth',
        'symbol': 'MEDIA',
        'initial_price': 1200,
        'volatility': 0.11,
        'sector': 'Media & Entertainment',
        'emoji': '📺'
    },
    'RETAIL': {
        'name': 'RiskMart LLC.',
        'symbol': 'RETAIL',
        'initial_price': 750,
        'volatility': 0.06,
        'sector': 'Retail',
        'emoji': '🛒'
    },
    'FINANCE': {
        'name': 'Omnarch Assoc.',
        'symbol': 'FINANCE',
        'initial_price': 1250,
        'volatility': 0.20,
        'sector': 'Finance and Accounting',
        'emoji': '💵'
    },
    'SPACE': {
        'name': 'NAZA Space',
        'symbol': 'SPACE',
        'initial_price': 12500,
        'volatility': 0.30,
        'sector': 'Space Venture Industry',
        'emoji': '🚀'
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
        # Generate the chart once — shared across all guilds
        chart_file = await generate_stock_chart()

        for guild in bot.guilds:
            try:
                # Check if market is frozen for this guild
                is_frozen = await db.is_stock_market_frozen(str(guild.id))
                
                stock_channel_id = await db.get_stock_market_channel(str(guild.id))
                stock_message_id = await db.get_stock_market_message(str(guild.id))

                if stock_channel_id and stock_message_id:
                    try:
                        channel = bot.get_channel(int(stock_channel_id))
                        if not channel:
                            channel = await bot.fetch_channel(int(stock_channel_id))

                        if channel:
                            message = await channel.fetch_message(int(stock_message_id))
                            embed = create_stock_market_embed(updates, is_frozen)

                            if chart_file:
                                # Re-seek the buffer each guild so the File can be read again
                                chart_file.fp.seek(0)
                                file_to_send = discord.File(chart_file.fp, filename='stock_chart.png')
                                await message.edit(embed=embed, attachments=[file_to_send])
                            else:
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


async def generate_stock_chart() -> Optional[discord.File]:
    """
    Render a 4×3 grid of line charts (one subplot per stock) covering the last 3 hours.
    Returns a discord.File wrapping the PNG, or None if there's not enough history yet.

    Layout: 4 columns × 3 rows = 12 cells for 12 stocks.
    Each subplot shows:
      - The stock's symbol as a title
      - A line coloured green if the stock is currently above its 3-hour-ago price, red otherwise
      - A dashed grey horizontal line at the opening price for visual reference
      - Minimal axis decoration to keep things readable at small size
    """
    # Use naive datetime to match database (PostgreSQL TIMESTAMP without timezone)
    three_hours_ago = datetime.utcnow() - timedelta(hours=3)

    # ── pull history for every stock ─────────────────────────────────
    all_history: Dict[str, List[Dict]] = {}
    for symbol in STOCK_COMPANIES:
        rows = await db.get_stock_price_history_since(symbol, three_hours_ago)
        all_history[symbol] = rows

    # If none of the stocks have any history at all, skip the chart entirely
    # (e.g. the bot just started and only one tick has fired)
    if all(len(v) == 0 for v in all_history.values()):
        return None

    # ── layout constants ─────────────────────────────────────────────
    COLS, ROWS = 4, 3
    fig, axes = plt.subplots(ROWS, COLS, figsize=(14, 9), facecolor='#2f3136')
    fig.suptitle('Stock Price History (Last 3 Hours)',
                 color='white', fontsize=15, fontweight='bold', y=0.97)
    axes_flat = axes.flatten()

    # ── iterate over every stock in definition order ─────────────────
    for idx, (key, company) in enumerate(STOCK_COMPANIES.items()):
        ax = axes_flat[idx]
        ax.set_facecolor('#36393f')
        history = all_history.get(key, [])

        symbol_display = company['symbol']
        name_display   = company['name'][:16]  # keep titles short

        if len(history) < 2:
            # Not enough data to draw a line — show placeholder text
            ax.text(0.5, 0.5, f"{symbol_display}\n{name_display}\n\nNo data yet",
                    ha='center', va='center', color='#aaa', fontsize=8,
                    transform=ax.transAxes)
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_visible(False)
            continue

        # Extract time series
        times  = [row['changed_at'] for row in history]
        prices = [row['new_price']  for row in history]

        open_price  = prices[0]   # first price in the 3-hour window
        close_price = prices[-1]  # most recent price

        # Colour: green if up from open, red if down, grey if flat
        if close_price > open_price:
            line_color = '#57f287'   # discord green-ish
        elif close_price < open_price:
            line_color = '#ed4943'   # discord red-ish
        else:
            line_color = '#aaa'

        # Draw
        ax.plot(times, prices, color=line_color, linewidth=1.5, solid_capstyle='round')
        ax.axhline(open_price, color='#555', linestyle='--', linewidth=0.8, alpha=0.7)

        # Fill between line and open price for a subtle area effect
        ax.fill_between(times, prices, open_price,
                        color=line_color, alpha=0.08)

        # ── styling ──────────────────────────────────────────────────
        ax.set_title(f"{symbol_display}  {name_display}",
                     color='white', fontsize=8, fontweight='bold', pad=4)

        # Y-axis: dollar formatting, white text
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(
            lambda val, _: f'${int(val):,}'
        ))
        ax.tick_params(colors='#aaa', labelsize=6.5)
        ax.yaxis.set_tick_params(labelsize=6.5)

        # X-axis: hide labels entirely (too cramped at this size), keep grid
        ax.set_xticks([])

        # Subtle grid
        ax.grid(axis='y', color='#555', linewidth=0.4, alpha=0.5)
        ax.set_axisbelow(True)

        # Border
        for spine in ax.spines.values():
            spine.set_color('#545454')
            spine.set_linewidth(0.6)

        # Tight y-limits with a little breathing room
        price_min, price_max = min(prices), max(prices)
        pad = max((price_max - price_min) * 0.08, 10)
        ax.set_ylim(price_min - pad, price_max + pad)

    plt.tight_layout(rect=[0, 0, 1, 0.94])  # leave room for suptitle

    # ── render to in-memory buffer ───────────────────────────────────
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=120, facecolor=fig.get_facecolor())
    plt.close(fig)   # free memory immediately
    buf.seek(0)

    return discord.File(buf, filename='stock_chart.png')


def create_stock_market_embed(updates: List[Dict] = None, is_frozen: bool = False) -> discord.Embed:
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
    title_prefix = "🔒 " if is_frozen else "📊 "
    title = f"{title_prefix}NPC Stock Market"
    
    if is_frozen:
        description = f"⚠️ **MARKET FROZEN** - Trading is currently disabled\n{table}"
    else:
        description = f"Live stock prices in Risky Monopoly\n{table}"
    
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.red() if is_frozen else discord.Color.gold()
    )
    embed.set_image(url="attachment://stock_chart.png")
    
    footer_text = "Market is FROZEN - No updates" if is_frozen else "Updates every 3 minutes • Use /buy-stock and /sell-stock to trade"
    embed.set_footer(text=footer_text)
    embed.timestamp = discord.utils.utcnow()

    return embed


def schedule_stock_updates(bot: 'commands.Bot'):
    """Schedule automatic stock price updates every 3 minutes"""

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
                # Check if any guild has the market unfrozen before updating
                should_update = False
                for guild in bot.guilds:
                    is_frozen = await db.is_stock_market_frozen(str(guild.id))
                    if not is_frozen:
                        should_update = True
                        break
                
                if should_update:
                    await update_stock_prices(bot)
                else:
                    print("📊 All markets frozen - skipping price update")
                
                # 3-minute tick (180 seconds)
                await asyncio.sleep(180)
            except Exception as e:
                print(f"Error in stock update loop: {e}")
                await asyncio.sleep(180)

    bot.loop.create_task(stock_update_loop())
