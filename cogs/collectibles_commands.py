# Collectibles commands - Cars, Planes, Real Estate, Boats, Jewelry, Art

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

import database as db
from collectibles_data import (
    COLLECTIBLES, COLLECTIBLE_CATEGORIES, RARITY_COLORS,
    get_collectibles_by_category, get_collectible_by_id, get_all_categories
)

class CollectiblesCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="browse-collectibles", description="🛍️ Browse available collectibles by category")
    @app_commands.describe(
        category="Category of collectibles to browse"
    )
    @app_commands.choices(category=[
        app_commands.Choice(name="🚗 Luxury Cars", value="cars"),
        app_commands.Choice(name="✈️ Private Jets", value="planes"),
        app_commands.Choice(name="🏰 Real Estate", value="real_estate"),
        app_commands.Choice(name="🛥️ Yachts & Boats", value="boats"),
        app_commands.Choice(name="💎 Jewelry", value="jewelry"),
        app_commands.Choice(name="🎨 Fine Art", value="art"),
    ])
    async def browse_collectibles(self, interaction: discord.Interaction, category: str):
        """Browse collectibles in a specific category"""
        category_data = COLLECTIBLE_CATEGORIES.get(category)
        collectibles = get_collectibles_by_category(category)
        
        if not collectibles:
            await interaction.response.send_message("No collectibles found in this category.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"{category_data['emoji']} {category_data['name']}",
            description=category_data['description'],
            color=discord.Color.blue()
        )
        
        # Sort by price descending
        sorted_items = sorted(collectibles.items(), key=lambda x: x[1]['price'], reverse=True)
        
        for item_id, item in sorted_items[:25]:  # Limit to 25 to avoid embed limits
            rarity_emoji = {
                'legendary': '🌟',
                'epic': '💜',
                'rare': '💙',
                'uncommon': '💚',
                'common': '⚪'
            }.get(item['rarity'], '⚪')
            
            embed.add_field(
                name=f"{item['emoji']} {item['name']}",
                value=f"{rarity_emoji} **${item['price']:,}**\n{item['description']}",
                inline=False
            )
        
        embed.set_footer(text="Use /buy-collectible <item_id> to purchase")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="buy-collectible", description="💰 Purchase a collectible item")
    @app_commands.describe(
        item_id="The ID of the collectible to buy"
    )
    async def buy_collectible(self, interaction: discord.Interaction, item_id: str):
        """Buy a collectible item"""
        await interaction.response.defer()
        
        # Get player
        player = await db.get_player(str(interaction.user.id))
        if not player:
            player = await db.upsert_player(str(interaction.user.id), interaction.user.name)
        
        # Get collectible
        collectible = get_collectible_by_id(item_id)
        if not collectible:
            await interaction.followup.send("❌ Invalid collectible ID.", ephemeral=True)
            return
        
        # Check if already owned
        if await db.player_owns_collectible(str(interaction.user.id), item_id):
            await interaction.followup.send(f"❌ You already own **{collectible['name']}**!", ephemeral=True)
            return
        
        # Check balance
        if player['balance'] < collectible['price']:
            await interaction.followup.send(
                f"❌ Insufficient funds! You need **${collectible['price']:,}** but only have **${player['balance']:,}**.",
                ephemeral=True
            )
            return
        
        # Purchase collectible
        await db.update_player_balance(str(interaction.user.id), -collectible['price'])
        await db.add_collectible_to_player(str(interaction.user.id), item_id)
        
        embed = discord.Embed(
            title="✅ Purchase Successful!",
            description=f"You've acquired **{collectible['name']}**!",
            color=RARITY_COLORS.get(collectible['rarity'], 0x808080)
        )
        embed.add_field(name=f"{collectible['emoji']} Item", value=collectible['name'], inline=True)
        embed.add_field(name="💰 Price", value=f"${collectible['price']:,}", inline=True)
        embed.add_field(name="⭐ Rarity", value=collectible['rarity'].title(), inline=True)
        embed.add_field(name="📝 Description", value=collectible['description'], inline=False)
        embed.set_footer(text=f"New balance: ${player['balance'] - collectible['price']:,}")
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="my-collection", description="🏆 View your collectibles collection")
    async def my_collection(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
        """View a player's collectibles collection"""
        target_user = user or interaction.user
        
        # Get player's collectibles
        owned_items = await db.get_player_collectibles(str(target_user.id))
        
        if not owned_items:
            if target_user == interaction.user:
                await interaction.response.send_message("You don't own any collectibles yet! Use `/browse-collectibles` to start collecting.", ephemeral=True)
            else:
                await interaction.response.send_message(f"{target_user.mention} doesn't own any collectibles yet.", ephemeral=True)
            return
        
        # Calculate total value
        total_value = sum(get_collectible_by_id(item['collectible_id'])['price'] for item in owned_items)
        
        embed = discord.Embed(
            title=f"🏆 {target_user.name}'s Collection",
            description=f"**Total Items:** {len(owned_items)}\n**Total Value:** ${total_value:,}",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=target_user.display_avatar.url)
        
        # Group by category
        by_category = {}
        for item in owned_items:
            collectible = get_collectible_by_id(item['collectible_id'])
            if collectible:
                category = collectible['category']
                if category not in by_category:
                    by_category[category] = []
                by_category[category].append(collectible)
        
        # Display by category
        for category, items in by_category.items():
            category_data = COLLECTIBLE_CATEGORIES[category]
            items_list = "\n".join([f"{item['emoji']} {item['name']} - ${item['price']:,}" for item in items[:5]])
            
            if len(items) > 5:
                items_list += f"\n*...and {len(items) - 5} more*"
            
            embed.add_field(
                name=f"{category_data['emoji']} {category_data['name']} ({len(items)})",
                value=items_list,
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="sell-collectible", description="💵 Sell a collectible from your collection")
    @app_commands.describe(
        item_id="The ID of the collectible to sell"
    )
    async def sell_collectible(self, interaction: discord.Interaction, item_id: str):
        """Sell a collectible item"""
        await interaction.response.defer()
        
        # Check if player owns it
        if not await db.player_owns_collectible(str(interaction.user.id), item_id):
            await interaction.followup.send("❌ You don't own this collectible!", ephemeral=True)
            return
        
        collectible = get_collectible_by_id(item_id)
        if not collectible:
            await interaction.followup.send("❌ Invalid collectible ID.", ephemeral=True)
            return
        
        # Sell for 80% of original price
        sell_price = int(collectible['price'] * 0.8)
        
        # Remove from collection and add money
        await db.remove_collectible_from_player(str(interaction.user.id), item_id)
        await db.update_player_balance(str(interaction.user.id), sell_price)
        
        player = await db.get_player(str(interaction.user.id))
        
        embed = discord.Embed(
            title="✅ Collectible Sold",
            description=f"You've sold **{collectible['name']}** for **${sell_price:,}**",
            color=discord.Color.green()
        )
        embed.add_field(name="💰 Original Value", value=f"${collectible['price']:,}", inline=True)
        embed.add_field(name="💵 Sell Price (80%)", value=f"${sell_price:,}", inline=True)
        embed.set_footer(text=f"New balance: ${player['balance']:,}")
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="collection-stats", description="📊 View collection statistics")
    async def collection_stats(self, interaction: discord.Interaction):
        """View server-wide collection statistics"""
        stats = await db.get_collectibles_stats()
        
        embed = discord.Embed(
            title="📊 Collection Statistics",
            description="Server-wide collectibles data",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🏆 Total Collectors",
            value=f"{stats['total_collectors']}",
            inline=True
        )
        embed.add_field(
            name="💎 Total Items Owned",
            value=f"{stats['total_items']}",
            inline=True
        )
        embed.add_field(
            name="💰 Total Collection Value",
            value=f"${stats['total_value']:,}",
            inline=True
        )
        
        if stats['most_collected']:
            collectible = get_collectible_by_id(stats['most_collected'])
            embed.add_field(
                name="🌟 Most Collected Item",
                value=f"{collectible['emoji']} {collectible['name']}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(CollectiblesCommands(bot))
