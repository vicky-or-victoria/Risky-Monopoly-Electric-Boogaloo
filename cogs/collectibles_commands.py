# Collectibles commands - Enhanced with persistent display and stylized UI

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

import database as db
from collectibles_data import (
    COLLECTIBLES, COLLECTIBLE_CATEGORIES, RARITY_COLORS,
    get_collectibles_by_category, get_collectible_by_id, get_all_categories
)


def create_collectibles_catalog_embed() -> discord.Embed:
    """Create a comprehensive collectibles catalog embed"""
    embed = discord.Embed(
        title="🏆 Luxury Collectibles Catalog",
        description="**Browse and purchase exclusive collectibles to expand your empire!**\n\n"
                   "Use the buttons below to explore categories or `/browse-collectibles` to shop.",
        color=discord.Color.gold()
    )
    
    # Add category overview
    for category_key, category_data in COLLECTIBLE_CATEGORIES.items():
        items = get_collectibles_by_category(category_key)
        if items:
            price_range = f"${min(item['price'] for item in items):,} - ${max(item['price'] for item in items):,}"
            embed.add_field(
                name=f"{category_data['emoji']} {category_data['name']}",
                value=f"**{len(items)} items** | {price_range}\n{category_data['description'][:100]}",
                inline=False
            )
    
    embed.add_field(
        name="💡 How to Use",
        value="• Use `/browse-collectibles` to view items by category\n"
              "• Use `/buy-collectible` to purchase an item\n"
              "• Use `/my-collection` to view your collection\n"
              "• Use `/sell-collectible` to sell items (80% refund)",
        inline=False
    )
    
    embed.set_footer(text="💎 Build your luxury empire • Prices shown are purchase prices")
    embed.timestamp = discord.utils.utcnow()
    
    return embed


