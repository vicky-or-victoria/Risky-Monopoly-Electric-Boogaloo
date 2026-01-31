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


class SellCollectibleView(discord.ui.View):
    """View for selecting which collectible to sell"""
    def __init__(self, user_id: int, owned_items: list):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.owned_items = owned_items
        
        # Create select menu for collectibles (max 25 per dropdown)
        options = []
        for item in owned_items[:25]:
            collectible = get_collectible_by_id(item['collectible_id'])
            if collectible:
                sell_price = int(collectible['price'] * 0.8)
                rarity_emoji = {
                    'legendary': '🌟',
                    'epic': '💜',
                    'rare': '💙',
                    'uncommon': '💚',
                    'common': '⚪'
                }.get(collectible['rarity'], '⚪')
                
                options.append(
                    discord.SelectOption(
                        label=collectible['name'][:100],  # Discord limit
                        description=f"{rarity_emoji} Sells for ${sell_price:,} (80% of ${collectible['price']:,})",
                        value=collectible['id'],
                        emoji=collectible['emoji']
                    )
                )
        
        if not options:
            options.append(
                discord.SelectOption(
                    label="No collectibles available",
                    description="You don't have any collectibles to sell",
                    value="none",
                    emoji="❌"
                )
            )
        
        select = discord.ui.Select(
            placeholder="Choose a collectible to sell...",
            min_values=1,
            max_values=1,
            options=options,
            disabled=len(self.owned_items) == 0
        )
        select.callback = self.collectible_selected
        self.add_item(select)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ This is not your sell menu!",
                ephemeral=True
            )
            return False
        return True
    
    async def collectible_selected(self, interaction: discord.Interaction):
        """Handle collectible selection"""
        item_id = interaction.data['values'][0]
        
        if item_id == "none":
            return await interaction.response.send_message(
                "❌ You don't have any collectibles to sell!",
                ephemeral=True
            )
        
        collectible = get_collectible_by_id(item_id)
        if not collectible:
            return await interaction.response.send_message(
                "❌ Invalid collectible!",
                ephemeral=True
            )
        
        # Check if player still owns it
        if not await db.player_owns_collectible(str(self.user_id), item_id):
            return await interaction.response.send_message(
                "❌ You don't own this collectible anymore!",
                ephemeral=True
            )
        
        # Show confirmation
        confirm_view = SellCollectibleConfirmView(self.user_id, item_id, collectible)
        
        sell_price = int(collectible['price'] * 0.8)
        player = await db.get_player(str(self.user_id))
        
        embed = discord.Embed(
            title="💵 Confirm Sale",
            description=f"Are you sure you want to sell **{collectible['name']}**?",
            color=RARITY_COLORS.get(collectible['rarity'], 0x808080)
        )
        embed.add_field(name=f"{collectible['emoji']} Item", value=collectible['name'], inline=False)
        embed.add_field(name="💰 Original Value", value=f"${collectible['price']:,}", inline=True)
        embed.add_field(name="💵 You'll Receive", value=f"${sell_price:,} (80%)", inline=True)
        embed.add_field(name="💸 New Balance", value=f"${player['balance'] + sell_price:,}", inline=True)
        embed.add_field(name="📝 Description", value=collectible['description'], inline=False)
        embed.set_footer(text="Click the button below to confirm the sale")
        
        await interaction.response.edit_message(embed=embed, view=confirm_view)


class SellCollectibleConfirmView(discord.ui.View):
    """View for confirming collectible sale"""
    def __init__(self, user_id: int, item_id: str, collectible: dict):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.item_id = item_id
        self.collectible = collectible
    
    @discord.ui.button(label="✅ Confirm Sale", style=discord.ButtonStyle.success)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ This is not your collectible!", ephemeral=True)
        
        await interaction.response.defer()
        
        # Check if player still owns it
        if not await db.player_owns_collectible(str(self.user_id), self.item_id):
            return await interaction.followup.send("❌ You don't own this collectible anymore!", ephemeral=True)
        
        # Sell for 80% of original price
        sell_price = int(self.collectible['price'] * 0.8)
        
        # Remove from collection and add money
        await db.remove_collectible_from_player(str(self.user_id), self.item_id)
        await db.update_player_balance(str(self.user_id), sell_price)
        
        player = await db.get_player(str(self.user_id))
        
        embed = discord.Embed(
            title="✅ Collectible Sold",
            description=f"You've sold **{self.collectible['name']}** for **${sell_price:,}**",
            color=discord.Color.green()
        )
        embed.add_field(name=f"{self.collectible['emoji']} Item", value=self.collectible['name'], inline=True)
        embed.add_field(name="💰 Original Value", value=f"${self.collectible['price']:,}", inline=True)
        embed.add_field(name="💵 Sale Price (80%)", value=f"${sell_price:,}", inline=True)
        embed.set_footer(text=f"New balance: ${player['balance']:,}")
        
        await interaction.edit_original_response(embed=embed, view=None)
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ This is not your collectible!", ephemeral=True)
        
        await interaction.response.edit_message(content="❌ Sale cancelled.", embed=None, view=None)


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
    async def sell_collectible(self, interaction: discord.Interaction, item_id: str = None):
        """Sell a collectible item with interactive dropdown"""
        await interaction.response.defer(ephemeral=True)
        
        # Get player's collectibles
        owned_items = await db.get_player_collectibles(str(interaction.user.id))
        
        if not owned_items:
            return await interaction.followup.send("You don't own any collectibles to sell!", ephemeral=True)
        
        # If item_id provided, sell that specific item
        if item_id is not None:
            if not await db.player_owns_collectible(str(interaction.user.id), item_id):
                return await interaction.followup.send("❌ You don't own this collectible!", ephemeral=True)
            
            collectible = get_collectible_by_id(item_id)
            if not collectible:
                return await interaction.followup.send("❌ Invalid collectible ID.", ephemeral=True)
            
            # Process sale
            await self._process_collectible_sale(interaction, item_id, collectible)
            return
        
        # No item_id provided, show interactive dropdown
        view = SellCollectibleView(interaction.user.id, owned_items)
        
        total_value = sum(get_collectible_by_id(item['collectible_id'])['price'] for item in owned_items)
        
        embed = discord.Embed(
            title="💵 Sell Collectible",
            description=f"You own **{len(owned_items)}** collectible(s) worth **${total_value:,}**.\n\n"
                       f"Select an item to sell (you'll receive 80% of original value):",
            color=discord.Color.blue()
        )
        
        player = await db.get_player(str(interaction.user.id))
        embed.add_field(name="💰 Current Balance", value=f"${player['balance']:,}", inline=False)
        embed.set_footer(text="Select a collectible from the dropdown below")
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    
    async def _process_collectible_sale(self, interaction: discord.Interaction, item_id: str, collectible: dict):
        """Helper method to process a collectible sale"""
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
        embed.add_field(name=f"{collectible['emoji']} Item", value=collectible['name'], inline=True)
        embed.add_field(name="💰 Original Value", value=f"${collectible['price']:,}", inline=True)
        embed.add_field(name="💵 Sell Price (80%)", value=f"${sell_price:,}", inline=True)
        embed.set_footer(text=f"New balance: ${player['balance']:,}")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
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
