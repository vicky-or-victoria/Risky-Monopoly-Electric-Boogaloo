# Risky Monopoly Discord Bot - FIXED VERSION
# For the Riskord

import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

import database as db
from events import schedule_income_and_events  # FIXED: Use the new combined scheduler

# Load environment variables
load_dotenv()

# Bot configuration
TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    raise ValueError("DISCORD_TOKEN not found in environment variables")

# Bot intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Create bot instance
class RiskyMonopolyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='rm!',
            intents=intents,
            help_command=None
        )
    
    async def setup_hook(self):
        """Load cogs and sync commands"""
        try:
            print('='*60)
            print('⚙️ SETUP HOOK - Loading cogs and syncing commands')
            print('='*60)
            
            # Load all cogs with individual error handling
            cogs = [
                'admin_commands',
                'company_commands',
                'economy_commands'
            ]
            
            loaded_cogs = []
            failed_cogs = []
            
            for cog in cogs:
                # Try loading from cogs/ folder first, then root
                for path in [f'cogs.{cog}', cog]:
                    try:
                        print(f'📦 Trying to load {path}...')
                        await self.load_extension(path)
                        loaded_cogs.append(path)
                        print(f'   ✅ {path} loaded successfully')
                        break
                    except commands.ExtensionNotFound:
                        continue
                    except Exception as e:
                        failed_cogs.append((path, e))
                        print(f'   ❌ Failed to load {path}: {e}')
                        import traceback
                        traceback.print_exc()
                        break
            
            print('='*60)
            print(f'📊 Cog Loading Summary:')
            print(f'   ✅ Loaded: {len(loaded_cogs)}/{len(cogs)}')
            print(f'   ❌ Failed: {len(failed_cogs)}/{len(cogs)}')
            
            if failed_cogs:
                print('   Failed cogs:')
                for cog, error in failed_cogs:
                    print(f'      - {cog}: {error}')
            
            if not loaded_cogs:
                print('   ⚠️  WARNING: No cogs loaded! Bot will have no commands!')
            
            print('='*60)
            
            # Sync commands globally
            try:
                print('🔄 Syncing slash commands globally...')
                synced = await self.tree.sync()
                print(f'✅ Successfully synced {len(synced)} global commands')
                
                if len(synced) == 0:
                    print('   ⚠️  WARNING: No commands to sync! Check cog loading.')
            except Exception as e:
                print(f'❌ Failed to sync commands globally: {e}')
                import traceback
                traceback.print_exc()
            
            print('='*60)
            
        except Exception as e:
            print('='*60)
            print(f'❌ CRITICAL ERROR in setup_hook: {e}')
            import traceback
            traceback.print_exc()
            print('='*60)
    
    async def on_ready(self):
        """Called when bot is ready"""
        print(f'✅ Bot logged in as {self.user} (ID: {self.user.id})')
        print(f'Connected to {len(self.guilds)} guild(s)')
        
        # Initialize auto-update system
        try:
            import auto_updates
            auto_updates.set_bot_instance(self)
            print('✅ Auto-update system initialized')
        except Exception as e:
            print(f'⚠️ Failed to initialize auto-update system: {e}')
        
        # FIXED: Schedule the combined income generation AND event system
        try:
            schedule_income_and_events(self)
            print('✅ Income generation system started (every 30 seconds)')
            print('✅ Event modification system started (checks based on guild frequency)')
        except Exception as e:
            print(f'⚠️ Failed to start income/event system: {e}')
            import traceback
            traceback.print_exc()
        
        # Check for overdue loans every hour
        async def check_overdue_loans():
            await self.wait_until_ready()
            while not self.is_closed():
                try:
                    overdue_loans = await db.get_overdue_loans()
                    
                    for loan in overdue_loans:
                        await apply_loan_penalty(self, loan)
                        
                except Exception as e:
                    print(f"Error checking overdue loans: {e}")
                
                await asyncio.sleep(3600)
        
        self.loop.create_task(check_overdue_loans())
        print('✅ Loan penalty checker started')
        
        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="companies grow 📈"
            )
        )
        
        print('✅ Bot is ready!')
    
    async def on_message(self, message):
        """Handle messages - delete non-owner messages in company threads"""
        if message.author.bot:
            return
        
        if isinstance(message.channel, discord.Thread):
            company = await db.get_company_by_thread(str(message.channel.id))
            
            if company:
                if str(message.author.id) != company['owner_id']:
                    try:
                        await message.delete()
                        try:
                            await message.channel.send(
                                f"⚠️ {message.author.mention}, only the company owner can post in this thread.",
                                delete_after=5
                            )
                        except:
                            pass
                    except discord.errors.NotFound:
                        pass
                    except Exception as e:
                        print(f"Error deleting message: {e}")
                    return
        
        await self.process_commands(message)