class CollectiblesCatalogView(discord.ui.View):
    """Persistent view for the collectibles catalog display"""
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="🚗 Luxury Cars", style=discord.ButtonStyle.primary, custom_id="collectibles:cars")
    async def cars_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_category(interaction, "cars")
    
    @discord.ui.button(label="✈️ Private Jets", style=discord.ButtonStyle.primary, custom_id="collectibles:planes")
    async def planes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_category(interaction, "planes")
    
    @discord.ui.button(label="🏰 Real Estate", style=discord.ButtonStyle.primary, custom_id="collectibles:real_estate")
    async def real_estate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_category(interaction, "real_estate")
    
    @discord.ui.button(label="🛥️ Yachts", style=discord.ButtonStyle.primary, custom_id="collectibles:boats")
    async def boats_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_category(interaction, "boats")
    
    @discord.ui.button(label="💎 Jewelry", style=discord.ButtonStyle.primary, custom_id="collectibles:jewelry")
    async def jewelry_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_category(interaction, "jewelry")
    
    @discord.ui.button(label="🎨 Fine Art", style=discord.ButtonStyle.primary, custom_id="collectibles:art")
    async def art_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_category(interaction, "art")
    
    @discord.ui.button(label="🏆 My Collection", style=discord.ButtonStyle.success, custom_id="collectibles:mycollection")
    async def my_collection_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        # Get player's collectibles
        owned_items = await db.get_player_collectibles(str(interaction.user.id))
        
        if not owned_items:
            return await interaction.followup.send(
                "You don't own any collectibles yet! Use the buttons above to browse and purchase.",
                ephemeral=True
            )
        
        # Calculate total value
        total_value = sum(get_collectible_by_id(item['collectible_id'])['price'] for item in owned_items)
        
        embed = discord.Embed(
            title=f"🏆 {interaction.user.name}'s Collection",
            description=f"**Total Items:** {len(owned_items)}\n**Total Value:** ${total_value:,}",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
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
        
        embed.set_footer(text="Use /sell-collectible to sell items for 80% of their value")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def show_category(self, interaction: discord.Interaction, category: str):
        """Show items in a specific category"""
        await interaction.response.defer(ephemeral=True)
        
        items = get_collectibles_by_category(category)
        category_data = COLLECTIBLE_CATEGORIES[category]
        
        if not items:
            return await interaction.followup.send(
                f"No items available in {category_data['name']}.",
                ephemeral=True
            )
        
        embed = discord.Embed(
            title=f"{category_data['emoji']} {category_data['name']}",
            description=category_data['description'],
            color=discord.Color.blue()
        )
        
        # Show items grouped by rarity
        by_rarity = {}
        for item in items:
            rarity = item['rarity']
            if rarity not in by_rarity:
                by_rarity[rarity] = []
            by_rarity[rarity].append(item)
        
        # Display in rarity order
        rarity_order = ['legendary', 'epic', 'rare', 'uncommon', 'common']
        for rarity in rarity_order:
            if rarity in by_rarity:
                rarity_items = by_rarity[rarity]
                rarity_emoji = {
                    'legendary': '🌟',
                    'epic': '💜',
                    'rare': '💙',
                    'uncommon': '💚',
                    'common': '⚪'
                }.get(rarity, '⚪')
                
                items_text = "\n".join([
                    f"{item['emoji']} **{item['name']}** - ${item['price']:,}"
                    for item in rarity_items[:5]
                ])
                
                if len(rarity_items) > 5:
                    items_text += f"\n*...and {len(rarity_items) - 5} more*"
                
                embed.add_field(
                    name=f"{rarity_emoji} {rarity.title()} ({len(rarity_items)})",
                    value=items_text,
                    inline=False
                )
        
        player = await db.get_player(str(interaction.user.id))
        if player:
            embed.set_footer(text=f"Your balance: ${player['balance']:,} • Use /buy-collectible to purchase")
        else:
            embed.set_footer(text="Use /buy-collectible to purchase items")
        
        await interaction.followup.send(embed=embed, ephemeral=True)


class BuyCollectibleView(discord.ui.View):
    """View for selecting which collectible to buy"""
    def __init__(self, user_id: int, category: str, player: dict):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.player = player
        
        items = get_collectibles_by_category(category)
        
        # Create select menu for collectibles (max 25 per dropdown)
        options = []
        for item in items[:25]:
            rarity_emoji = {
                'legendary': '🌟',
                'epic': '💜',
                'rare': '💙',
                'uncommon': '💚',
                'common': '⚪'
            }.get(item['rarity'], '⚪')
            
            # Check if player can afford it
            can_afford = player['balance'] >= item['price']
            
            options.append(
                discord.SelectOption(
                    label=f"{item['name'][:80]}" + ("" if can_afford else " [Can't Afford]"),
                    description=f"{rarity_emoji} ${item['price']:,} | {item['rarity'].title()}",
                    value=item['id'],
                    emoji=item['emoji']
                )
            )
        
        select = discord.ui.Select(
            placeholder="Choose a collectible to purchase...",
            min_values=1,
            max_values=1,
            options=options
        )
        select.callback = self.collectible_selected
        self.add_item(select)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ This is not your shop menu!",
                ephemeral=True
            )
            return False
        return True
    
    async def collectible_selected(self, interaction: discord.Interaction):
        """Handle collectible selection"""
        item_id = interaction.data['values'][0]
        collectible = get_collectible_by_id(item_id)
        
        if not collectible:
            return await interaction.response.send_message(
                "❌ Invalid collectible!",
                ephemeral=True
            )
        
        # Show confirmation
        confirm_view = BuyCollectibleConfirmView(self.user_id, item_id, collectible)
        
        embed = discord.Embed(
            title="🛍️ Confirm Purchase",
            description=f"Are you sure you want to buy **{collectible['name']}**?",
            color=RARITY_COLORS.get(collectible['rarity'], 0x808080)
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name=f"{collectible['emoji']} Item", value=collectible['name'], inline=False)
        embed.add_field(name="💰 Price", value=f"${collectible['price']:,}", inline=True)
        embed.add_field(name="⭐ Rarity", value=collectible['rarity'].title(), inline=True)
        embed.add_field(name="📂 Category", value=COLLECTIBLE_CATEGORIES[collectible['category']]['name'], inline=True)
        embed.add_field(name="📝 Description", value=collectible['description'], inline=False)
        
        # Check if player can afford it
        player = await db.get_player(str(self.user_id))
        new_balance = player['balance'] - collectible['price']
        
        if new_balance < 0:
            embed.add_field(
                name="⚠️ Warning",
                value=f"❌ Insufficient funds! You need ${collectible['price']:,} but only have ${player['balance']:,}",
                inline=False
            )
            embed.color = discord.Color.red()
            return await interaction.response.edit_message(embed=embed, view=None)
        else:
            embed.add_field(name="💸 New Balance", value=f"${new_balance:,}", inline=False)
        
        embed.set_footer(text="Click the button below to confirm your purchase")
        
        await interaction.response.edit_message(embed=embed, view=confirm_view)


