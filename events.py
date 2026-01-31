# Daily event system for companies - FIXED VERSION (BACKWARDS COMPATIBLE)

import discord
import random
from typing import TYPE_CHECKING
from datetime import datetime, timedelta

import database as db
from company_data import COMPANY_EVENTS, is_event_available_for_rank, get_rank_color

if TYPE_CHECKING:
    from discord.ext import commands

async def generate_company_income(bot: 'commands.Bot'):
    """Generate income for ALL companies every 30 seconds (separate from events)"""
    try:
        companies = await db.get_all_companies()
        income_generated = 0
        
        for company in companies:
            try:
                # Add current income to player balance
                await db.update_player_balance(company['owner_id'], company['current_income'])
                income_generated += 1
                
            except Exception as e:
                print(f'Error generating income for company {company.get("id", "unknown")}: {e}')
        
        if income_generated > 0:
            print(f'💰 Generated income for {income_generated} companies')
        
    except Exception as e:
        print(f'Error in generate_company_income: {e}')
        import traceback
        traceback.print_exc()

async def trigger_company_events(bot: 'commands.Bot'):
    """Trigger events for companies based on guild event frequency settings (separate from income)"""
    try:
        companies = await db.get_all_companies()
        events_processed = 0
        
        for company in companies:
            try:
                # Get the guild ID from the thread
                if not company.get('thread_id'):
                    continue
                
                thread = bot.get_channel(int(company['thread_id']))
                if not thread:
                    try:
                        thread = await bot.fetch_channel(int(company['thread_id']))
                    except:
                        continue
                
                if not thread or not hasattr(thread, 'guild'):
                    continue
                
                guild_id = str(thread.guild.id)
                
                # Get event frequency for this guild
                event_frequency_hours = await db.get_event_frequency(guild_id)
                
                # Check if enough time has passed since last event
                last_event_time = company.get('last_event_at')
                if last_event_time:
                    time_since_last = datetime.now() - last_event_time
                    required_time = timedelta(hours=event_frequency_hours)
                    
                    if time_since_last < required_time:
                        # Not time for an event yet
                        continue
                
                # Process the event (this MODIFIES income, doesn't generate it)
                await process_company_event(bot, company)
                events_processed += 1
                
            except Exception as e:
                print(f'Error processing event for company {company.get("id", "unknown")}: {e}')
        
        if events_processed > 0:
            print(f'📰 Processed {events_processed} company events')
        
    except Exception as e:
        print(f'Error in trigger_company_events: {e}')
        import traceback
        traceback.print_exc()

async def process_company_event(bot: 'commands.Bot', company: dict):
    """Process a single company event - this MODIFIES the income rate"""
    # Determine event type
    # 15% neutral, 42.5% positive, 42.5% negative
    event_chance = random.random()
    
    if event_chance < 0.15:
        event_pool = COMPANY_EVENTS['neutral']
        event_type = 'neutral'
    elif event_chance < 0.575:
        # Positive event
        event_pool = [e for e in COMPANY_EVENTS['positive'] 
                     if is_event_available_for_rank(e, company['rank'])]
        event_type = 'positive'
    else:
        # Negative event
        event_pool = [e for e in COMPANY_EVENTS['negative'] 
                     if is_event_available_for_rank(e, company['rank'])]
        event_type = 'negative'
    
    # Fallback to neutral if no events available
    if not event_pool:
        event_pool = COMPANY_EVENTS['neutral']
        event_type = 'neutral'
    
    # Select random event
    event = random.choice(event_pool)
    
    # Calculate income change (this changes the RATE, not generates money)
    income_change = int(company['current_income'] * event['income_multiplier'])
    
    # Update company in database
    # NOTE: update_company_income will automatically trigger company embed update
    updated_company = await db.update_company_income(company['id'], income_change)
    
    # Log the event
    await db.log_company_event(
        company['id'],
        event_type,
        event['description'],
        income_change
    )
    
    # Update the pinned company embed
    await update_company_embed(bot, updated_company)
    
    # Post event to company thread if it exists
    if company['thread_id']:
        try:
            thread = bot.get_channel(int(company['thread_id']))
            if not thread:
                thread = await bot.fetch_channel(int(company['thread_id']))
            
            if thread:
                # Determine embed color
                if event_type == 'positive':
                    color = discord.Color.green()
                elif event_type == 'negative':
                    color = discord.Color.red()
                else:
                    color = discord.Color.gold()
                
                embed = discord.Embed(
                    title="📰 Company Event",
                    description=event['description'],
                    color=color
                )
                embed.add_field(
                    name="📊 Income Change",
                    value=f"+${income_change:,}/30s" if income_change >= 0 else f"-${abs(income_change):,}/30s",
                    inline=True
                )
                embed.add_field(
                    name="📈 New Income Rate",
                    value=f"${updated_company['current_income']:,}/30s",
                    inline=True
                )
                
                # Get event frequency safely
                event_freq = 6  # default
                if thread.guild:
                    try:
                        event_freq = await db.get_event_frequency(str(thread.guild.id))
                    except:
                        pass
                
                embed.add_field(
                    name="🕐 Next Event",
                    value=f"In ~{event_freq} hours",
                    inline=True
                )
                embed.timestamp = discord.utils.utcnow()
                
                await thread.send(embed=embed)
        except Exception as e:
            print(f"Failed to post event to thread {company['thread_id']}: {e}")

