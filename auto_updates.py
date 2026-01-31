# Automatic update system for company embeds and leaderboards

import discord
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from discord.ext import commands

# Store bot reference globally
_bot_instance = None

def set_bot_instance(bot: 'commands.Bot'):
    """Set the bot instance for auto-updates"""
    global _bot_instance
    _bot_instance = bot

async def trigger_company_embed_update(company_id: int):
    """Trigger an update for a specific company's embed"""
    if not _bot_instance:
        return
    
    try:
        import database as db
        from events import update_company_embed
        
        company = await db.get_company_by_id(company_id)
        if company:
            await update_company_embed(_bot_instance, company)
    except Exception as e:
        print(f"Error auto-updating company embed {company_id}: {e}")

async def trigger_all_leaderboards_update():
    """Trigger an update for all guild leaderboards"""
    if not _bot_instance:
        return
    
    try:
        leaderboard_cog = _bot_instance.get_cog('LeaderboardCommands')
        if leaderboard_cog:
            for guild in _bot_instance.guilds:
                try:
                    await leaderboard_cog.update_persistent_leaderboard(str(guild.id))
                except Exception as e:
                    print(f'Error auto-updating leaderboard for guild {guild.id}: {e}')
    except Exception as e:
        print(f"Error in auto-update leaderboards: {e}")

async def trigger_updates_for_balance_change(user_id: str):
    """Trigger updates when a player's balance changes"""
    # Update leaderboard since player balance changed
    await trigger_all_leaderboards_update()

async def trigger_updates_for_company_change(company_id: int):
    """Trigger updates when a company's stats change"""
    # Update the company embed
    await trigger_company_embed_update(company_id)
    # Also update leaderboard since company income affects player wealth
    await trigger_all_leaderboards_update()
