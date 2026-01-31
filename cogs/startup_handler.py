# Bot startup handler - Ensures persistent displays are restored after redeployment

import discord
from discord.ext import commands


class StartupHandler(commands.Cog):
    """Handles bot startup tasks to restore persistent displays"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Called when bot is ready - restore all persistent displays"""
        if not hasattr(self, '_startup_complete'):
            self._startup_complete = False
        
        # Only run once per bot session
        if self._startup_complete:
            return
        
        print("🔄 Bot restarted - Restoring persistent displays...")
        
        # Re-register all persistent views
        await self.register_persistent_views()
        
        # Restore leaderboards for all guilds
        await self.restore_leaderboards()
        
        # Restore stock market displays
        await self.restore_stock_markets()
        
        # Restore collectibles catalogs
        await self.restore_collectibles_catalogs()
        
        self._startup_complete = True
        print("✅ All persistent displays restored successfully!")
    
    async def register_persistent_views(self):
        """Re-register all persistent views with the bot"""
        try:
            # Import the view classes
            from cogs.stock_commands import StockMarketView
            from cogs.collectibles_commands import CollectiblesCatalogView
            
            # Register persistent views
            self.bot.add_view(StockMarketView())
            self.bot.add_view(CollectiblesCatalogView())
            
            print("✅ Persistent views registered")
        except Exception as e:
            print(f"⚠️ Error registering persistent views: {e}")
    
    async def restore_leaderboards(self):
        """Restore leaderboard displays for all guilds"""
        try:
            import database as db
            
            # Get all guilds
            for guild in self.bot.guilds:
                try:
                    settings = await db.get_guild_settings(str(guild.id))
                    
                    if not settings or not settings.get('leaderboard_channel_id'):
                        continue
                    
                    channel_id = settings.get('leaderboard_channel_id')
                    message_id = settings.get('leaderboard_message_id')
                    
                    if not channel_id:
                        continue
                    
                    channel = guild.get_channel(int(channel_id))
                    if not channel:
                        print(f"⚠️ Leaderboard channel not found in {guild.name}")
                        continue
                    
                    # If message exists, update it; otherwise create new
                    if message_id:
                        try:
                            message = await channel.fetch_message(int(message_id))
                            # Message exists, update it
                            leaderboard_cog = self.bot.get_cog('LeaderboardCommands')
                            if leaderboard_cog:
                                await leaderboard_cog.update_persistent_leaderboard(str(guild.id))
                                print(f"✅ Restored leaderboard in {guild.name}")
                        except discord.NotFound:
                            # Message deleted, create new one
                            leaderboard_cog = self.bot.get_cog('LeaderboardCommands')
                            if leaderboard_cog:
                                await leaderboard_cog.update_persistent_leaderboard(str(guild.id))
                                print(f"✅ Created new leaderboard in {guild.name}")
                    else:
                        # No message ID, create new
                        leaderboard_cog = self.bot.get_cog('LeaderboardCommands')
                        if leaderboard_cog:
                            await leaderboard_cog.update_persistent_leaderboard(str(guild.id))
                            print(f"✅ Created leaderboard in {guild.name}")
                
                except Exception as e:
                    print(f"⚠️ Error restoring leaderboard for {guild.name}: {e}")
                    continue
        
        except Exception as e:
            print(f"⚠️ Error in restore_leaderboards: {e}")
    
    async def restore_stock_markets(self):
        """Restore stock market displays for all guilds"""
        try:
            import database as db
            from stock_market import STOCK_COMPANIES, create_stock_market_embed
            from cogs.stock_commands import StockMarketView
            
            for guild in self.bot.guilds:
                try:
                    settings = await db.get_guild_settings(str(guild.id))
                    
                    if not settings or not settings.get('stock_market_channel_id'):
                        continue
                    
                    channel_id = settings.get('stock_market_channel_id')
                    message_id = settings.get('stock_market_message_id')
                    
                    if not channel_id:
                        continue
                    
                    channel = guild.get_channel(int(channel_id))
                    if not channel:
                        print(f"⚠️ Stock market channel not found in {guild.name}")
                        continue
                    
                    # Get current stock prices
                    updates = []
                    for symbol, data in STOCK_COMPANIES.items():
                        current_price = await db.get_stock_price(symbol)
                        if current_price is None:
                            current_price = data['initial_price']
                        
                        # Get price history
                        history = await db.get_stock_price_history(symbol, limit=2)
                        if len(history) >= 2:
                            old_price = history[1]['new_price']
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
                    view = StockMarketView()
                    
                    # Try to update existing message
                    if message_id:
                        try:
                            message = await channel.fetch_message(int(message_id))
                            await message.edit(embed=embed, view=view)
                            print(f"✅ Restored stock market display in {guild.name}")
                        except discord.NotFound:
                            # Message deleted, create new one
                            message = await channel.send(embed=embed, view=view)
                            await db.set_stock_market_message(str(guild.id), str(message.id))
                            print(f"✅ Created new stock market display in {guild.name}")
                    else:
                        # No message ID, create new
                        message = await channel.send(embed=embed, view=view)
                        await db.set_stock_market_message(str(guild.id), str(message.id))
                        print(f"✅ Created stock market display in {guild.name}")
                
                except Exception as e:
                    print(f"⚠️ Error restoring stock market for {guild.name}: {e}")
                    continue
        
        except Exception as e:
            print(f"⚠️ Error in restore_stock_markets: {e}")
    
    async def restore_collectibles_catalogs(self):
        """Restore collectibles catalog displays for all guilds"""
        try:
            import database as db
            from cogs.collectibles_commands import create_collectibles_catalog_embed, CollectiblesCatalogView
            
            for guild in self.bot.guilds:
                try:
                    settings = await db.get_guild_settings(str(guild.id))
                    
                    if not settings or not settings.get('collectibles_catalog_channel_id'):
                        continue
                    
                    channel_id = settings.get('collectibles_catalog_channel_id')
                    message_id = settings.get('collectibles_catalog_message_id')
                    
                    if not channel_id:
                        continue
                    
                    channel = guild.get_channel(int(channel_id))
                    if not channel:
                        print(f"⚠️ Collectibles catalog channel not found in {guild.name}")
                        continue
                    
                    # Create catalog embed
                    embed = create_collectibles_catalog_embed()
                    view = CollectiblesCatalogView()
                    
                    # Try to update existing message
                    if message_id:
                        try:
                            message = await channel.fetch_message(int(message_id))
                            await message.edit(embed=embed, view=view)
                            print(f"✅ Restored collectibles catalog in {guild.name}")
                        except discord.NotFound:
                            # Message deleted, create new one
                            message = await channel.send(embed=embed, view=view)
                            await db.set_collectibles_catalog_message(str(guild.id), str(message.id))
                            print(f"✅ Created new collectibles catalog in {guild.name}")
                    else:
                        # No message ID, create new
                        message = await channel.send(embed=embed, view=view)
                        await db.set_collectibles_catalog_message(str(guild.id), str(message.id))
                        print(f"✅ Created collectibles catalog in {guild.name}")
                
                except Exception as e:
                    print(f"⚠️ Error restoring collectibles catalog for {guild.name}: {e}")
                    continue
        
        except Exception as e:
            print(f"⚠️ Error in restore_collectibles_catalogs: {e}")


async def setup(bot):
    await bot.add_cog(StartupHandler(bot))