class BuyCollectibleConfirmView(discord.ui.View):
    """View for confirming collectible purchase"""
    def __init__(self, user_id: int, item_id: str, collectible: dict):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.item_id = item_id
        self.collectible = collectible
    
    @discord.ui.button(label="✅ Confirm Purchase", style=discord.ButtonStyle.success)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ This is not your purchase!", ephemeral=True)
        
        await interaction.response.defer()
        
        # Get current player data
        player = await db.get_player(str(self.user_id))
        if not player:
            player = await db.upsert_player(str(self.user_id), interaction.user.name)
        
        # Check if player can afford it
        if player['balance'] < self.collectible['price']:
            return await interaction.followup.send(
                f"❌ Insufficient funds! You need **${self.collectible['price']:,}** but only have **${player['balance']:,}**.",
                ephemeral=True
            )
        
        # Purchase collectible
        await db.update_player_balance(str(self.user_id), -self.collectible['price'])
        await db.add_collectible_to_player(str(self.user_id), self.item_id)
        
        embed = discord.Embed(
            title="✅ Purchase Successful!",
            description=f"You've acquired **{self.collectible['name']}**!",
            color=RARITY_COLORS.get(self.collectible['rarity'], 0x808080)
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name=f"{self.collectible['emoji']} Item", value=self.collectible['name'], inline=True)
        embed.add_field(name="💰 Price", value=f"${self.collectible['price']:,}", inline=True)
        embed.add_field(name="⭐ Rarity", value=self.collectible['rarity'].title(), inline=True)
        embed.add_field(name="📝 Description", value=self.collectible['description'], inline=False)
        embed.set_footer(text=f"New balance: ${player['balance'] - self.collectible['price']:,}")
        
        await interaction.edit_original_response(embed=embed, view=None)
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ This is not your purchase!", ephemeral=True)
        
        await interaction.response.edit_message(content="❌ Purchase cancelled.", embed=None, view=None)


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
                        label=collectible['name'][:100],
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
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
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
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
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
        
        # Register persistent view
        self.bot.add_view(CollectiblesCatalogView())
    
    async def is_admin(self, interaction: discord.Interaction) -> bool:
        """
        Check if user is:
        1. Bot owner (always has access)
        2. Server admin (always has access)
        3. Has an authorized admin role
        """
        if not interaction.guild:
            return False
        
        # Check if user is bot owner
        app_info = interaction.client.application
        is_owner = interaction.user.id == app_info.owner.id if app_info and app_info.owner else False
        
        if is_owner:
            return True
        
        # Check if user has administrator permissions
        is_admin = interaction.user.guild_permissions.administrator
        
        if is_admin:
            return True
        
        # Check if user has an authorized admin role
        settings = await db.get_guild_settings(str(interaction.guild.id))
        if settings and settings.get('admin_role_ids'):
            admin_role_ids = settings['admin_role_ids']
            user_role_ids = [str(role.id) for role in interaction.user.roles]
            
            # Check if user has any of the authorized roles
            if any(role_id in admin_role_ids for role_id in user_role_ids):
                return True
        
        return False
    
    @app_commands.command(name="setup-collectibles-catalog", description="⚙️ Setup collectibles catalog display (Admin only)")
    @app_commands.describe(
        channel="Channel for collectibles catalog display"
    )
    async def setup_collectibles_catalog(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Setup persistent collectibles catalog display"""
        if not await self.is_admin(interaction):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            # Create catalog embed
            embed = create_collectibles_catalog_embed()
            view = CollectiblesCatalogView()
            
            # Send message
            message = await channel.send(embed=embed, view=view)
            
            # Save to database
            await db.set_collectibles_catalog_channel(str(interaction.guild.id), str(channel.id))
            await db.set_collectibles_catalog_message(str(interaction.guild.id), str(message.id))
            
            await interaction.followup.send(f"✅ Collectibles catalog set up in {channel.mention}")
            
        except Exception as e:
            print(f"Error setting up collectibles catalog: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(f"❌ Error setting up collectibles catalog: {e}", ephemeral=True)
    
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
        """Browse collectibles by category with enhanced UI"""
        await interaction.response.defer(ephemeral=True)
        
        items = get_collectibles_by_category(category)
        category_data = COLLECTIBLE_CATEGORIES[category]
        
        if not items:
            return await interaction.followup.send(
                f"No items available in {category_data['name']}.",
                ephemeral=True
            )
        
        embed = discord.Embed(
            title=f"{category_data['emoji']} {category_data['name']}",
            description=f"**{category_data['description']}**\n\n"
                       f"Browse {len(items)} exclusive items in this category.",
            color=discord.Color.blue()
        )
        
        # Show items grouped by rarity
        by_rarity = {}
        for item in items:
            rarity = item['rarity']
            if rarity not in by_rarity:
                by_rarity[rarity] = []
            by_rarity[rarity].append(item)
        
        # Display in rarity order
        rarity_order = ['legendary', 'epic', 'rare', 'uncommon', 'common']
        for rarity in rarity_order:
            if rarity in by_rarity:
                rarity_items = by_rarity[rarity]
                rarity_emoji = {
                    'legendary': '🌟',
                    'epic': '💜',
                    'rare': '💙',
                    'uncommon': '💚',
                    'common': '⚪'
                }.get(rarity, '⚪')
                
                items_text = "\n".join([
                    f"{item['emoji']} **{item['name']}** - ${item['price']:,}"
                    for item in rarity_items
                ])
                
                embed.add_field(
                    name=f"{rarity_emoji} {rarity.title()} ({len(rarity_items)})",
                    value=items_text,
                    inline=False
                )
        
        player = await db.get_player(str(interaction.user.id))
        if player:
            embed.set_footer(text=f"Your balance: ${player['balance']:,} • Use /buy-collectible to purchase")
        else:
            embed.set_footer(text="Use /buy-collectible to purchase items")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="buy-collectible", description="🛍️ Purchase a collectible item")
    @app_commands.describe(
        category="Category to shop from"
    )
    @app_commands.choices(category=[
        app_commands.Choice(name="🚗 Luxury Cars", value="cars"),
        app_commands.Choice(name="✈️ Private Jets", value="planes"),
        app_commands.Choice(name="🏰 Real Estate", value="real_estate"),
        app_commands.Choice(name="🛥️ Yachts & Boats", value="boats"),
        app_commands.Choice(name="💎 Jewelry", value="jewelry"),
        app_commands.Choice(name="🎨 Fine Art", value="art"),
    ])
    async def buy_collectible(self, interaction: discord.Interaction, category: str):
        """Buy a collectible with interactive UI"""
        await interaction.response.defer(ephemeral=True)
        
        # Get player
        player = await db.get_player(str(interaction.user.id))
        if not player:
            player = await db.upsert_player(str(interaction.user.id), interaction.user.name)
        
        items = get_collectibles_by_category(category)
        category_data = COLLECTIBLE_CATEGORIES[category]
        
        if not items:
            return await interaction.followup.send(
                f"No items available in {category_data['name']}.",
                ephemeral=True
            )
        
        # Create view
        view = BuyCollectibleView(interaction.user.id, category, player)
        
        embed = discord.Embed(
            title=f"🛍️ {category_data['emoji']} {category_data['name']} Shop",
            description=f"**{category_data['description']}**\n\n"
                       f"Select an item to purchase from the dropdown below.",
            color=discord.Color.blue()
        )
        embed.add_field(name="💰 Your Balance", value=f"${player['balance']:,}", inline=True)
        embed.add_field(name="📦 Available Items", value=f"{len(items)}", inline=True)
        embed.set_footer(text="Select an item from the dropdown below")
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="my-collection", description="🏆 View your collectibles collection")
    async def my_collection(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
        """View a player's collectibles collection"""
        target_user = user or interaction.user
        
        # Get player's collectibles
        owned_items = await db.get_player_collectibles(str(target_user.id))
        
        if not owned_items:
            if target_user == interaction.user:
                await interaction.response.send_message(
                    "You don't own any collectibles yet! Use `/browse-collectibles` or the catalog buttons to start collecting.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"{target_user.mention} doesn't own any collectibles yet.",
                    ephemeral=True
                )
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
        
        if target_user == interaction.user:
            embed.set_footer(text="Use /sell-collectible to sell items for 80% of their value")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="sell-collectible", description="💵 Sell a collectible from your collection")
    async def sell_collectible(self, interaction: discord.Interaction):
        """Sell a collectible item with interactive dropdown"""
        await interaction.response.defer(ephemeral=True)
        
        # Get player's collectibles
        owned_items = await db.get_player_collectibles(str(interaction.user.id))
        
        if not owned_items:
            return await interaction.followup.send(
                "You don't own any collectibles to sell! Use `/browse-collectibles` to start collecting.",
                ephemeral=True
            )
        
        # Create view
        view = SellCollectibleView(interaction.user.id, owned_items)
        
        total_value = sum(get_collectible_by_id(item['collectible_id'])['price'] for item in owned_items)
        total_sell_value = int(total_value * 0.8)
        
        embed = discord.Embed(
            title="💵 Sell Collectible",
            description=f"You own **{len(owned_items)}** collectible(s) worth **${total_value:,}**.\n"
                       f"Select an item to sell for **80%** of its original value (**${total_sell_value:,}** total).",
            color=discord.Color.blue()
        )
        
        player = await db.get_player(str(interaction.user.id))
        embed.add_field(name="💰 Current Balance", value=f"${player['balance']:,}", inline=False)
        embed.set_footer(text="Select a collectible from the dropdown below")
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="collection-stats", description="📊 View collection statistics")
    async def collection_stats(self, interaction: discord.Interaction):
        """View server-wide collection statistics"""
        stats = await db.get_collectibles_stats()
        
        embed = discord.Embed(
            title="📊 Collection Statistics",
            description="**Server-wide collectibles data**",
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
            if collectible:
                embed.add_field(
                    name="🌟 Most Collected Item",
                    value=f"{collectible['emoji']} {collectible['name']}",
                    inline=False
                )
        
        embed.set_footer(text="Global statistics across all players")
        embed.timestamp = discord.utils.utcnow()
        
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(CollectiblesCommands(bot))
