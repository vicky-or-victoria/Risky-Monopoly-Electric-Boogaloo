# Tax administration commands

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

import database as db

class TaxCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def is_admin(self, interaction: discord.Interaction) -> bool:
        """Check if user is server owner or has admin role"""
        if interaction.user.id == interaction.guild.owner_id:
            return True
        
        admin_roles = await db.get_admin_roles(str(interaction.guild.id))
        user_role_ids = [str(role.id) for role in interaction.user.roles]
        
        return any(role_id in admin_roles for role_id in user_role_ids)
    
    @app_commands.command(name="set-tax-rate", description="⚙️ Set the automatic tax rate (Admin only)")
    @app_commands.describe(
        rate="Tax rate percentage (0-100)"
    )
    async def set_tax_rate(self, interaction: discord.Interaction, rate: app_commands.Range[float, 0, 100]):
        """Set the tax rate for automatic taxation"""
        if not await self.is_admin(interaction):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return
        
        await db.set_tax_rate(str(interaction.guild.id), rate)
        
        embed = discord.Embed(
            title="✅ Tax Rate Updated",
            description=f"The automatic tax rate has been set to **{rate}%**",
            color=discord.Color.green()
        )
        embed.add_field(
            name="ℹ️ How it works",
            value=f"Every 6 hours, {rate}% of each player's balance will be collected as tax.",
            inline=False
        )
        embed.set_footer(text="Use /set-tax-notification to set where announcements are sent")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="set-tax-notification", description="⚙️ Set tax notification channel (Admin only)")
    @app_commands.describe(
        channel="Channel for tax collection announcements"
    )
    async def set_tax_notification(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set the channel for tax notifications"""
        if not await self.is_admin(interaction):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return
        
        await db.set_tax_notification_channel(str(interaction.guild.id), str(channel.id))
        
        embed = discord.Embed(
            title="✅ Tax Notification Channel Set",
            description=f"Tax collection announcements will be sent to {channel.mention}",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="tax-info", description="📊 View current tax settings")
    async def tax_info(self, interaction: discord.Interaction):
        """Display current tax information"""
        tax_rate = await db.get_tax_rate(str(interaction.guild.id))
        tax_channel_id = await db.get_tax_notification_channel(str(interaction.guild.id))
        
        embed = discord.Embed(
            title="💰 Tax Information",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="📊 Current Tax Rate",
            value=f"{tax_rate}%" if tax_rate > 0 else "No taxes (0%)",
            inline=True
        )
        
        if tax_channel_id:
            embed.add_field(
                name="📢 Notification Channel",
                value=f"<#{tax_channel_id}>",
                inline=True
            )
        else:
            embed.add_field(
                name="📢 Notification Channel",
                value="Not set",
                inline=True
            )
        
        embed.add_field(
            name="⏰ Collection Frequency",
            value="Every 6 hours",
            inline=True
        )
        
        # Get last tax collection info
        last_collection = await db.get_last_tax_collection(str(interaction.guild.id))
        if last_collection:
            embed.add_field(
                name="📅 Last Collection",
                value=discord.utils.format_dt(last_collection['collected_at'], 'R'),
                inline=True
            )
            embed.add_field(
                name="💵 Amount Collected",
                value=f"${last_collection['total_amount']:,}",
                inline=True
            )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="tax-history", description="📜 View tax collection history")
    async def tax_history(self, interaction: discord.Interaction):
        """View tax collection history for this server"""
        history = await db.get_tax_history(str(interaction.guild.id), limit=10)
        
        if not history:
            await interaction.response.send_message("No tax collections have occurred yet.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📜 Tax Collection History",
            description="Last 10 tax collections",
            color=discord.Color.gold()
        )
        
        for record in history:
            timestamp = discord.utils.format_dt(record['collected_at'], 'f')
            embed.add_field(
                name=f"💰 ${record['total_amount']:,}",
                value=f"{timestamp}\n{record['players_taxed']} players taxed",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(TaxCommands(bot))
