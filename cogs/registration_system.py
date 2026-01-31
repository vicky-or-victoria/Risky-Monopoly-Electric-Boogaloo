# Registration System - Reaction-based role assignment

import discord
from discord import app_commands
from discord.ext import commands
import os

import database as db

class RegistrationSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="setup-registration", description="⚙️ Set up player registration system (Admin only)")
    @app_commands.describe(
        channel="Channel where the registration message will be posted",
        role="Role to assign to registered players"
    )
    async def setup_registration(
        self, 
        interaction: discord.Interaction, 
        channel: discord.TextChannel,
        role: discord.Role
    ):
        """Set up the registration system with reaction-based role assignment"""
        # Check if user is bot owner
        app_info = interaction.client.application
        is_bot_owner = interaction.user.id == app_info.owner.id if app_info and app_info.owner else False
        
        if not is_bot_owner:
            # Check if user is server owner
            if interaction.user.id != interaction.guild.owner_id:
                # Check if user has administrator permissions
                if not interaction.user.guild_permissions.administrator:
                    # Check if user has an authorized admin role
                    settings = await db.get_guild_settings(str(interaction.guild.id))
                    if settings and settings.get('admin_role_ids'):
                        admin_role_ids = settings['admin_role_ids']
                        user_role_ids = [str(role_id.id) for role_id in interaction.user.roles]
                        
                        if not any(role_id in admin_role_ids for role_id in user_role_ids):
                            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
                            return
                    else:
                        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
                        return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Create the registration embed
            embed = discord.Embed(
                title="🎮 Welcome to Risky Monopoly!",
                description=(
                    "**Ready to build your business empire?**\n\n"
                    "React to this message with ✅ to register and start playing!\n\n"
                    "**What you'll get:**\n"
                    "• Access to all game commands\n"
                    "• Ability to create and manage companies\n"
                    "• Participate in the economy\n"
                    "• Compete on the leaderboards\n"
                    "• Join or create corporations\n\n"
                    "**To unregister:** Simply remove your reaction."
                ),
                color=discord.Color.green()
            )
            embed.add_field(
                name="📋 Getting Started",
                value=(
                    "After registering, try these commands:\n"
                    "• `/balance` - Check your balance\n"
                    "• `/create-company` - Start your first company\n"
                    "• `/leaderboard` - See the top players"
                ),
                inline=False
            )
            embed.set_footer(text=f"Role: {role.name}")
            embed.timestamp = discord.utils.utcnow()
            
            # Send the message to the channel
            message = await channel.send(embed=embed)
            
            # Add the reaction
            await message.add_reaction("✅")
            
            # Store the settings in database
            await db.set_registration_channel(str(interaction.guild.id), str(channel.id))
            await db.set_registration_message(str(interaction.guild.id), str(message.id))
            await db.set_registration_role(str(interaction.guild.id), str(role.id))
            
            # Send success message
            success_embed = discord.Embed(
                title="✅ Registration System Set Up!",
                description=f"The registration system is now active in {channel.mention}",
                color=discord.Color.green()
            )
            success_embed.add_field(
                name="⚙️ Settings",
                value=(
                    f"**Channel:** {channel.mention}\n"
                    f"**Role:** {role.mention}\n"
                    f"**Reaction:** ✅"
                ),
                inline=False
            )
            success_embed.add_field(
                name="📋 How It Works",
                value=(
                    "• Players react with ✅ to register\n"
                    "• They automatically receive the role\n"
                    "• Removing the reaction removes the role\n"
                    "• Only registered players can use game commands"
                ),
                inline=False
            )
            
            await interaction.followup.send(embed=success_embed, ephemeral=True)
            
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ I don't have permission to send messages in that channel or manage roles!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ Failed to set up registration system: {e}",
                ephemeral=True
            )
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Handle reaction additions for registration"""
        # Ignore bot reactions
        if payload.user_id == self.bot.user.id:
            return
        
        # Get registration settings for this guild
        settings = await db.get_registration_settings(str(payload.guild_id))
        
        if not settings:
            return
        
        # Check if this is the registration message
        if (str(payload.message_id) != settings['registration_message_id'] or
            str(payload.channel_id) != settings['registration_channel_id']):
            return
        
        # Check if the reaction is the correct one (✅)
        if str(payload.emoji) != "✅":
            return
        
        # Get the guild and member
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        
        member = guild.get_member(payload.user_id)
        if not member:
            return
        
        # Get the role
        role = guild.get_role(int(settings['registration_role_id']))
        if not role:
            print(f"Registration role not found: {settings['registration_role_id']}")
            return
        
        # Add the role
        try:
            await member.add_roles(role, reason="Registered for Risky Monopoly")
            print(f"✅ Registered player: {member.name} ({member.id}) in guild {guild.name}")
            
            # Try to send a DM
            try:
                welcome_embed = discord.Embed(
                    title="🎉 Welcome to Risky Monopoly!",
                    description=f"You've successfully registered in **{guild.name}**!",
                    color=discord.Color.green()
                )
                welcome_embed.add_field(
                    name="🚀 Get Started",
                    value=(
                        "Try these commands to begin:\n"
                        "• `/balance` - Check your balance\n"
                        "• `/create-company` - Start your first company\n"
                        "• `/leaderboard` - See the top players\n"
                        "• `/help-info` - View all available commands"
                    ),
                    inline=False
                )
                await member.send(embed=welcome_embed)
            except:
                pass  # If DM fails, that's okay
                
        except discord.Forbidden:
            print(f"Failed to add role to {member.name}: Missing permissions")
        except Exception as e:
            print(f"Error adding registration role: {e}")
    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """Handle reaction removals for unregistration"""
        # Ignore bot reactions
        if payload.user_id == self.bot.user.id:
            return
        
        # Get registration settings for this guild
        settings = await db.get_registration_settings(str(payload.guild_id))
        
        if not settings:
            return
        
        # Check if this is the registration message
        if (str(payload.message_id) != settings['registration_message_id'] or
            str(payload.channel_id) != settings['registration_channel_id']):
            return
        
        # Check if the reaction is the correct one (✅)
        if str(payload.emoji) != "✅":
            return
        
        # Get the guild and member
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        
        member = guild.get_member(payload.user_id)
        if not member:
            return
        
        # Get the role
        role = guild.get_role(int(settings['registration_role_id']))
        if not role:
            print(f"Registration role not found: {settings['registration_role_id']}")
            return
        
        # Remove the role
        try:
            await member.remove_roles(role, reason="Unregistered from Risky Monopoly")
            print(f"❌ Unregistered player: {member.name} ({member.id}) in guild {guild.name}")
        except discord.Forbidden:
            print(f"Failed to remove role from {member.name}: Missing permissions")
        except Exception as e:
            print(f"Error removing registration role: {e}")

async def setup(bot):
    await bot.add_cog(RegistrationSystem(bot))
