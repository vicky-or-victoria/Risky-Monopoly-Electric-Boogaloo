# Stock market trading commands

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

import database as db
from stock_market import STOCK_COMPANIES, create_stock_market_embed


class StockSharesModal(discord.ui.Modal, title="Enter Number of Shares"):
    """Modal for entering the number of shares to buy/sell"""
    shares = discord.ui.TextInput(
        label="Number of Shares",
        placeholder="Enter number of shares (e.g., 100)",
        required=True,
        min_length=1,
        max_length=10
    )
    
    def __init__(self, symbol: str, action: str, max_shares: int = None, cog=None):
        super().__init__()
        self.symbol = symbol
        self.action = action  # "buy" or "sell"
        self.max_shares = max_shares
        self.cog = cog
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            shares_count = int(self.shares.value)
            
            if shares_count <= 0:
                return await interaction.response.send_message(
                    "❌ Number of shares must be positive!",
                    ephemeral=True
                )
            
            if self.action == "buy":
                await self._process_buy(interaction, shares_count)
            elif self.action == "sell":
                if self.max_shares and shares_count > self.max_shares:
                    return await interaction.response.send_message(
                        f"❌ You only own {self.max_shares} shares of {self.symbol}!",
                        ephemeral=True
                    )
                await self._process_sell(interaction, shares_count)
        
        except ValueError:
            await interaction.response.send_message(
                "❌ Please enter a valid number!",
                ephemeral=True
            )
    
    async def _process_buy(self, interaction: discord.Interaction, shares: int):
        """Process stock purchase"""
        await interaction.response.defer()
        
        # Get player
        player = await db.get_player(str(interaction.user.id))
        
        # Get current stock price
        current_price = await db.get_stock_price(self.symbol)
        if current_price is None:
            return await interaction.followup.send("❌ Stock not found.", ephemeral=True)
        
        # Calculate total cost
        total_cost = current_price * shares
        
        # Check balance
        if player['balance'] < total_cost:
            return await interaction.followup.send(
                f"❌ Insufficient funds! You need **${total_cost:,}** but only have **${player['balance']:,}**.",
                ephemeral=True
            )
        
        # Execute purchase
        await db.update_player_balance(str(interaction.user.id), -total_cost)
        await db.add_stock_to_portfolio(str(interaction.user.id), self.symbol, shares, current_price)
        
        stock_data = STOCK_COMPANIES[self.symbol]
        
        embed = discord.Embed(
            title="✅ Stock Purchase Successful",
            description=f"You've purchased **{shares}** shares of **{self.symbol}**",
            color=discord.Color.green()
        )
        embed.add_field(name=f"{stock_data['emoji']} Company", value=stock_data['name'], inline=True)
        embed.add_field(name="💵 Price per Share", value=f"${current_price:,}", inline=True)
        embed.add_field(name="📊 Total Shares", value=f"{shares}", inline=True)
        embed.add_field(name="💰 Total Cost", value=f"${total_cost:,}", inline=True)
        embed.set_footer(text=f"New balance: ${player['balance'] - total_cost:,}")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def _process_sell(self, interaction: discord.Interaction, shares: int):
        """Process stock sale"""
        await interaction.response.defer()
        
        # Get player's holdings
        holdings = await db.get_player_stock_holdings(str(interaction.user.id), self.symbol)
        
        if not holdings or holdings['shares'] < shares:
            return await interaction.followup.send(
                f"❌ You don't have enough shares! You own {holdings['shares'] if holdings else 0} shares of {self.symbol}.",
                ephemeral=True
            )
        
        # Get current stock price
        current_price = await db.get_stock_price(self.symbol)
        
        # Calculate sale value
        sale_value = current_price * shares
        
        # Calculate profit/loss
        avg_buy_price = holdings['average_price']
        profit_loss = (current_price - avg_buy_price) * shares
        
        # Execute sale
        await db.remove_stock_from_portfolio(str(interaction.user.id), self.symbol, shares)
        await db.update_player_balance(str(interaction.user.id), sale_value)
        
        player = await db.get_player(str(interaction.user.id))
        stock_data = STOCK_COMPANIES[self.symbol]
        
        embed = discord.Embed(
            title="✅ Stock Sale Successful",
            description=f"You've sold **{shares}** shares of **{self.symbol}**",
            color=discord.Color.green() if profit_loss >= 0 else discord.Color.red()
        )
        embed.add_field(name=f"{stock_data['emoji']} Company", value=stock_data['name'], inline=True)
        embed.add_field(name="💵 Sale Price per Share", value=f"${current_price:,}", inline=True)
        embed.add_field(name="📊 Shares Sold", value=f"{shares}", inline=True)
        embed.add_field(name="💰 Total Sale Value", value=f"${sale_value:,}", inline=True)
        embed.add_field(
            name="📈 Profit/Loss",
            value=f"+${profit_loss:,}" if profit_loss >= 0 else f"-${abs(profit_loss):,}",
            inline=True
        )
        embed.set_footer(text=f"New balance: ${player['balance']:,}")
        
        await interaction.followup.send(embed=embed, ephemeral=True)


