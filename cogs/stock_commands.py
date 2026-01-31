# Stock market trading commands

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

import database as db
from stock_market import STOCK_COMPANIES, create_stock_market_embed

class StockCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def is_admin(self, interaction: discord.Interaction) -> bool:
        """Check if user is server owner or has admin role"""
        if interaction.user.id == interaction.guild.owner_id:
            return True
        
        admin_roles = await db.get_admin_roles(str(interaction.guild.id))
        user_role_ids = [str(role.id) for role in interaction.user.roles]
        
        return any(role_id in admin_roles for role_id in user_role_ids)
    
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
    @app_commands.describe(
        symbol="Stock symbol (e.g., TECH, AUTO)",
        shares="Number of shares to buy"
    )
    @app_commands.choices(symbol=[
        app_commands.Choice(name=f"{data['emoji']} {symbol} - {data['name']}", value=symbol)
        for symbol, data in STOCK_COMPANIES.items()
    ])
    async def buy_stock(self, interaction: discord.Interaction, symbol: str, shares: app_commands.Range[int, 1, 10000]):
        """Buy stock shares"""
        await interaction.response.defer()
        
        # Get player
        player = await db.get_player(str(interaction.user.id))
        if not player:
            player = await db.upsert_player(str(interaction.user.id), interaction.user.name)
        
        # Get current stock price
        current_price = await db.get_stock_price(symbol)
        if current_price is None:
            await interaction.followup.send("❌ Stock not found.", ephemeral=True)
            return
        
        # Calculate total cost
        total_cost = current_price * shares
        
        # Check balance
        if player['balance'] < total_cost:
            await interaction.followup.send(
                f"❌ Insufficient funds! You need **${total_cost:,}** but only have **${player['balance']:,}**.",
                ephemeral=True
            )
            return
        
        # Execute purchase
        await db.update_player_balance(str(interaction.user.id), -total_cost)
        await db.add_stock_to_portfolio(str(interaction.user.id), symbol, shares, current_price)
        
        stock_data = STOCK_COMPANIES[symbol]
        
        embed = discord.Embed(
            title="✅ Stock Purchase Successful",
            description=f"You've purchased **{shares}** shares of **{symbol}**",
            color=discord.Color.green()
        )
        embed.add_field(name=f"{stock_data['emoji']} Company", value=stock_data['name'], inline=True)
        embed.add_field(name="💵 Price per Share", value=f"${current_price:,}", inline=True)
        embed.add_field(name="📊 Total Shares", value=f"{shares}", inline=True)
        embed.add_field(name="💰 Total Cost", value=f"${total_cost:,}", inline=True)
        embed.set_footer(text=f"New balance: ${player['balance'] - total_cost:,}")
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="sell-stock", description="📉 Sell shares of a stock")
    @app_commands.describe(
        symbol="Stock symbol (e.g., TECH, AUTO)",
        shares="Number of shares to sell (or 'all')"
    )
    @app_commands.choices(symbol=[
        app_commands.Choice(name=f"{data['emoji']} {symbol} - {data['name']}", value=symbol)
        for symbol, data in STOCK_COMPANIES.items()
    ])
    async def sell_stock(self, interaction: discord.Interaction, symbol: str, shares: app_commands.Range[int, 1, 10000]):
        """Sell stock shares"""
        await interaction.response.defer()
        
        # Get player's holdings
        holdings = await db.get_player_stock_holdings(str(interaction.user.id), symbol)
        
        if not holdings or holdings['shares'] < shares:
            await interaction.followup.send(
                f"❌ You don't have enough shares! You own {holdings['shares'] if holdings else 0} shares of {symbol}.",
                ephemeral=True
            )
            return
        
        # Get current stock price
        current_price = await db.get_stock_price(symbol)
        
        # Calculate sale value
        sale_value = current_price * shares
        
        # Calculate profit/loss
        avg_buy_price = holdings['average_price']
        profit_loss = (current_price - avg_buy_price) * shares
        
        # Execute sale
        await db.remove_stock_from_portfolio(str(interaction.user.id), symbol, shares)
        await db.update_player_balance(str(interaction.user.id), sale_value)
        
        player = await db.get_player(str(interaction.user.id))
        stock_data = STOCK_COMPANIES[symbol]
        
        embed = discord.Embed(
            title="✅ Stock Sale Successful",
            description=f"You've sold **{shares}** shares of **{symbol}**",
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
        
        await interaction.followup.send(embed=embed)
    
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
