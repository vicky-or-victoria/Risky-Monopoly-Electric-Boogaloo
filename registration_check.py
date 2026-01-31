# Registration check utility
# This module provides a decorator to check if a player is registered before allowing command use

import discord
from discord.ext import commands
from functools import wraps
import database as db

async def is_registered(interaction: discord.Interaction) -> bool:
    """Check if a user has the registration role"""
    # Get registration settings
    settings = await db.get_registration_settings(str(interaction.guild.id))
    
    if not settings or not settings.get('registration_role_id'):
        # If registration is not set up, allow all commands
        return True
    
    # Check if user has the registration role
    role_id = int(settings['registration_role_id'])
    role = interaction.guild.get_role(role_id)
    
    if not role:
        # If role doesn't exist, allow command
        return True
    
    # Check if member has the role
    return role in interaction.user.roles

def require_registration():
    """Decorator to require registration for command use"""
    async def predicate(interaction: discord.Interaction) -> bool:
        if not await is_registered(interaction):
            # Get registration settings to show helpful message
            settings = await db.get_registration_settings(str(interaction.guild.id))
            
            embed = discord.Embed(
                title="🚫 Registration Required",
                description="You must be registered to use this command!",
                color=discord.Color.red()
            )
            
            if settings and settings.get('registration_channel_id'):
                channel = interaction.guild.get_channel(int(settings['registration_channel_id']))
                if channel:
                    embed.add_field(
                        name="How to Register",
                        value=f"React with ✅ in {channel.mention} to register!",
                        inline=False
                    )
            else:
                embed.add_field(
                    name="How to Register",
                    value="Contact a server admin to set up the registration system.",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True
    
    return commands.check(predicate)

# For app_commands (slash commands)
async def check_registration(interaction: discord.Interaction) -> bool:
    """Check function for app_commands"""
    if not await is_registered(interaction):
        settings = await db.get_registration_settings(str(interaction.guild.id))
        
        embed = discord.Embed(
            title="🚫 Registration Required",
            description="You must be registered to use this command!",
            color=discord.Color.red()
        )
        
        if settings and settings.get('registration_channel_id'):
            channel = interaction.guild.get_channel(int(settings['registration_channel_id']))
            if channel:
                embed.add_field(
                    name="How to Register",
                    value=f"React with ✅ in {channel.mention} to register!",
                    inline=False
                )
        else:
            embed.add_field(
                name="How to Register",
                value="Contact a server admin to set up the registration system.",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return False
    return True