async def update_company_embed(bot: 'commands.Bot', company: dict):
    """Update the pinned company embed with current stats"""
    if not company.get('embed_message_id') or not company.get('thread_id'):
        return
    
    try:
        thread = bot.get_channel(int(company['thread_id']))
        if not thread:
            thread = await bot.fetch_channel(int(company['thread_id']))
        
        if not thread:
            return
        
        # Fetch the embed message
        try:
            message = await thread.fetch_message(int(company['embed_message_id']))
        except:
            return
        
        # Get assets count
        assets = await db.get_company_assets(company['id'])
        
        # Rebuild the embed with updated stats
        embed = discord.Embed(
            title=f"🏢 {company['name']}",
            description=f"**Rank {company['rank']} Company**\nOwned by <@{company['owner_id']}>",
            color=get_rank_color(company['rank'])
        )
        embed.add_field(name="💵 Income/30s", value=f"${company['current_income']:,}", inline=True)
        embed.add_field(name="📊 Income/Min", value=f"${company['current_income'] * 2:,}", inline=True)
        embed.add_field(name="🕐 Income/Hour", value=f"${company['current_income'] * 120:,}", inline=True)
        embed.add_field(name="💰 Base Income", value=f"${company['base_income']:,}/30s", inline=True)
        embed.add_field(name="⭐ Reputation", value=f"{company['reputation']}/100", inline=True)
        embed.add_field(name="🎯 Assets", value=f"{len(assets)}", inline=True)
        embed.add_field(name="🆔 Company ID", value=f"#{company['id']}", inline=True)
        embed.add_field(name="📅 Established", value=discord.utils.format_dt(company['created_at'], 'D'), inline=True)
        embed.set_footer(text="Use rm!upgrade-company in this thread to purchase assets! • Updates every 30s")
        embed.timestamp = discord.utils.utcnow()
        
        # Edit the message
        await message.edit(embed=embed)
    except Exception as e:
        print(f"Error updating company embed for company {company['id']}: {e}")

def schedule_income_and_events(bot: 'commands.Bot'):
    """Schedule BOTH income generation (every 30s) AND event processing (every 30s check)"""
    import asyncio
    
    async def run_income_and_events_loop():
        await bot.wait_until_ready()
        
        while not bot.is_closed():
            try:
                # ALWAYS generate income every 30 seconds for all companies
                await generate_company_income(bot)
                
                # Check if any companies are due for events (based on guild frequency settings)
                await trigger_company_events(bot)
                
                # Update all guild leaderboards
                try:
                    leaderboard_cog = bot.get_cog('LeaderboardCommands')
                    if leaderboard_cog:
                        for guild in bot.guilds:
                            try:
                                await leaderboard_cog.update_persistent_leaderboard(str(guild.id))
                            except Exception as e:
                                print(f'Error updating leaderboard for guild {guild.id}: {e}')
                except Exception as e:
                    print(f'Error in leaderboard update: {e}')
                
                # Wait 30 seconds before next cycle
                await asyncio.sleep(30)
            except Exception as e:
                print(f"Error in income/events loop: {e}")
                await asyncio.sleep(30)
    
    # Start the loop
    bot.loop.create_task(run_income_and_events_loop())
    print('✅ Income generation system started (every 30 seconds)')
    print('✅ Event processing system started (checks every 30 seconds, triggers based on guild frequency)')

# BACKWARDS COMPATIBILITY - ALL POSSIBLE FUNCTION NAMES
def schedule_daily_events(bot: 'commands.Bot'):
    """Backwards compatibility alias #1"""
    return schedule_income_and_events(bot)

def trigger_daily_events(bot: 'commands.Bot'):
    """Backwards compatibility alias #2 - THIS IS WHAT YOUR MAIN.PY IMPORTS"""
    return schedule_income_and_events(bot)