class BuyStockView(discord.ui.View):
    """View for selecting which stock to buy"""
    def __init__(self, user_id: int, player: dict, current_prices: dict, cog):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.player = player
        self.current_prices = current_prices
        self.cog = cog
        
        # Create select menu for stocks
        options = []
        for symbol, data in STOCK_COMPANIES.items():
            price = current_prices.get(symbol, data['initial_price'])
            
            options.append(
                discord.SelectOption(
                    label=f"{symbol} - ${price:,}/share",
                    description=data['name'][:100],
                    value=symbol,
                    emoji=data['emoji']
                )
            )
        
        select = discord.ui.Select(
            placeholder="Choose a stock to buy...",
            min_values=1,
            max_values=1,
            options=options
        )
        select.callback = self.stock_selected
        self.add_item(select)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ This is not your stock menu!",
                ephemeral=True
            )
            return False
        return True
    
    async def stock_selected(self, interaction: discord.Interaction):
        """Handle stock selection and show shares modal"""
        symbol = interaction.data['values'][0]
        modal = StockSharesModal(symbol, "buy", cog=self.cog)
        await interaction.response.send_modal(modal)


class SellStockView(discord.ui.View):
    """View for selecting which stock to sell"""
    def __init__(self, user_id: int, portfolio: list, cog):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.portfolio = portfolio
        self.cog = cog
        
        # Create select menu for owned stocks
        options = []
        for holding in portfolio[:25]:  # Discord limit
            symbol = holding['symbol']
            stock_data = STOCK_COMPANIES[symbol]
            
            shares = holding['shares']
            avg_price = holding['average_price']
            
            options.append(
                discord.SelectOption(
                    label=f"{symbol} - {shares} shares",
                    description=f"{stock_data['name']} | Avg: ${avg_price:,}/share",
                    value=symbol,
                    emoji=stock_data['emoji']
                )
            )
        
        select = discord.ui.Select(
            placeholder="Choose a stock to sell...",
            min_values=1,
            max_values=1,
            options=options
        )
        select.callback = self.stock_selected
        self.add_item(select)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ This is not your stock menu!",
                ephemeral=True
            )
            return False
        return True
    
    async def stock_selected(self, interaction: discord.Interaction):
        """Handle stock selection and show shares modal"""
        symbol = interaction.data['values'][0]
        
        # Get max shares for this stock
        holding = next((h for h in self.portfolio if h['symbol'] == symbol), None)
        max_shares = holding['shares'] if holding else 0
        
        modal = StockSharesModal(symbol, "sell", max_shares=max_shares, cog=self.cog)
        await interaction.response.send_modal(modal)


class StockCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def is_admin(self, interaction: discord.Interaction) -> bool:
        """Check if user is bot owner, server owner, or has admin role"""
        # Check if user is bot owner
        app_info = interaction.client.application
        is_bot_owner = interaction.user.id == app_info.owner.id if app_info and app_info.owner else False
        
        if is_bot_owner:
            return True
        
        # Check if user is server owner
        if interaction.user.id == interaction.guild.owner_id:
            return True
        
        # Check if user has administrator permissions
        if interaction.user.guild_permissions.administrator:
            return True
        
        # Check if user has an authorized admin role
        settings = await db.get_guild_settings(str(interaction.guild.id))
        if settings and settings.get('admin_role_ids'):
            admin_role_ids = settings['admin_role_ids']
            user_role_ids = [str(role.id) for role in interaction.user.roles]
            
            if any(role_id in admin_role_ids for role_id in user_role_ids):
                return True
        
        return False
    
    @app_commands.command(name="stock-market", description="📊 View the current stock market")
    async def stock_market(self, interaction: discord.Interaction):
        """Display current stock market prices"""
        # Get current prices
        current_prices = await db.get_all_stock_prices()
        
        updates = []
        for symbol, data in STOCK_COMPANIES.items():
            current_price = current_prices.get(symbol, data['initial_price'])
            
            # Get price history to show change
            history = await db.get_stock_price_history(symbol, limit=2)
            
            if len(history) >= 2:
                old_price = history[1]['price']
                change = current_price - old_price
                change_percent = ((current_price - old_price) / old_price) * 100
            else:
                old_price = current_price
                change = 0
                change_percent = 0
            
            updates.append({
                'symbol': symbol,
                'old_price': old_price,
                'new_price': current_price,
                'change': change,
                'change_percent': change_percent
            })
        
        embed = create_stock_market_embed(updates)
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="buy-stock", description="📈 Buy shares of a stock")
    async def buy_stock_interactive(self, interaction: discord.Interaction):
        """Buy stock shares with interactive dropdown and modal"""
        await interaction.response.defer(ephemeral=True)
        
        # Get player
        player = await db.get_player(str(interaction.user.id))
        if not player:
            player = await db.upsert_player(str(interaction.user.id), interaction.user.name)
        
        # Get current prices
        current_prices = {}
        for symbol in STOCK_COMPANIES.keys():
            current_prices[symbol] = await db.get_stock_price(symbol)
        
        # Create view
        view = BuyStockView(interaction.user.id, player, current_prices, self)
        
        embed = discord.Embed(
            title="📈 Buy Stock",
            description="Select a stock to purchase shares:",
            color=discord.Color.blue()
        )
        embed.add_field(name="💰 Your Balance", value=f"${player['balance']:,}", inline=False)
        embed.set_footer(text="Select a stock from the dropdown below")
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="sell-stock", description="📉 Sell shares of a stock")
    async def sell_stock_interactive(self, interaction: discord.Interaction):
        """Sell stock shares with interactive dropdown and modal"""
        await interaction.response.defer(ephemeral=True)
        
        # Get player's portfolio
        portfolio = await db.get_player_portfolio(str(interaction.user.id))
        
        if not portfolio:
            return await interaction.followup.send(
                "You don't own any stocks to sell! Use `/buy-stock` to start investing.",
                ephemeral=True
            )
        
        # Create view
        view = SellStockView(interaction.user.id, portfolio, self)
        
        player = await db.get_player(str(interaction.user.id))
        
        embed = discord.Embed(
            title="📉 Sell Stock",
            description="Select a stock to sell shares:",
            color=discord.Color.red()
        )
        embed.add_field(name="💰 Your Balance", value=f"${player['balance']:,}", inline=False)
        embed.set_footer(text="Select a stock from the dropdown below")
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="portfolio", description="💼 View your stock portfolio")
    async def portfolio(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
        """View stock portfolio"""
        target_user = user or interaction.user
        
        # Get portfolio
        portfolio = await db.get_player_portfolio(str(target_user.id))
        
        if not portfolio:
            if target_user == interaction.user:
                await interaction.response.send_message("You don't own any stocks yet! Use `/buy-stock` to start investing.", ephemeral=True)
            else:
                await interaction.response.send_message(f"{target_user.mention} doesn't own any stocks yet.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"💼 {target_user.name}'s Portfolio",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=target_user.display_avatar.url)
        
        total_value = 0
        total_invested = 0
        
        for holding in portfolio:
            symbol = holding['symbol']
            stock_data = STOCK_COMPANIES[symbol]
            current_price = await db.get_stock_price(symbol)
            
            shares = holding['shares']
            avg_price = holding['average_price']
            
            current_value = current_price * shares
            invested = avg_price * shares
            profit_loss = current_value - invested
            profit_loss_percent = ((current_price - avg_price) / avg_price) * 100
            
            total_value += current_value
            total_invested += invested
            
            pl_indicator = "📈" if profit_loss >= 0 else "📉"
            pl_str = f"+${profit_loss:,} (+{profit_loss_percent:.2f}%)" if profit_loss >= 0 else f"-${abs(profit_loss):,} ({profit_loss_percent:.2f}%)"
            
            embed.add_field(
                name=f"{stock_data['emoji']} {symbol} - {shares} shares",
                value=f"Current: ${current_price:,}/share\nValue: ${current_value:,}\n{pl_indicator} {pl_str}",
                inline=True
            )
        
        total_pl = total_value - total_invested
        total_pl_percent = ((total_value - total_invested) / total_invested) * 100 if total_invested > 0 else 0
        
        embed.add_field(
            name="📊 Portfolio Summary",
            value=f"**Total Value:** ${total_value:,}\n**Total Invested:** ${total_invested:,}\n**Total P/L:** {'+' if total_pl >= 0 else ''}{total_pl:,} ({total_pl_percent:+.2f}%)",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="setup-stock-market", description="⚙️ Setup stock market display (Admin only)")
    @app_commands.describe(
        channel="Channel for stock market display"
    )
    async def setup_stock_market(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Setup persistent stock market display"""
        if not await self.is_admin(interaction):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Create initial embed
        embed = create_stock_market_embed()
        message = await channel.send(embed=embed)
        
        # Save to database
        await db.set_stock_market_channel(str(interaction.guild.id), str(channel.id))
        await db.set_stock_market_message(str(interaction.guild.id), str(message.id))
        
        await interaction.followup.send(f"✅ Stock market display set up in {channel.mention}")
    
    @app_commands.command(name="set-stock-update-interval", description="⚙️ Set stock update interval (Admin only)")
    @app_commands.describe(
        minutes="Minutes between stock updates (1-60)"
    )
    async def set_stock_interval(self, interaction: discord.Interaction, minutes: app_commands.Range[int, 1, 60]):
        """Set stock market update interval"""
        if not await self.is_admin(interaction):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return
        
        await db.set_stock_update_interval(str(interaction.guild.id), minutes)
        
        embed = discord.Embed(
            title="✅ Stock Update Interval Set",
            description=f"Stocks will now update every **{minutes}** minute(s)",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(StockCommands(bot))
