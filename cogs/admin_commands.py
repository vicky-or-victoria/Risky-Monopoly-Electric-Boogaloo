# Leaderboard and Admin commands

import discord
from discord import app_commands
from discord.ext import commands
import os

import database as db
from events import trigger_daily_events

class LeaderboardCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_command(name="leaderboard", description="View the wealth leaderboard")
    async def leaderboard(self, ctx: commands.Context, page: int = 1):
        """View the wealth leaderboard
        
        Parameters
        -----------
        page: int
            Page number to view (optional, defaults to 1)
        """
        # Validate page number
        if page < 1:
            page = 1
        
        # Show paginated leaderboard (all players)
        await self.show_leaderboard_page(ctx, page=page - 1, is_initial=True)
    
    async def show_leaderboard_page(self, ctx: commands.Context, page: int = 0, is_initial: bool = False):
        players_per_page = 10
        offset = page * players_per_page
        
        players = await db.get_top_players(limit=players_per_page, offset=offset)
        total_players = await db.get_total_player_count()
        total_pages = (total_players + players_per_page - 1) // players_per_page
        
        # If page is out of range, show last page
        if page >= total_pages and total_pages > 0:
            page = total_pages - 1
            offset = page * players_per_page
            players = await db.get_top_players(limit=players_per_page, offset=offset)
        
        if not players:
            embed = discord.Embed(
                title="💰 Wealth Leaderboard",
                description="No players with balance yet!",
                color=discord.Color.gold()
            )
            if is_initial:
                return await ctx.send(embed=embed)
            else:
                # For button interactions
                if isinstance(ctx, discord.Interaction):
                    return await ctx.response.edit_message(embed=embed, view=None)
                return await ctx.send(embed=embed)
        
        # Build leaderboard text
        leaderboard_text = "```\n"
        for player in players:
            rank = player['rank']
            medal = self.get_medal_emoji(rank)
            username = player['username'][:20].ljust(20)
            balance = f"${player['balance']:,}"
            leaderboard_text += f"{medal} #{str(rank).rjust(3)} | {username} | {balance}\n"
        leaderboard_text += "```"
        
        # Calculate rank range for this page
        start_rank = offset + 1
        end_rank = min(offset + len(players), total_players)
        
        embed = discord.Embed(
            title="💰 Wealth Leaderboard",
            description=f"Showing ranks {start_rank}-{end_rank} of {total_players} players\n{leaderboard_text}",
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"Page {page + 1} of {total_pages if total_pages > 0 else 1} • Use buttons to navigate all pages")
        embed.timestamp = discord.utils.utcnow()
        
        # Create navigation buttons
        view = LeaderboardView(page, total_pages)
        
        if is_initial:
            await ctx.send(embed=embed, view=view)
        else:
            # For button interactions
            if isinstance(ctx, discord.Interaction):
                await ctx.response.edit_message(embed=embed, view=view)
            else:
                await ctx.send(embed=embed, view=view)
    
    def get_medal_emoji(self, rank: int) -> str:
        if rank == 1:
            return "🥇"
        elif rank == 2:
            return "🥈"
        elif rank == 3:
            return "🥉"
        else:
            return "  "
    
    async def update_persistent_leaderboard(self, guild_id: str):
        """Update the persistent leaderboard message"""
        try:
            settings = await db.get_guild_settings(guild_id)
            
            if not settings or not settings.get('leaderboard_channel_id'):
                return
            
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                print(f"Guild {guild_id} not found for leaderboard update")
                return
            
            channel = guild.get_channel(int(settings['leaderboard_channel_id']))
            if not channel:
                print(f"Channel {settings['leaderboard_channel_id']} not found for leaderboard update")
                return
            
            # Get top 25 players for persistent leaderboard
            players = await db.get_top_players(limit=25, offset=0)
            
            if not players:
                leaderboard_text = "No players with balance yet!"
            else:
                leaderboard_text = "```\n"
                for player in players:
                    rank = player['rank']
                    medal = self.get_medal_emoji(rank)
                    username = player['username'][:20].ljust(20)
                    balance = f"${player['balance']:,}"
                    leaderboard_text += f"{medal} #{str(rank).rjust(3)} | {username} | {balance}\n"
                leaderboard_text += "```"
            
            embed = discord.Embed(
                title="💰 Wealth Leaderboard",
                description=f"Top 25 richest players in Risky Monopoly\n{leaderboard_text}",
                color=discord.Color.gold()
            )
            embed.set_footer(text="Updated every 30 seconds • Use rm!leaderboard for interactive view")
            embed.timestamp = discord.utils.utcnow()
            
            # Try to edit existing message, or create new one
            if settings.get('leaderboard_message_id'):
                try:
                    message = await channel.fetch_message(int(settings['leaderboard_message_id']))
                    await message.edit(embed=embed)
                    print(f"✅ Updated leaderboard in guild {guild_id}")
                    return
                except discord.NotFound:
                    print(f"Leaderboard message not found, creating new one in guild {guild_id}")
                except Exception as e:
                    print(f"Error editing leaderboard message: {e}")
            
            # Create new message
            message = await channel.send(embed=embed)
            await db.set_leaderboard_channel(guild_id, str(channel.id), str(message.id))
            print(f"✅ Created new leaderboard message in guild {guild_id}")
            
        except Exception as e:
            print(f"Error updating persistent leaderboard for guild {guild_id}: {e}")
            import traceback
            traceback.print_exc()

class LeaderboardView(discord.ui.View):
    def __init__(self, current_page: int, total_pages: int):
        super().__init__(timeout=180)
        self.current_page = current_page
        self.total_pages = total_pages
        
        # Disable buttons if at boundaries
        self.children[0].disabled = (current_page == 0)  # First
        self.children[1].disabled = (current_page == 0)  # Previous
        self.children[2].disabled = (current_page >= total_pages - 1)  # Next
        self.children[3].disabled = (current_page >= total_pages - 1)  # Last
    
    @discord.ui.button(label="⏮️ First", style=discord.ButtonStyle.secondary)
    async def first_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog('LeaderboardCommands')
        await cog.show_leaderboard_page(interaction, 0, is_initial=False)
    
    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.primary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            cog = interaction.client.get_cog('LeaderboardCommands')
            await cog.show_leaderboard_page(interaction, self.current_page - 1, is_initial=False)
    
    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages - 1:
            cog = interaction.client.get_cog('LeaderboardCommands')
            await cog.show_leaderboard_page(interaction, self.current_page + 1, is_initial=False)
    
    @discord.ui.button(label="Last ⏭️", style=discord.ButtonStyle.secondary)
    async def last_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog('LeaderboardCommands')
        await cog.show_leaderboard_page(interaction, self.total_pages - 1, is_initial=False)

async def is_admin_or_authorized(ctx_or_interaction) -> bool:
    """
    Check if user is:
    1. Bot owner (always has access)
    2. Server admin (always has access)
    3. Has an authorized admin role
    """
    # Handle both Context and Interaction
    if isinstance(ctx_or_interaction, discord.Interaction):
        user = ctx_or_interaction.user
        guild = ctx_or_interaction.guild
        client = ctx_or_interaction.client
    else:  # commands.Context
        user = ctx_or_interaction.author
        guild = ctx_or_interaction.guild
        client = ctx_or_interaction.bot
    
    if not guild:
        return False
    
    # Check if user is bot owner
    app_info = client.application
    is_owner = user.id == app_info.owner.id if app_info and app_info.owner else False
    
    if is_owner:
        return True
    
    # Check if user has administrator permissions
    is_admin = user.guild_permissions.administrator
    
    if is_admin:
        return True
    
    # Check if user has an authorized admin role
    settings = await db.get_guild_settings(str(guild.id))
    if settings and settings.get('admin_role_ids'):
        admin_role_ids = settings['admin_role_ids']
        user_role_ids = [str(role.id) for role in user.roles]
        
        # Check if user has any of the authorized roles
        if any(role_id in admin_role_ids for role_id in user_role_ids):
            return True
    
    return False

