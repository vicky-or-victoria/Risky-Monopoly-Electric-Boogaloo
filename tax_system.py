# Automatic taxation system for players

import discord
import asyncio
from typing import TYPE_CHECKING
from datetime import datetime

import database as db

if TYPE_CHECKING:
    from discord.ext import commands

async def collect_taxes(bot: 'commands.Bot'):
    """Collect taxes from all players based on guild settings"""
    try:
        # Get all guilds
        for guild in bot.guilds:
            try:
                guild_id = str(guild.id)
                
                # Get tax settings
                tax_rate = await db.get_tax_rate(guild_id)
                tax_channel_id = await db.get_tax_notification_channel(guild_id)
                
                if tax_rate <= 0:
                    continue
                
                # Get all players with positive balance
                players = await db.get_all_players_with_balance()
                
                total_collected = 0
                players_taxed = 0
                
                for player in players:
                    if player['balance'] > 0:
                        tax_amount = int(player['balance'] * (tax_rate / 100))
                        
                        if tax_amount > 0:
                            await db.update_player_balance(player['user_id'], -tax_amount)
                            await db.log_tax_collection(player['user_id'], tax_amount, guild_id)
                            
                            total_collected += tax_amount
                            players_taxed += 1
                
                # Send notification to tax channel
                if tax_channel_id and total_collected > 0:
                    try:
                        channel = bot.get_channel(int(tax_channel_id))
                        if not channel:
                            channel = await bot.fetch_channel(int(tax_channel_id))
                        
                        if channel:
                            embed = discord.Embed(
                                title="💰 Tax Collection Complete",
                                description=f"Automatic tax collection has been processed.",
                                color=discord.Color.gold()
                            )
                            embed.add_field(
                                name="📊 Tax Rate",
                                value=f"{tax_rate}%",
                                inline=True
                            )
                            embed.add_field(
                                name="👥 Players Taxed",
                                value=f"{players_taxed}",
                                inline=True
                            )
                            embed.add_field(
                                name="💵 Total Collected",
                                value=f"${total_collected:,}",
                                inline=True
                            )
                            embed.set_footer(text="Next tax collection in 6 hours")
                            embed.timestamp = discord.utils.utcnow()
                            
                            await channel.send(embed=embed)
                    except Exception as e:
                        print(f"Error sending tax notification for guild {guild_id}: {e}")
                
                if players_taxed > 0:
                    print(f"💰 Collected ${total_collected:,} in taxes from {players_taxed} players in guild {guild.name}")
                
            except Exception as e:
                print(f"Error collecting taxes for guild {guild.id}: {e}")
        
    except Exception as e:
        print(f"Error in collect_taxes: {e}")
        import traceback
        traceback.print_exc()

def schedule_tax_collection(bot: 'commands.Bot'):
    """Schedule automatic tax collection"""
    
    async def tax_collection_loop():
        await bot.wait_until_ready()
        
        while not bot.is_closed():
            try:
                # Collect taxes from all guilds
                await collect_taxes(bot)
                
                # Wait for the tax interval (default 6 hours = 21600 seconds)
                # This will be checked per-guild and can be customized
                await asyncio.sleep(21600)
                
            except Exception as e:
                print(f"Error in tax collection loop: {e}")
                await asyncio.sleep(21600)
    
    # Start the loop
    bot.loop.create_task(tax_collection_loop())