async def main():
    """Main entry point"""
    try:
        print('='*60)
        print('🚀 RISKY MONOPOLY BOT - STARTING UP (FIXED VERSION)')
        print('='*60)
        
        print('🔍 Checking environment variables...')
        token = os.getenv('DISCORD_TOKEN')
        db_url = os.getenv('DATABASE_URL')
        
        if not token:
            print('❌ FATAL ERROR: DISCORD_TOKEN not found!')
            return
        
        if not db_url:
            print('❌ FATAL ERROR: DATABASE_URL not found!')
            return
        
        print('✅ Environment variables found')
        
        print('='*60)
        print('💾 Initializing database connection...')
        try:
            await db.init_database()
            print('✅ Database initialized successfully')
        except Exception as e:
            print(f'❌ FATAL ERROR: Failed to initialize database!')
            print(f'   Error: {e}')
            import traceback
            traceback.print_exc()
            return
        
        print('='*60)
        
        print('🤖 Creating bot instance...')
        try:
            bot = RiskyMonopolyBot()
            print('✅ Bot instance created')
        except Exception as e:
            print(f'❌ FATAL ERROR: Failed to create bot!')
            print(f'   Error: {e}')
            await db.close_database()
            return
        
        print('='*60)
        print('🔌 Connecting to Discord...')
        try:
            await bot.start(TOKEN)
        except KeyboardInterrupt:
            print('\n⚠️ Bot stopped by user (Ctrl+C)')
        except discord.LoginFailure:
            print('❌ FATAL ERROR: Invalid Discord token!')
        except Exception as e:
            print(f'❌ FATAL ERROR: Bot crashed!')
            print(f'   Error: {e}')
            import traceback
            traceback.print_exc()
        finally:
            print('='*60)
            print('🧹 Cleaning up...')
            try:
                await db.close_database()
                print('✅ Database connection closed')
            except Exception as e:
                print(f'⚠️ Error closing database: {e}')
            
            try:
                await bot.close()
                print('✅ Bot connection closed')
            except Exception as e:
                print(f'⚠️ Error closing bot: {e}')
            
            print('='*60)
            print('👋 Bot shutdown complete')
            print('='*60)
            
    except Exception as e:
        print('='*60)
        print('❌ CATASTROPHIC ERROR!')
        print(f'   Error: {e}')
        import traceback
        traceback.print_exc()
        print('='*60)

async def apply_loan_penalty(bot: commands.Bot, loan: dict):
    """Apply penalty for overdue loan"""
    try:
        player = await db.get_player(loan['borrower_id'])
        
        if loan['company_id']:
            company = await db.get_company_by_id(loan['company_id'])
            
            if company:
                await db.delete_company(loan['company_id'])
                
                if company['thread_id']:
                    try:
                        thread = bot.get_channel(int(company['thread_id']))
                        if not thread:
                            thread = await bot.fetch_channel(int(company['thread_id']))
                        
                        if thread:
                            embed = discord.Embed(
                                title="🏦 COMPANY LIQUIDATED",
                                description=(
                                    f"Due to failure to repay Loan #{loan['id']}, "
                                    f"**{company['name']}** has been liquidated by the bank."
                                ),
                                color=discord.Color.red()
                            )
                            embed.add_field(name="💰 Loan Amount", value=f"${loan['total_owed']:,}", inline=True)
                            embed.timestamp = discord.utils.utcnow()
                            
                            await thread.send(embed=embed)
                            await thread.edit(archived=True, locked=True)
                    except Exception as e:
                        print(f"Error notifying company liquidation: {e}")
        else:
            penalty = min(loan['total_owed'], player['balance'])
            await db.update_player_balance(loan['borrower_id'], -penalty)
            
            try:
                user = bot.get_user(int(loan['borrower_id']))
                if not user:
                    user = await bot.fetch_user(int(loan['borrower_id']))
                
                if user:
                    embed = discord.Embed(
                        title="⚠️ LOAN PENALTY APPLIED",
                        description=(
                            f"Due to failure to repay Loan #{loan['id']}, "
                            f"${penalty:,} has been seized from your account."
                        ),
                        color=discord.Color.red()
                    )
                    embed.add_field(name="💰 Total Owed", value=f"${loan['total_owed']:,}", inline=True)
                    embed.add_field(name="💵 Amount Seized", value=f"${penalty:,}", inline=True)
                    embed.timestamp = discord.utils.utcnow()
                    
                    await user.send(embed=embed)
            except Exception as e:
                print(f"Error notifying user of penalty: {e}")
        
        await db.pay_loan(loan['id'])
        
    except Exception as e:
        print(f"Error applying loan penalty: {e}")

if __name__ == '__main__':
    asyncio.run(main())