def is_admin_check():
    """Decorator for hybrid commands to check admin/owner/authorized role"""
    async def predicate(ctx: commands.Context):
        return await is_admin_or_authorized(ctx)
    return commands.check(predicate)

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="set-admin-roles", description="[ADMIN] Set roles that can use admin commands")
    @app_commands.describe(roles="Roles to authorize for admin commands (mention them)")
    async def set_admin_roles(self, interaction: discord.Interaction, roles: str):
        """[ADMIN] Set roles that can use admin commands"""
        # Check if user is admin or owner (not checking authorized roles since we're setting them)
        app_info = interaction.client.application
        is_owner = interaction.user.id == app_info.owner.id if app_info and app_info.owner else False
        is_admin = interaction.user.guild_permissions.administrator if interaction.guild else False
        
        if not (is_owner or is_admin):
            return await interaction.response.send_message(
                '❌ You need Administrator permissions (or be the bot owner) to use this command!',
                ephemeral=True
            )
        
        # Extract role mentions from the roles string
        role_ids = []
        mentioned_roles = []
        
        # Parse role mentions from the string
        import re
        role_mentions = re.findall(r'<@&(\d+)>', roles)
        
        if not role_mentions:
            return await interaction.response.send_message(
                '❌ No valid role mentions found! Please mention the roles you want to authorize.\n'
                'Example: `/set-admin-roles roles: @Moderator @Staff`',
                ephemeral=True
            )
        
        # Validate roles exist in guild
        for role_id in role_mentions:
            role = interaction.guild.get_role(int(role_id))
            if role:
                role_ids.append(role_id)
                mentioned_roles.append(role)
        
        if not role_ids:
            return await interaction.response.send_message(
                '❌ None of the mentioned roles were found in this server!',
                ephemeral=True
            )
        
        # Save to database
        await db.set_admin_roles(str(interaction.guild.id), role_ids)
        
        role_list = ", ".join([role.mention for role in mentioned_roles])
        
        embed = discord.Embed(
            title="✅ Admin Roles Updated",
            description=f"The following roles can now use admin commands:\n{role_list}",
            color=discord.Color.green()
        )
        embed.add_field(
            name="ℹ️ Who Can Use Admin Commands",
            value="• Bot Owner (always)\n"
                  "• Server Administrators (always)\n"
                  "• Users with the roles listed above",
            inline=False
        )
        embed.set_footer(text="Use /remove-admin-roles to remove specific roles or /clear-admin-roles to remove all")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="remove-admin-roles", description="[ADMIN] Remove roles from admin command access")
    @app_commands.describe(roles="Roles to remove from admin commands (mention them)")
    async def remove_admin_roles(self, interaction: discord.Interaction, roles: str):
        """[ADMIN] Remove roles from admin command access"""
        # Check if user is admin or owner
        app_info = interaction.client.application
        is_owner = interaction.user.id == app_info.owner.id if app_info and app_info.owner else False
        is_admin = interaction.user.guild_permissions.administrator if interaction.guild else False
        
        if not (is_owner or is_admin):
            return await interaction.response.send_message(
                '❌ You need Administrator permissions (or be the bot owner) to use this command!',
                ephemeral=True
            )
        
        # Get current admin roles
        settings = await db.get_guild_settings(str(interaction.guild.id))
        if not settings or not settings.get('admin_role_ids'):
            return await interaction.response.send_message(
                '❌ No admin roles are currently set!',
                ephemeral=True
            )
        
        current_role_ids = settings['admin_role_ids']
        
        # Parse role mentions
        import re
        role_mentions = re.findall(r'<@&(\d+)>', roles)
        
        if not role_mentions:
            return await interaction.response.send_message(
                '❌ No valid role mentions found! Please mention the roles you want to remove.',
                ephemeral=True
            )
        
        # Remove the roles
        removed_roles = []
        for role_id in role_mentions:
            if role_id in current_role_ids:
                current_role_ids.remove(role_id)
                role = interaction.guild.get_role(int(role_id))
                if role:
                    removed_roles.append(role)
        
        if not removed_roles:
            return await interaction.response.send_message(
                '❌ None of the mentioned roles were in the admin roles list!',
                ephemeral=True
            )
        
        # Update database
        await db.set_admin_roles(str(interaction.guild.id), current_role_ids)
        
        role_list = ", ".join([role.mention for role in removed_roles])
        
        embed = discord.Embed(
            title="✅ Admin Roles Removed",
            description=f"The following roles can no longer use admin commands:\n{role_list}",
            color=discord.Color.orange()
        )
        
        if current_role_ids:
            remaining_roles = []
            for role_id in current_role_ids:
                role = interaction.guild.get_role(int(role_id))
                if role:
                    remaining_roles.append(role.mention)
            
            if remaining_roles:
                embed.add_field(
                    name="📋 Remaining Admin Roles",
                    value=", ".join(remaining_roles),
                    inline=False
                )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="clear-admin-roles", description="[ADMIN] Remove all authorized admin roles")
    async def clear_admin_roles(self, interaction: discord.Interaction):
        """[ADMIN] Clear all authorized admin roles"""
        # Check if user is admin or owner
        app_info = interaction.client.application
        is_owner = interaction.user.id == app_info.owner.id if app_info and app_info.owner else False
        is_admin = interaction.user.guild_permissions.administrator if interaction.guild else False
        
        if not (is_owner or is_admin):
            return await interaction.response.send_message(
                '❌ You need Administrator permissions (or be the bot owner) to use this command!',
                ephemeral=True
            )
        
        # Clear admin roles
        await db.set_admin_roles(str(interaction.guild.id), [])
        
        embed = discord.Embed(
            title="✅ Admin Roles Cleared",
            description="All authorized admin roles have been removed.\n\n"
                       "Only bot owner and server administrators can now use admin commands.",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="view-admin-roles", description="View roles that can use admin commands")
    async def view_admin_roles(self, interaction: discord.Interaction):
        """View roles that can use admin commands"""
        settings = await db.get_guild_settings(str(interaction.guild.id))
        
        embed = discord.Embed(
            title="🔒 Admin Command Access",
            description="Users who can use admin commands in this server:",
            color=discord.Color.blue()
        )
        
        # Always have access
        embed.add_field(
            name="✅ Always Authorized",
            value="• Bot Owner\n• Server Administrators",
            inline=False
        )
        
        # Authorized roles
        if settings and settings.get('admin_role_ids'):
            admin_role_ids = settings['admin_role_ids']
            role_mentions = []
            
            for role_id in admin_role_ids:
                role = interaction.guild.get_role(int(role_id))
                if role:
                    role_mentions.append(role.mention)
            
            if role_mentions:
                embed.add_field(
                    name="📋 Authorized Roles",
                    value="\n".join([f"• {role}" for role in role_mentions]),
                    inline=False
                )
            else:
                embed.add_field(
                    name="📋 Authorized Roles",
                    value="*No roles currently authorized*",
                    inline=False
                )
        else:
            embed.add_field(
                name="📋 Authorized Roles",
                value="*No roles currently authorized*",
                inline=False
            )
        
        embed.set_footer(text="Use /set-admin-roles to authorize roles")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="setup-company-forum", description="[ADMIN] Set the company forum channel")
    @app_commands.describe(forum="The forum channel to use for companies")
    async def setup_company_forum_slash(self, interaction: discord.Interaction, forum: discord.ForumChannel):
        """[ADMIN] Set the company forum channel"""
        if not await is_admin_or_authorized(interaction):
            return await interaction.response.send_message(
                '❌ You need admin permissions to use this command!',
                ephemeral=True
            )
        
        await db.set_company_forum(str(interaction.guild.id), str(forum.id))
        
        await interaction.response.send_message(
            f'✅ Company forum set to {forum.mention}',
            ephemeral=True
        )
    
    @app_commands.command(name="setup-bank-forum", description="[ADMIN] Set the bank forum channel")
    @app_commands.describe(forum="The forum channel to use for loans")
    async def setup_bank_forum_slash(self, interaction: discord.Interaction, forum: discord.ForumChannel):
        """[ADMIN] Set the bank forum channel"""
        if not await is_admin_or_authorized(interaction):
            return await interaction.response.send_message(
                '❌ You need admin permissions to use this command!',
                ephemeral=True
            )
        
        await db.set_bank_forum(str(interaction.guild.id), str(forum.id))
        
        await interaction.response.send_message(
            f'✅ Bank forum set to {forum.mention}',
            ephemeral=True
        )
    
    @commands.hybrid_command(name="setup-company-forum-legacy", description="[ADMIN] Set the company forum channel")
    @is_admin_check()
    async def setup_company_forum(self, ctx: commands.Context, forum: discord.ForumChannel):
        """[ADMIN] Set the company forum channel
        
        Parameters
        -----------
        forum: discord.ForumChannel
            The forum channel to use for companies
        """
        await db.set_company_forum(str(ctx.guild.id), str(forum.id))
        
        await ctx.send(
            f'✅ Company forum set to {forum.mention}',
        )
    
    @commands.hybrid_command(name="setup-bank-forum-legacy", description="[ADMIN] Set the bank forum channel")
    @is_admin_check()
    async def setup_bank_forum(self, ctx: commands.Context, forum: discord.ForumChannel):
        """[ADMIN] Set the bank forum channel
        
        Parameters
        -----------
        forum: discord.ForumChannel
            The forum channel to use for loans
        """
        await db.set_bank_forum(str(ctx.guild.id), str(forum.id))
        
        await ctx.send(
            f'✅ Bank forum set to {forum.mention}',
        )
    
    @commands.hybrid_command(name="setup-leaderboard", description="[ADMIN] Setup persistent leaderboard in current channel")
    @is_admin_check()
    async def setup_leaderboard(self, ctx: commands.Context):
        """[ADMIN] Setup persistent leaderboard in current channel"""
        await ctx.defer()
        
        try:
            # Create initial leaderboard message
            players = await db.get_top_players(limit=25, offset=0)
            
            leaderboard_cog = self.bot.get_cog('LeaderboardCommands')
            
            if not players:
                leaderboard_text = "No players with balance yet!"
            else:
                leaderboard_text = "```\n"
                for player in players:
                    rank = player['rank']
                    medal = leaderboard_cog.get_medal_emoji(rank)
                    username = player['username'][:20].ljust(20)
                    balance = f"${player['balance']:,}"
                    leaderboard_text += f"{medal} #{str(rank).rjust(3)} | {username} | {balance}\n"
                leaderboard_text += "```"
            
            embed = discord.Embed(
                title="💰 Wealth Leaderboard",
                description=f"Top 25 richest players in Risky Monopoly\n{leaderboard_text}",
                color=discord.Color.gold()
            )
            embed.set_footer(text="Updated every 30 seconds • Use rm!leaderboard for interactive view")
            embed.timestamp = discord.utils.utcnow()
            
            message = await ctx.send(embed=embed)
            
            # Save to database
            await db.set_leaderboard_channel(str(ctx.guild.id), str(ctx.channel.id), str(message.id))
            
            await ctx.send(
                '✅ Leaderboard setup complete! This message will update automatically every 30 seconds.',
                ephemeral=True
            )
            
        except Exception as e:
            print(f"Error setting up leaderboard: {e}")
            await ctx.send(f'❌ Error setting up leaderboard: {e}')
    
    @commands.hybrid_command(name="set-max-companies", description="[ADMIN] Set maximum companies per player")
    @is_admin_check()
    async def set_max_companies(self, ctx: commands.Context, max_companies: int):
        """[ADMIN] Set maximum companies per player
        
        Parameters
        -----------
        max_companies: int
            Maximum number of companies a player can own
        """
        if max_companies < 1:
            return await ctx.send('❌ Max companies must be at least 1!', ephemeral=True)
        
        company_cog = self.bot.get_cog('CompanyCommands')
        if company_cog:
            company_cog.max_companies = max_companies
        
        await ctx.send(
            f'✅ Maximum companies per player set to {max_companies}',
        )
    
    @commands.hybrid_command(name="set-interest-rate", description="[ADMIN] Set loan interest rate")
    @is_admin_check()
    async def set_interest_rate(self, ctx: commands.Context, rate: float):
        """[ADMIN] Set loan interest rate
        
        Parameters
        -----------
        rate: float
            Interest rate percentage (e.g., 5.0 for 5%)
        """
        if rate < 0:
            return await ctx.send('❌ Interest rate cannot be negative!', ephemeral=True)
        
        economy_cog = self.bot.get_cog('EconomyCommands')
        if economy_cog:
            economy_cog.interest_rate = rate
        
        # Update environment variable
        os.environ['LOAN_INTEREST_RATE'] = str(rate)
        
        await ctx.send(
            f'✅ Loan interest rate set to {rate}%',
        )
    
    @commands.hybrid_command(name="give-money", description="[ADMIN] Give money to a player")
    @is_admin_check()
    async def give_money(self, ctx: commands.Context, user: discord.User, amount: int):
        """[ADMIN] Give money to a player
        
        Parameters
        -----------
        user: discord.User
            User to give money to
        amount: int
            Amount to give
        """
        try:
            await db.upsert_player(str(user.id), user.name)
            await db.update_player_balance(str(user.id), amount)
            
            player = await db.get_player(str(user.id))
            
            await ctx.send(
                f'✅ Gave ${amount:,} to {user.mention}. Their new balance is ${player["balance"]:,}',
            )
        except Exception as e:
            print(f"Error giving money: {e}")
            await ctx.send(f'❌ Error giving money: {e}', ephemeral=True)
    
    @commands.hybrid_command(name="set-balance", description="[ADMIN] Set a player's balance to a specific amount")
    @is_admin_check()
    async def set_balance(self, ctx: commands.Context, user: discord.User, amount: int):
        """[ADMIN] Set a player's balance to a specific amount
        
        Parameters
        -----------
        user: discord.User
            User to set balance for
        amount: int
            New balance amount
        """
        if amount < 0:
            return await ctx.send('❌ Balance cannot be negative!', ephemeral=True)
        
        try:
            await db.upsert_player(str(user.id), user.name)
            
            # Get current balance
            player = await db.get_player(str(user.id))
            current_balance = player['balance'] if player else 0
            
            # Calculate difference and update
            difference = amount - current_balance
            await db.update_player_balance(str(user.id), difference)
            
            await ctx.send(
                f'✅ Set {user.mention}\'s balance to ${amount:,}',
            )
        except Exception as e:
            print(f"Error setting balance: {e}")
            import traceback
            traceback.print_exc()
            await ctx.send(f'❌ Error setting balance: {e}', ephemeral=True)
    
    @commands.hybrid_command(name="force-disband", description="[ADMIN] Force disband a company by ID")
    @is_admin_check()
    async def force_disband(self, ctx: commands.Context, company_id: int):
        """[ADMIN] Force disband a company
        
        Parameters
        -----------
        company_id: int
            ID of the company to disband
        """
        company = await db.get_company_by_id(company_id)
        
        if not company:
            return await ctx.send(f'❌ Company #{company_id} not found!', ephemeral=True)
        
        # Delete the thread if it exists
        if company['thread_id']:
            try:
                thread = self.bot.get_channel(int(company['thread_id']))
                if not thread:
                    thread = await self.bot.fetch_channel(int(company['thread_id']))
                
                if thread:
                    # Send notification before deleting
                    embed = discord.Embed(
                        title="🔨 COMPANY DISBANDED BY ADMIN",
                        description=f"**{company['name']}** has been forcibly disbanded by an administrator.\n\nThis thread will be deleted in 5 seconds.",
                        color=discord.Color.dark_red()
                    )
                    embed.add_field(name="🏢 Company", value=company['name'], inline=True)
                    embed.add_field(name="⭐ Rank", value=company['rank'], inline=True)
                    embed.add_field(name="💰 Income", value=f"${company['current_income']:,}/30s", inline=True)
                    embed.timestamp = discord.utils.utcnow()
                    
                    await thread.send(embed=embed)
                    
                    # Wait 5 seconds then delete
                    await asyncio.sleep(5)
                    await thread.delete()
                    print(f"Deleted thread {thread.id} for company {company['name']}")
            except Exception as e:
                print(f"Error deleting company thread: {e}")
            except Exception as e:
                print(f"Error closing company thread: {e}")
        
        # Delete the company
        await db.delete_company(company_id)
        
        embed = discord.Embed(
            title="✅ Company Disbanded",
            description=f"**{company['name']}** (ID: #{company_id}) has been forcibly disbanded.",
            color=discord.Color.green()
        )
        embed.add_field(name="👤 Owner", value=f"<@{company['owner_id']}>", inline=True)
        embed.add_field(name="⭐ Rank", value=company['rank'], inline=True)
        embed.add_field(name="💰 Income", value=f"${company['current_income']:,}/30s", inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="forgive-loan", description="[ADMIN] Forgive a loan by ID")
    @is_admin_check()
    async def forgive_loan(self, ctx: commands.Context, loan_id: int):
        """[ADMIN] Forgive a loan (mark as paid without charging)
        
        Parameters
        -----------
        loan_id: int
            ID of the loan to forgive
        """
        loan = await db.get_loan_by_id(loan_id)
        
        if not loan:
            return await ctx.send(f'❌ Loan #{loan_id} not found!', ephemeral=True)
        
        if loan['is_paid']:
            return await ctx.send(f'❌ Loan #{loan_id} is already paid!', ephemeral=True)
        
        # Mark loan as paid
        await db.pay_loan(loan_id)
        
        # Update the loan thread embed if it exists
        if loan.get('thread_id') and loan.get('embed_message_id'):
            try:
                thread = self.bot.get_channel(int(loan['thread_id']))
                if not thread:
                    thread = await self.bot.fetch_channel(int(loan['thread_id']))
                
                if thread:
                    try:
                        message = await thread.fetch_message(int(loan['embed_message_id']))
                        
                        # Update the embed to show FORGIVEN
                        old_embed = message.embeds[0] if message.embeds else None
                        if old_embed:
                            new_embed = discord.Embed(
                                title="💚 Loan FORGIVEN",
                                description=old_embed.description,
                                color=discord.Color.green()
                            )
                            for field in old_embed.fields:
                                new_embed.add_field(name=field.name, value=field.value, inline=field.inline)
                            new_embed.add_field(name="✨ Status", value="FORGIVEN BY ADMIN", inline=False)
                            new_embed.set_footer(text="This loan has been forgiven by an administrator")
                            new_embed.timestamp = discord.utils.utcnow()
                            
                            await message.edit(embed=new_embed)
                            await thread.edit(archived=True, locked=True)
                    except Exception as e:
                        print(f"Error updating loan embed: {e}")
            except Exception as e:
                print(f"Error accessing loan thread: {e}")
        
        embed = discord.Embed(
            title="✅ Loan Forgiven",
            description=f"Loan #{loan_id} has been forgiven by administrator.",
            color=discord.Color.green()
        )
        embed.add_field(name="👤 Borrower", value=f"<@{loan['borrower_id']}>", inline=True)
        embed.add_field(name="💰 Amount Forgiven", value=f"${loan['total_owed']:,}", inline=True)
        embed.add_field(name="🏷️ Tier", value=loan['loan_tier'], inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="view-player", description="[ADMIN] View detailed player information")
    @is_admin_check()
    async def view_player(self, ctx: commands.Context, user: discord.User):
        """[ADMIN] View detailed information about a player
        
        Parameters
        -----------
        user: discord.User
            User to view information for
        """
        player = await db.get_player(str(user.id))
        
        if not player:
            return await ctx.send(f'❌ {user.mention} has not joined the game yet!', ephemeral=True)
        
        # Get companies
        companies = await db.get_player_companies(str(user.id))
        
        # Get loans
        unpaid_loans = await db.get_player_loans(str(user.id), unpaid_only=True)
        all_loans = await db.get_player_loans(str(user.id), unpaid_only=False)
        
        embed = discord.Embed(
            title=f"👤 Player Info: {user.name}",
            description=f"User ID: `{user.id}`",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        
        # Balance info
        embed.add_field(name="💰 Balance", value=f"${player['balance']:,}", inline=True)
        
        # Company info
        if companies:
            total_income_30s = sum(c['current_income'] for c in companies)
            company_list = "\n".join([
                f"#{c['id']} - {c['name']} ({c['rank']}) - ${c['current_income']:,}/30s"
                for c in companies
            ])
            embed.add_field(
                name=f"🏢 Companies ({len(companies)})",
                value=company_list[:1024],
                inline=False
            )
            embed.add_field(name="📊 Total Income", value=f"${total_income_30s:,}/30s", inline=True)
        else:
            embed.add_field(name="🏢 Companies", value="None", inline=False)
        
        # Loan info
        if unpaid_loans:
            total_debt = sum(l['total_owed'] for l in unpaid_loans)
            loan_list = "\n".join([
                f"#{l['id']} - {l['loan_tier']} Tier - ${l['total_owed']:,} - Due {discord.utils.format_dt(l['due_date'], 'R')}"
                for l in unpaid_loans[:5]
            ])
            if len(unpaid_loans) > 5:
                loan_list += f"\n... and {len(unpaid_loans) - 5} more"
            
            embed.add_field(
                name=f"💳 Active Loans ({len(unpaid_loans)})",
                value=loan_list[:1024],
                inline=False
            )
            embed.add_field(name="💸 Total Debt", value=f"${total_debt:,}", inline=True)
        else:
            embed.add_field(name="💳 Active Loans", value="None", inline=False)
        
        # Stats
        embed.add_field(name="📈 Total Loans Taken", value=str(len(all_loans)), inline=True)
        embed.add_field(name="📅 Joined", value=discord.utils.format_dt(player['created_at'], 'R'), inline=True)
        
        embed.timestamp = discord.utils.utcnow()
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="force-event", description="[ADMIN] Trigger daily events for all companies")
    @is_admin_check()
    async def force_event(self, ctx: commands.Context):
        """[ADMIN] Trigger daily events for all companies"""
        async with ctx.typing():
            try:
                await trigger_daily_events(self.bot)
                
                # Update leaderboards
                leaderboard_cog = self.bot.get_cog('LeaderboardCommands')
                if leaderboard_cog:
                    for guild in self.bot.guilds:
                        await leaderboard_cog.update_persistent_leaderboard(str(guild.id))
                
                await ctx.send('✅ Daily events triggered for all companies and leaderboards updated!')
            except Exception as e:
                print(f"Error triggering events: {e}")
                await ctx.send(f'❌ Error triggering events: {e}')
    
    @commands.hybrid_command(name="list-all-companies", description="[ADMIN] List all companies in the database")
    @is_admin_check()
    async def list_all_companies(self, ctx: commands.Context):
        """[ADMIN] List all companies in the database"""
        companies = await db.get_all_companies()
        
        if not companies:
            return await ctx.send('📋 No companies exist yet!', ephemeral=True)
        
        # Sort by rank and income
        rank_order = ['F', 'E', 'D', 'C', 'B', 'A', 'S', 'SS', 'SSR']
        companies.sort(key=lambda c: (rank_order.index(c['rank']), -c['current_income']))
        
        embed = discord.Embed(
            title="🏢 All Companies",
            description=f"Total: {len(companies)} companies",
            color=discord.Color.blue()
        )
        
        # Group by rank
        for rank in rank_order:
            rank_companies = [c for c in companies if c['rank'] == rank]
            if rank_companies:
                company_list = "\n".join([
                    f"#{c['id']} - {c['name']} - <@{c['owner_id']}> - ${c['current_income']:,}/30s"
                    for c in rank_companies[:10]
                ])
                if len(rank_companies) > 10:
                    company_list += f"\n... and {len(rank_companies) - 10} more"
                
                embed.add_field(
                    name=f"⭐ {rank} Rank ({len(rank_companies)})",
                    value=company_list[:1024],
                    inline=False
                )
        
        embed.timestamp = discord.utils.utcnow()
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="list-all-loans", description="[ADMIN] List all active loans")
    @is_admin_check()
    async def list_all_loans(self, ctx: commands.Context):
        """[ADMIN] List all active loans in the database"""
        # Get all unpaid loans
        loans = await db.get_overdue_loans()
        
        # Get all active (non-overdue) loans
        async with db.pool.acquire() as conn:
            active_rows = await conn.fetch('''
                SELECT * FROM loans
                WHERE is_paid = FALSE AND due_date >= CURRENT_TIMESTAMP
                ORDER BY due_date
            ''')
            active_loans = [dict(row) for row in active_rows]
        
        all_loans = loans + active_loans
        
        if not all_loans:
            return await ctx.send('📋 No active loans exist!', ephemeral=True)
        
        embed = discord.Embed(
            title="💳 All Active Loans",
            description=f"Total: {len(all_loans)} loans ({len(loans)} overdue)",
            color=discord.Color.red() if loans else discord.Color.blue()
        )
        
        # Show overdue loans first
        if loans:
            loan_list = "\n".join([
                f"#{l['id']} - <@{l['borrower_id']}> - {l['loan_tier']} - ${l['total_owed']:,} - ⚠️ OVERDUE"
                for l in loans[:10]
            ])
            if len(loans) > 10:
                loan_list += f"\n... and {len(loans) - 10} more"
            
            embed.add_field(
                name=f"⚠️ Overdue Loans ({len(loans)})",
                value=loan_list[:1024],
                inline=False
            )
        
        # Show active loans
        if active_loans:
            loan_list = "\n".join([
                f"#{l['id']} - <@{l['borrower_id']}> - {l['loan_tier']} - ${l['total_owed']:,} - Due {discord.utils.format_dt(l['due_date'], 'R')}"
                for l in active_loans[:10]
            ])
            if len(active_loans) > 10:
                loan_list += f"\n... and {len(active_loans) - 10} more"
            
            embed.add_field(
                name=f"✅ Active Loans ({len(active_loans)})",
                value=loan_list[:1024],
                inline=False
            )
        
        # Calculate totals
        total_outstanding = sum(l['total_owed'] for l in all_loans)
        embed.add_field(name="💰 Total Outstanding", value=f"${total_outstanding:,}", inline=True)
        
        embed.timestamp = discord.utils.utcnow()
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="server-settings", description="[ADMIN] View current server settings")
    @is_admin_check()
    async def server_settings(self, ctx: commands.Context):
        """[ADMIN] View current server settings"""
        settings = await db.get_guild_settings(str(ctx.guild.id))
        
        embed = discord.Embed(
            title="⚙️ Server Settings",
            description="Current configuration for Risky Monopoly",
            color=discord.Color.blue()
        )
        
        if settings:
            if settings.get('company_forum_id'):
                embed.add_field(
                    name="🏢 Company Forum",
                    value=f"<#{settings['company_forum_id']}>",
                    inline=False
                )
            else:
                embed.add_field(name="🏢 Company Forum", value="Not set", inline=False)
            
            if settings.get('bank_forum_id'):
                embed.add_field(
                    name="🏦 Bank Forum",
                    value=f"<#{settings['bank_forum_id']}>",
                    inline=False
                )
            else:
                embed.add_field(name="🏦 Bank Forum", value="Not set", inline=False)
            
            if settings.get('leaderboard_channel_id'):
                embed.add_field(
                    name="📊 Leaderboard Channel",
                    value=f"<#{settings['leaderboard_channel_id']}>",
                    inline=False
                )
            else:
                embed.add_field(name="📊 Leaderboard Channel", value="Not set", inline=False)
            
            # Show admin roles
            if settings.get('admin_role_ids'):
                admin_role_ids = settings['admin_role_ids']
                role_mentions = []
                
                for role_id in admin_role_ids:
                    role = ctx.guild.get_role(int(role_id))
                    if role:
                        role_mentions.append(role.mention)
                
                if role_mentions:
                    embed.add_field(
                        name="🔒 Admin Roles",
                        value=", ".join(role_mentions),
                        inline=False
                    )
                else:
                    embed.add_field(name="🔒 Admin Roles", value="None set", inline=False)
            else:
                embed.add_field(name="🔒 Admin Roles", value="None set", inline=False)
        else:
            embed.description = "No settings configured yet!"
        
        # Add game settings
        company_cog = self.bot.get_cog('CompanyCommands')
        economy_cog = self.bot.get_cog('EconomyCommands')
        
        if company_cog:
            embed.add_field(name="🏢 Max Companies", value=str(company_cog.max_companies), inline=True)
        if economy_cog:
            embed.add_field(name="💳 Loan Interest Rate", value=f"{economy_cog.interest_rate}%", inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="post-guide", description="[OWNER] Post the bot guide")
    @commands.is_owner()
    async def post_guide(self, ctx: commands.Context):
        """[OWNER ONLY] Post the comprehensive bot guide"""
        embed = discord.Embed(
            title="📚 Risky Monopoly - Complete Guide",
            description="Welcome to Risky Monopoly! Build your business empire from a lemonade stand to a global monopoly!",
            color=discord.Color.gold()
        )
        
        # Getting Started
        embed.add_field(
            name="🎮 Getting Started",
            value="1️⃣ Use `rm!create-company` in the company forum\n"
                  "2️⃣ Start with a FREE Lemonade Stand (F Rank)\n"
                  "3️⃣ Income generates every 30 seconds automatically\n"
                  "4️⃣ Money is deposited directly to your balance\n"
                  "5️⃣ Save money to upgrade to better companies!",
            inline=False
        )
        
        # Core Commands
        embed.add_field(
            name="💼 Core Commands",
            value="`rm!create-company` - Create a new company (interactive)\n"
                  "`rm!my-companies` - View your companies\n"
                  "`rm!balance` - Check your balance & income rates\n"
                  "`rm!upgrade-company` - Buy assets (in company thread)\n"
                  "`rm!disband-company <id>` - Disband a company for money",
            inline=False
        )
        
        # Banking Commands
        embed.add_field(
            name="🏦 Banking & Loans",
            value="`rm!request-loan` - Request a loan (use in bank forum)\n"
                  "`rm!my-loans` - View your active loans\n"
                  "`rm!pay-loan <id>` - Pay off a loan\n"
                  "⚠️ **WARNING**: Unpaid loans = Company liquidation!",
            inline=False
        )
        
        # Admin Commands
        embed.add_field(
            name="⚙️ Admin Commands",
            value="`/setup-company-forum` - Set company creation forum\n"
                  "`/setup-bank-forum` - Set bank/loans forum\n"
                  "`/set-event-frequency <hours>` - Set event frequency (default 6h)\n"
                  "`/view-settings` - View current server settings\n"
                  "`/set-admin-roles` - Authorize roles for admin commands\n"
                  "`/view-admin-roles` - View authorized admin roles\n"
                  "`/create-leaderboard` - Create persistent leaderboard\n"
                  "`/force-disband-company <id>` - Force delete any company\n"
                  "`/disband-all-companies` - Delete ALL companies (⚠️ CAUTION)",
            inline=False
        )
        
        # Progression System
        embed.add_field(
            name="📈 Rank Progression",
            value="**F** → **E** → **D** → **C** → **B** → **A** → **S** → **SS** → **SSR**\n\n"
                  "🔹 F: $0-800 | $10-20/30s\n"
                  "🔹 E: $5k-7k | $50-65/30s\n"
                  "🔹 D: $35k-50k | $200-280/30s\n"
                  "🔹 C: $180k-240k | $800-1k/30s\n"
                  "🔹 B: $800k-1.2M | $3k-3.8k/30s\n"
                  "🔹 A: $3.5M-5M | $10k-12.5k/30s\n"
                  "🔹 S: $18M-25M | $40k-48k/30s\n"
                  "🔹 SS: $80M-110M | $150k-180k/30s\n"
                  "🔹 SSR: $350M-450M | $500k-600k/30s",
            inline=False
        )
        
        # Strategy Tips
        embed.add_field(
            name="💡 Pro Tips",
            value="• **Max 3 companies** - Choose wisely!\n"
                  "• **Loans accelerate progress** - But pay them back!\n"
                  "• **Buy assets** to boost company income\n"
                  "• **Disband weak companies** to make room for better ones\n"
                  "• **Check leaderboard** with `rm!leaderboard` to see rankings\n"
                  "• **Events affect income** - Can be positive or negative!",
            inline=False
        )
        
        # Additional Info
        embed.add_field(
            name="🎯 Game Mechanics",
            value="**Income Generation**: Every 30 seconds (automatic)\n"
                  "**Company Events**: Every 6 hours (default, configurable by admin)\n"
                  "**ROI (Return on Investment)**: Most companies pay for themselves in 15-120 minutes\n"
                  "**Liquidation Value**: 5x base income when disbanding\n"
                  "**First F Company**: Always FREE (Lemonade Stand)\n"
                  "**Company Threads**: Each company gets its own thread for management",
            inline=False
        )
        
        embed.set_footer(text="Good luck building your empire! 🚀")
        embed.timestamp = discord.utils.utcnow()
        
        await ctx.send(embed=embed)
    
    @app_commands.command(name="list-companies", description="View all companies currently active in this server")
    async def list_companies_public(self, interaction: discord.Interaction):
        """Public command — anyone can view all companies in the server"""
        companies = await db.get_all_companies()

        if not companies:
            return await interaction.response.send_message(
                '📋 No companies exist in this server yet!',
                ephemeral=True
            )

        # Sort by rank tier then by income descending
        rank_order = ['F', 'E', 'D', 'C', 'B', 'A', 'S', 'SS', 'SSR']

        def rank_sort_key(c):
            try:
                return (rank_order.index(c['rank']), -c['current_income'])
            except ValueError:
                return (len(rank_order), -c['current_income'])

        companies.sort(key=rank_sort_key)

        # Build paginated embeds (Discord field limit = 25)
        pages = []
        page_size = 20
        for i in range(0, len(companies), page_size):
            chunk = companies[i:i + page_size]

            embed = discord.Embed(
                title="🏢 All Companies",
                description=f"**{len(companies)} total companies** in this server",
                color=discord.Color.blue()
            )

            # Group this chunk by rank for readability
            current_rank = None
            field_lines = {}
            for c in chunk:
                if c['rank'] not in field_lines:
                    field_lines[c['rank']] = []
                owner_mention = f"<@{c['owner_id']}>"
                field_lines[c['rank']].append(
                    f"  **#{c['id']}** {c['name']} — {owner_mention} — ${c['current_income']:,}/30s"
                )

            for rank in rank_order:
                if rank in field_lines:
                    rank_companies_in_chunk = [c for c in chunk if c['rank'] == rank]
                    total_in_rank = len([c for c in companies if c['rank'] == rank])
                    embed.add_field(
                        name=f"⭐ Rank {rank} ({total_in_rank} total)",
                        value="\n".join(field_lines[rank]),
                        inline=False
                    )

            page_start = i + 1
            page_end = min(i + page_size, len(companies))
            total_pages = (len(companies) + page_size - 1) // page_size
            embed.set_footer(text=f"Showing {page_start}–{page_end} of {len(companies)} • Page {(i // page_size) + 1}/{total_pages}")
            embed.timestamp = discord.utils.utcnow()
            pages.append(embed)

        # Show first page with navigation if multiple pages
        if len(pages) == 1:
            await interaction.response.send_message(embed=pages[0])
        else:
            view = CompanyListPaginationView(pages, interaction.user.id)
            await interaction.response.send_message(embed=pages[0], view=view)

    @app_commands.command(name="reset-server", description="[ADMIN] Delete ALL companies, forgive ALL loans, and reset ALL balances to $0")
    async def reset_server(self, interaction: discord.Interaction):
        """[ADMIN] Full server economy reset — requires confirmation"""
        if not await is_admin_or_authorized(interaction):
            return await interaction.response.send_message(
                '❌ You need to be: Bot Owner, Server Admin, or have an authorized admin role!',
                ephemeral=True
            )

        # Gather stats to show in the confirmation prompt
        all_companies = await db.get_all_companies()
        all_active_loans = await db.get_all_active_loans()
        all_players = await db.get_all_players_with_balance()

        total_wealth = sum(p['balance'] for p in all_players)
        total_debt = sum(l['total_owed'] for l in all_active_loans)

        embed = discord.Embed(
            title="⚠️ SERVER ECONOMY RESET — CONFIRM",
            description=(
                "**This will permanently:**\n"
                "• 🗑️ Delete every company and archive their threads\n"
                "• 💳 Forgive (zero out) every active loan\n"
                "• 💰 Set every player's balance to **$0**\n\n"
                "**This action CANNOT be undone.**"
            ),
            color=discord.Color.red()
        )
        embed.add_field(name="🏢 Companies to Delete", value=f"{len(all_companies)}", inline=True)
        embed.add_field(name="💳 Loans to Forgive", value=f"{len(all_active_loans)}", inline=True)
        embed.add_field(name="👤 Players to Reset", value=f"{len(all_players)}", inline=True)
        embed.add_field(name="💰 Total Wealth Erased", value=f"${total_wealth:,}", inline=True)
        embed.add_field(name="💸 Total Debt Forgiven", value=f"${total_debt:,}", inline=True)
        embed.set_footer(text="Click the button below to confirm. This prompt expires in 60 seconds.")
        embed.timestamp = discord.utils.utcnow()

        view = ResetServerConfirmView(interaction.user.id, all_companies, interaction.guild)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="check-bot-permissions", description="[ADMIN] Diagnose bot permissions on configured forum channels")
    async def check_bot_permissions(self, interaction: discord.Interaction):
        """Reports exactly which permissions the bot has or is missing on every configured forum."""
        if not await is_admin_or_authorized(interaction):
            return await interaction.response.send_message(
                '❌ You need admin permissions to use this command!',
                ephemeral=True
            )

        settings = await db.get_guild_settings(str(interaction.guild.id))
        bot_member = interaction.guild.me

        embed = discord.Embed(
            title="🔍 Bot Permission Diagnostic",
            description="Checking permissions on all configured channels…",
            color=discord.Color.blue()
        )

        # Permissions the bot needs to function in company/bank forums
        REQUIRED_FORUM_PERMS = {
            'create_public_threads': 'Create Forum Threads',
            'send_messages': 'Send Messages',
            'manage_threads': 'Manage Threads',
            'manage_messages': 'Manage Messages',
            'pin_messages': 'Pin Messages',
            'read_messages': 'View Channel',
        }

        channels_to_check = []
        if settings:
            if settings.get('company_forum_id'):
                channels_to_check.append(('🏢 Company Forum', settings['company_forum_id']))
            if settings.get('bank_forum_id'):
                channels_to_check.append(('🏦 Bank Forum', settings['bank_forum_id']))
            if settings.get('leaderboard_channel_id'):
                channels_to_check.append(('📊 Leaderboard Channel', settings['leaderboard_channel_id']))

        if not channels_to_check:
            embed.description = "⚠️ No channels have been configured yet.\nUse `/setup-company-forum` and `/setup-bank-forum` first."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        all_ok = True

        for label, channel_id in channels_to_check:
            try:
                channel = interaction.guild.get_channel(int(channel_id))
                if not channel:
                    channel = await interaction.guild.fetch_channel(int(channel_id))
            except Exception:
                channel = None

            if not channel:
                embed.add_field(
                    name=f"{label}",
                    value=f"❌ Channel `{channel_id}` **not found** — it may have been deleted.",
                    inline=False
                )
                all_ok = False
                continue

            perms = channel.permissions_for(bot_member)
            lines = []
            missing = []

            for perm_attr, perm_name in REQUIRED_FORUM_PERMS.items():
                has_it = getattr(perms, perm_attr, False)
                if has_it:
                    lines.append(f"  ✅ {perm_name}")
                else:
                    lines.append(f"  ❌ **{perm_name}** — MISSING")
                    missing.append(perm_name)
                    all_ok = False

            status = "✅ All required permissions present" if not missing else f"⚠️ Missing {len(missing)} permission(s)"
            embed.add_field(
                name=f"{label} — {channel.mention}",
                value=f"{status}\n" + "\n".join(lines),
                inline=False
            )

        # Overall summary
        if all_ok:
            embed.color = discord.Color.green()
            embed.description = "✅ **All configured channels have the required permissions.** The bot should be fully functional."
        else:
            embed.color = discord.Color.red()
            embed.description = (
                "❌ **Permission issues detected.** The bot is missing one or more required permissions.\n"
                "To fix: go to the channel settings → Permissions → select the bot's role → grant the permissions marked ❌ above."
            )

        embed.set_footer(text="Permissions are resolved per-channel including role overwrites")
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed, ephemeral=True)
    @app_commands.describe(hours="Hours between events (1-168 hours, default is 6)")
    async def set_event_frequency(self, interaction: discord.Interaction, hours: int):
        """Set event frequency for the server"""
        if not await is_admin_or_authorized(interaction):
            return await interaction.response.send_message(
                '❌ You need admin permissions to use this command!',
                ephemeral=True
            )
        
        # Validate hours
        if hours < 1 or hours > 168:  # 1 hour minimum, 1 week maximum
            return await interaction.response.send_message(
                '❌ Event frequency must be between 1 and 168 hours (1 week)!',
                ephemeral=True
            )
        
        # Update database
        await db.set_event_frequency(str(interaction.guild.id), hours)
        
        # Calculate some helpful time estimates
        events_per_day = 24 / hours
        events_per_week = events_per_day * 7
        
        embed = discord.Embed(
            title="✅ Event Frequency Updated",
            description=f"Company events will now occur every **{hours} hour(s)**",
            color=discord.Color.green()
        )
        embed.add_field(name="⏰ Frequency", value=f"{hours} hour(s)", inline=True)
        embed.add_field(name="📊 Events/Day", value=f"~{events_per_day:.1f}", inline=True)
        embed.add_field(name="📅 Events/Week", value=f"~{events_per_week:.1f}", inline=True)
        embed.add_field(
            name="ℹ️ How It Works",
            value=f"Each company will experience a random event (positive, negative, or neutral) "
                  f"every {hours} hour(s). Events affect company income temporarily.",
            inline=False
        )
        embed.set_footer(text="Events are checked every 30 seconds but only trigger when the time has elapsed")
        embed.timestamp = discord.utils.utcnow()
        
        await interaction.response.send_message(embed=embed)
        print(f"✅ Set event frequency to {hours} hours for guild {interaction.guild.id}")
    
    @app_commands.command(name="view-settings", description="View server economy settings")
    async def view_settings(self, interaction: discord.Interaction):
        """View current server settings"""
        settings = await db.get_guild_settings(str(interaction.guild.id))
        
        if not settings:
            return await interaction.response.send_message(
                '⚠️ No settings configured yet. Use setup commands to configure the server.',
                ephemeral=True
            )
        
        embed = discord.Embed(
            title=f"⚙️ {interaction.guild.name} Settings",
            description="Current server economy configuration",
            color=discord.Color.blue()
        )
        
        # Company forum
        if settings.get('company_forum_id'):
            embed.add_field(
                name="🏢 Company Forum",
                value=f"<#{settings['company_forum_id']}>",
                inline=True
            )
        else:
            embed.add_field(name="🏢 Company Forum", value="Not set", inline=True)
        
        # Bank forum
        if settings.get('bank_forum_id'):
            embed.add_field(
                name="🏦 Bank Forum",
                value=f"<#{settings['bank_forum_id']}>",
                inline=True
            )
        else:
            embed.add_field(name="🏦 Bank Forum", value="Not set", inline=True)
        
        # Event frequency
        event_freq = settings.get('event_frequency_hours', 6)
        events_per_day = 24 / event_freq
        embed.add_field(
            name="⏰ Event Frequency",
            value=f"{event_freq} hour(s)\n(~{events_per_day:.1f} events/day)",
            inline=True
        )
        
        # Leaderboard
        if settings.get('leaderboard_channel_id'):
            embed.add_field(
                name="🏆 Leaderboard",
                value=f"<#{settings['leaderboard_channel_id']}>",
                inline=True
            )
        else:
            embed.add_field(name="🏆 Leaderboard", value="Not set", inline=True)
        
        # Admin roles
        if settings.get('admin_role_ids'):
            admin_role_ids = settings['admin_role_ids']
            role_mentions = []
            
            for role_id in admin_role_ids:
                role = interaction.guild.get_role(int(role_id))
                if role:
                    role_mentions.append(role.mention)
            
            if role_mentions:
                embed.add_field(
                    name="🔒 Admin Roles",
                    value=", ".join(role_mentions),
                    inline=False
                )
        
        embed.set_footer(text="Use admin commands to update settings")
        embed.timestamp = discord.utils.utcnow()
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="force-disband-company", description="Force disband any company (Admin only)")
    @app_commands.describe(company_id="The ID of the company to disband")
    async def force_disband_company(self, interaction: discord.Interaction, company_id: int):
        """Force disband a company - Admin only"""
        if not await is_admin_or_authorized(interaction):
            return await interaction.response.send_message(
                '❌ You need admin permissions to use this command!',
                ephemeral=True
            )
        
        # Get company
        company = await db.get_company_by_id(company_id)
        
        if not company:
            return await interaction.response.send_message(
                '❌ Company not found!',
                ephemeral=True
            )
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Send warning message in thread FIRST, then wait and delete
            if company['thread_id']:
                try:
                    thread = interaction.guild.get_thread(int(company['thread_id']))
                    if not thread:
                        thread = await interaction.guild.fetch_channel(int(company['thread_id']))
                    
                    if thread:
                        # Send the warning embed
                        warning_embed = discord.Embed(
                            title="🔨 COMPANY DISBANDED BY ADMIN",
                            description=f"**{company['name']}** has been forcibly disbanded by an administrator.\n\nThis thread will be deleted in 5 seconds.",
                            color=discord.Color.dark_red()
                        )
                        warning_embed.add_field(name="🏢 Company", value=company['name'], inline=True)
                        warning_embed.add_field(name="⭐ Rank", value=company['rank'], inline=True)
                        warning_embed.add_field(name="💰 Income", value=f"${company['current_income']:,}/30s", inline=True)
                        warning_embed.timestamp = discord.utils.utcnow()
                        
                        await thread.send(embed=warning_embed)
                        
                        # Wait 5 seconds
                        import asyncio
                        await asyncio.sleep(5)
                        
                        # Now delete the thread
                        await thread.delete()
                        print(f"Deleted thread {thread.id} for company {company['name']}")
                except Exception as e:
                    print(f"Failed to delete thread {company['thread_id']}: {e}")
            
            # Delete company from database
            await db.delete_company(company_id)
            
            embed = discord.Embed(
                title="✅ Company Force Disbanded",
                description=f"**{company['name']}** (ID: #{company_id}) has been forcefully disbanded.",
                color=discord.Color.green()
            )
            embed.add_field(name="🏢 Company", value=company['name'], inline=True)
            embed.add_field(name="👤 Owner", value=f"<@{company['owner_id']}>", inline=True)
            embed.add_field(name="📊 Income", value=f"${company['current_income']:,}/30s", inline=True)
            embed.set_footer(text="No liquidation value was given to the owner")
            embed.timestamp = discord.utils.utcnow()
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            print(f"✅ Admin force disbanded company #{company_id}")
            
        except Exception as e:
            print(f"Error force disbanding company: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(f'❌ Failed to disband company: {str(e)}', ephemeral=True)
    
    @app_commands.command(name="disband-all-companies", description="Disband ALL companies in the server (Admin only - USE WITH CAUTION)")
    async def disband_all_companies(self, interaction: discord.Interaction):
        """Disband all companies - Admin only, requires confirmation"""
        if not await is_admin_or_authorized(interaction):
            return await interaction.response.send_message(
                '❌ You need admin permissions to use this command!',
                ephemeral=True
            )
        
        # Get all companies
        all_companies = await db.get_all_companies()
        
        # Filter to only companies in this guild
        guild_companies = []
        for company in all_companies:
            if company.get('thread_id'):
                try:
                    thread = interaction.guild.get_thread(int(company['thread_id']))
                    if not thread:
                        thread = await interaction.guild.fetch_channel(int(company['thread_id']))
                    if thread:
                        guild_companies.append(company)
                except:
                    pass
        
        if not guild_companies:
            return await interaction.response.send_message(
                '❌ No companies found in this server!',
                ephemeral=True
            )
        
        # Create confirmation view
        view = DisbandAllConfirmView(interaction.user.id, guild_companies, interaction.guild)
        
        embed = discord.Embed(
            title="⚠️ CONFIRM MASS DISBANDMENT",
            description=f"⚠️ **WARNING: This will disband ALL {len(guild_companies)} companies in this server!**\n\n"
                       f"This action will:\n"
                       f"• Delete all company threads\n"
                       f"• Remove all company data\n"
                       f"• **NOT** give liquidation values to owners\n\n"
                       f"**This action CANNOT be undone!**",
            color=discord.Color.red()
        )
        embed.add_field(name="🏢 Companies to Delete", value=f"{len(guild_companies)}", inline=True)
        embed.set_footer(text="Click the button below to confirm")
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# ─────────────────────────────────────────────────────────────────────────
# Helper: build paginated embeds for the company list
# ─────────────────────────────────────────────────────────────────────────

def _build_company_pages(companies: list) -> list:
    """
    Split a sorted company list into Discord embed pages.
    Each page groups companies by rank and fits ≤15 companies so the
    embed stays well under the 6 000-character limit.
    """
    rank_order = ['F', 'E', 'D', 'C', 'B', 'A', 'S', 'SS', 'SSR']
    pages      = []
    chunk_size = 15          # companies per page
    total      = len(companies)

    for start in range(0, total, chunk_size):
        chunk = companies[start:start + chunk_size]
        page_num = (start // chunk_size) + 1
        total_pages = (total + chunk_size - 1) // chunk_size

        embed = discord.Embed(
            title="🏢 All Companies",
            description=f"**{total:,} companies** in this server  •  Page {page_num}/{total_pages}",
            color=discord.Color.blue()
        )

        # Group this chunk by rank
        for rank in rank_order:
            rank_cos = [c for c in chunk if c['rank'] == rank]
            if not rank_cos:
                continue
            lines = "\n".join(
                f"  `#{c['id']}` **{c['name']}** — <@{c['owner_id']}> — ${c['current_income']:,}/30s"
                for c in rank_cos
            )
            embed.add_field(
                name=f"⭐ Rank {rank}  ({len(rank_cos)})",
                value=lines,
                inline=False
            )

        embed.set_footer(text="Use the buttons below to navigate pages")
        embed.timestamp = discord.utils.utcnow()
        pages.append(embed)

    return pages if pages else [discord.Embed(
        title="🏢 All Companies",
        description="No companies exist yet.",
        color=discord.Color.blue()
    )]



class CompanyListPaginationView(discord.ui.View):
    """Pagination view for the public /list-companies command"""
    def __init__(self, pages: list, user_id: int):
        super().__init__(timeout=120)
        self.pages = pages
        self.current_page = 0
        self.user_id = user_id

    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Not your menu!", ephemeral=True)
        if self.current_page > 0:
            self.current_page -= 1
            await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)
        else:
            await interaction.response.send_message("Already on the first page.", ephemeral=True)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Not your menu!", ephemeral=True)
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)
        else:
            await interaction.response.send_message("Already on the last page.", ephemeral=True)


class ResetServerConfirmView(discord.ui.View):
    """Two-step confirmation for /reset-server"""
    def __init__(self, user_id: int, companies: list, guild: discord.Guild):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.companies = companies
        self.guild = guild

    @discord.ui.button(label="⚠️ YES — RESET EVERYTHING", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message(
                "❌ Only the admin who initiated this can confirm!", ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        # --- 1. Archive/lock company threads (preserve history, don't delete) ---
        threads_archived = 0
        threads_failed = 0
        for company in self.companies:
            if company.get('thread_id'):
                try:
                    thread = self.guild.get_thread(int(company['thread_id']))
                    if not thread:
                        thread = await self.guild.fetch_channel(int(company['thread_id']))
                    if thread:
                        # Post a notice before archiving
                        notice_embed = discord.Embed(
                            title="🔄 SERVER ECONOMY RESET",
                            description=f"**{company['name']}** has been removed as part of a full server economy reset by an administrator.",
                            color=discord.Color.dark_red()
                        )
                        notice_embed.timestamp = discord.utils.utcnow()
                        await thread.send(embed=notice_embed)
                        await thread.edit(archived=True, locked=True)
                        threads_archived += 1
                except Exception as e:
                    print(f"Failed to archive thread {company.get('thread_id')} for company {company.get('name')}: {e}")
                    threads_failed += 1

        # --- 2. Delete all companies from the database ---
        await db.delete_all_companies()

        # --- 3. Forgive all loans (mark as paid) ---
        await db.forgive_all_loans()

        # --- 4. Reset every player's balance to 0 ---
        await db.reset_all_balances()

        # --- Build result report ---
        embed = discord.Embed(
            title="✅ Server Economy Reset Complete",
            description="The server economy has been fully reset.",
            color=discord.Color.green()
        )
        embed.add_field(name="🏢 Companies Deleted", value=str(len(self.companies)), inline=True)
        embed.add_field(name="🗂️ Threads Archived", value=str(threads_archived), inline=True)
        if threads_failed:
            embed.add_field(name="⚠️ Threads Failed", value=str(threads_failed), inline=True)
        embed.add_field(name="💳 All Loans", value="Forgiven ✅", inline=True)
        embed.add_field(name="💰 All Balances", value="Reset to $0 ✅", inline=True)
        embed.set_footer(text="Players can start fresh from here.")
        embed.timestamp = discord.utils.utcnow()

        await interaction.followup.send(embed=embed, ephemeral=True)
        print(f"✅ Server reset executed by {interaction.user} in guild {self.guild.id}")

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message(
                "❌ Only the admin who initiated this can cancel!", ephemeral=True
            )
        await interaction.response.edit_message(content="❌ Server reset cancelled.", embed=None, view=None)


class DisbandAllConfirmView(discord.ui.View):
    def __init__(self, user_id: int, companies: list, guild: discord.Guild):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.companies = companies
        self.guild = guild
    
    @discord.ui.button(label="⚠️ YES, DISBAND ALL COMPANIES", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Only the admin who initiated this can confirm!", ephemeral=True)
        
        await interaction.response.defer(ephemeral=True)
        
        deleted_count = 0
        failed_count = 0
        
        for company in self.companies:
            try:
                # Delete thread if it exists
                if company['thread_id']:
                    try:
                        thread = self.guild.get_thread(int(company['thread_id']))
                        if not thread:
                            thread = await self.guild.fetch_channel(int(company['thread_id']))
                        if thread:
                            await thread.delete()
                    except Exception as e:
                        print(f"Failed to delete thread {company['thread_id']}: {e}")
                
                # Delete company from database
                await db.delete_company(company['id'])
                deleted_count += 1
                
            except Exception as e:
                print(f"Error deleting company {company['id']}: {e}")
                failed_count += 1
        
        embed = discord.Embed(
            title="✅ Mass Disbandment Complete",
            description=f"All companies have been disbanded.",
            color=discord.Color.green()
        )
        embed.add_field(name="✅ Successfully Deleted", value=f"{deleted_count}", inline=True)
        if failed_count > 0:
            embed.add_field(name="❌ Failed", value=f"{failed_count}", inline=True)
        embed.timestamp = discord.utils.utcnow()
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        print(f"✅ Mass disbanded {deleted_count} companies in guild {self.guild.id}")
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Only the admin who initiated this can cancel!", ephemeral=True)
        
        await interaction.response.edit_message(content="❌ Mass disbandment cancelled.", embed=None, view=None)

# FIXED: Maintenance commands moved to AdminCommands cog (not in View class)


class MaintenanceCommands(commands.Cog):
    """Maintenance and status commands"""
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="shutdown-bot", description="[ADMIN] Put bot into maintenance mode")
    async def shutdown_bot(self, interaction: discord.Interaction):
        """[ADMIN] Put bot into maintenance mode"""
        # Check permissions
        if not await is_admin_or_authorized(interaction):
            return await interaction.response.send_message(
                '❌ You need to be: Bot Owner, Server Admin, or have an authorized admin role!\nUse `/set-admin-roles` to add roles.',
                ephemeral=True
            )
        
        try:
            import bot_maintenance
            
            if bot_maintenance.is_bot_shutdown():
                return await interaction.response.send_message('⚠️ Bot is already in maintenance mode!', ephemeral=True)
            
            bot_maintenance.set_bot_shutdown(True)
            
            embed = discord.Embed(
                title="🔧 Bot Shutdown - Maintenance Mode Enabled",
                description="The bot has been put into maintenance mode.",
                color=discord.Color.orange()
            )
            embed.add_field(
                name="📋 What This Means",
                value="• Players can still run commands\n• Commands show interfaces normally\n• **BUT** actions won't finalize\n• Players see maintenance messages",
                inline=False
            )
            embed.add_field(name="🔄 How to Restart", value="Use `/startup-bot` to resume", inline=False)
            embed.set_footer(text=f"Maintenance mode • By {interaction.user.name}")
            embed.timestamp = discord.utils.utcnow()
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            import traceback
            await interaction.response.send_message(f'❌ Error: {str(e)}\n```\n{traceback.format_exc()[:1000]}\n```', ephemeral=True)
    
    @app_commands.command(name="startup-bot", description="[ADMIN] Resume normal bot operations")
    async def startup_bot(self, interaction: discord.Interaction):
        """[ADMIN] Resume normal operations"""
        if not await is_admin_or_authorized(interaction):
            return await interaction.response.send_message(
                '❌ You need to be: Bot Owner, Server Admin, or have an authorized admin role!',
                ephemeral=True
            )
        
        try:
            import bot_maintenance
            
            if not bot_maintenance.is_bot_shutdown():
                return await interaction.response.send_message('⚠️ Bot is not in maintenance mode!', ephemeral=True)
            
            bot_maintenance.set_bot_shutdown(False)
            
            embed = discord.Embed(
                title="✅ Bot Restarted - Normal Operations Resumed",
                description="The bot is now back online and functioning normally!",
                color=discord.Color.green()
            )
            embed.add_field(
                name="📋 What Changed",
                value="• All commands fully functional\n• Companies can be created\n• Loans can be issued\n• Actions finalize properly",
                inline=False
            )
            embed.set_footer(text=f"Operational • By {interaction.user.name}")
            embed.timestamp = discord.utils.utcnow()
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            import traceback
            await interaction.response.send_message(f'❌ Error: {str(e)}\n```\n{traceback.format_exc()[:1000]}\n```', ephemeral=True)
    
    @app_commands.command(name="bot-status", description="Check if bot is in maintenance mode")
    async def check_bot_status(self, interaction: discord.Interaction):
        """Check bot status - anyone can use"""
        try:
            import bot_maintenance
            is_shutdown = bot_maintenance.is_bot_shutdown()
            
            if is_shutdown:
                embed = discord.Embed(
                    title="🔧 Bot Status: Maintenance Mode",
                    description="The bot is currently in maintenance mode.",
                    color=discord.Color.orange()
                )
                embed.add_field(name="Status", value="🔴 **OFFLINE** - Maintenance Mode", inline=False)
                embed.add_field(name="What This Means", value="Commands can run but won't finalize. Wait for admin to restart.", inline=False)
            else:
                embed = discord.Embed(
                    title="✅ Bot Status: Online",
                    description="The bot is fully operational!",
                    color=discord.Color.green()
                )
                embed.add_field(name="Status", value="🟢 **ONLINE** - All Systems Operational", inline=False)
                embed.add_field(name="What This Means", value="All commands working. Create companies, take loans, play!", inline=False)
            
            embed.timestamp = discord.utils.utcnow()
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            import traceback
            await interaction.response.send_message(f'❌ Error: {str(e)}\n```\n{traceback.format_exc()[:1000]}\n```', ephemeral=True)

async def setup(bot):
    await bot.add_cog(LeaderboardCommands(bot))
    await bot.add_cog(AdminCommands(bot))
    await bot.add_cog(MaintenanceCommands(bot))
