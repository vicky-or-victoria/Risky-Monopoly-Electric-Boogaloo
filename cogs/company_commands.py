# Company management commands - COMPLETE REWRITE

import discord
from discord import app_commands
from discord.ext import commands
import os
import asyncio

import database as db
from company_data import COMPANY_DATA, ASSET_TYPES, get_rank_color

# Permission check for admin commands
async def is_admin_or_authorized(ctx_or_interaction) -> bool:
    """Check if user is admin/owner/authorized"""
    if isinstance(ctx_or_interaction, discord.Interaction):
        user = ctx_or_interaction.user
        guild = ctx_or_interaction.guild
        client = ctx_or_interaction.client
    else:
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
        
        if any(role_id in admin_role_ids for role_id in user_role_ids):
            return True
    
    return False

class CompanyCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.max_companies = int(os.getenv('MAX_COMPANIES_PER_PLAYER', 3))
    
    async def check_allowed_post(self, ctx: commands.Context, command_name: str) -> bool:
        """Check if command is allowed in current channel/post"""
        # Get guild settings
        settings = await db.get_guild_settings(str(ctx.guild.id))
        
        if not settings:
            return True  # No restrictions if no settings
        
        # Get allowed post ID for this command
        allowed_post_key = f'{command_name}_post_id'
        allowed_post_id = settings.get(allowed_post_key)
        
        if not allowed_post_id:
            return True  # No restriction set
        
        # Check if we're in the allowed post (or its thread)
        current_id = str(ctx.channel.id)
        
        # If we're in a thread, check parent
        if isinstance(ctx.channel, discord.Thread):
            # Check if thread itself is the allowed post
            if current_id == allowed_post_id:
                return True
            # Check if thread's parent is the allowed forum
            if hasattr(ctx.channel, 'parent_id'):
                parent_id = str(ctx.channel.parent_id)
                if parent_id == allowed_post_id:
                    return True
        else:
            # We're in a channel
            if current_id == allowed_post_id:
                return True
        
        return False
    
    @app_commands.command(name="set-company-post", description="[ADMIN] Set which forum post /create-company can be used in")
    @app_commands.describe(
        post="The forum post where /create-company should be restricted to (optional - leave empty to remove restriction)"
    )
    async def set_company_post(self, interaction: discord.Interaction, post: discord.Thread = None):
        """[ADMIN] Set the allowed forum post for creating companies"""
        if not await is_admin_or_authorized(interaction):
            return await interaction.response.send_message(
                '❌ You need admin permissions to use this command!',
                ephemeral=True
            )
        
        guild_id = str(interaction.guild.id)
        
        if post is None:
            # Remove restriction
            await db.set_command_post_restriction(guild_id, 'create_company', None)
            return await interaction.response.send_message(
                '✅ Removed post restriction for `/create-company`. It can now be used anywhere in the company forum.',
                ephemeral=True
            )
        
        # Set restriction
        await db.set_command_post_restriction(guild_id, 'create_company', str(post.id))
        
        embed = discord.Embed(
            title="✅ Company Creation Post Set",
            description=f"`/create-company` can now only be used in {post.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="Post ID", value=post.id, inline=False)
        embed.set_footer(text="Use this command again with no post to remove the restriction")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="set-loan-post", description="[ADMIN] Set which forum post /request-loan can be used in")
    @app_commands.describe(
        post="The forum post where /request-loan should be restricted to (optional - leave empty to remove restriction)"
    )
    async def set_loan_post(self, interaction: discord.Interaction, post: discord.Thread = None):
        """[ADMIN] Set the allowed forum post for requesting loans"""
        if not await is_admin_or_authorized(interaction):
            return await interaction.response.send_message(
                '❌ You need admin permissions to use this command!',
                ephemeral=True
            )
        
        guild_id = str(interaction.guild.id)
        
        if post is None:
            # Remove restriction
            await db.set_command_post_restriction(guild_id, 'request_loan', None)
            return await interaction.response.send_message(
                '✅ Removed post restriction for `/request-loan`. It can now be used anywhere in the bank forum.',
                ephemeral=True
            )
        
        # Set restriction
        await db.set_command_post_restriction(guild_id, 'request_loan', str(post.id))
        
        embed = discord.Embed(
            title="✅ Loan Request Post Set",
            description=f"`/request-loan` can now only be used in {post.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="Post ID", value=post.id, inline=False)
        embed.set_footer(text="Use this command again with no post to remove the restriction")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @commands.hybrid_command(name="create-company", description="Create a new company (interactive selection)")
    async def create_company(self, ctx: commands.Context):
        """Create a new company with an interactive selection process"""
        try:
            # Check if guild settings exist
            settings = await db.get_guild_settings(str(ctx.guild.id))
            
            # Check if command is restricted to specific post
            if not await self.check_allowed_post(ctx, 'create_company'):
                allowed_post_id = settings.get('create_company_post_id')
                if allowed_post_id:
                    return await ctx.send(
                        f'❌ This command can only be used in <#{allowed_post_id}>!',
                        ephemeral=True if ctx.interaction else False
                    )
            
            # If settings exist and company forum is set, validate channel
            if settings and settings.get('company_forum_id'):
                # Check if we're in a thread of the forum or the forum itself
                channel_id = str(ctx.channel.id)
                if isinstance(ctx.channel, discord.Thread):
                    # Get parent channel ID for threads
                    channel_id = str(ctx.channel.parent_id)
                
                if channel_id != settings['company_forum_id']:
                    return await ctx.send(
                        f'❌ This command can only be used in <#{settings["company_forum_id"]}>!',
                        ephemeral=True if ctx.interaction else False
                    )
            elif not isinstance(ctx.channel, (discord.ForumChannel, discord.Thread)):
                return await ctx.send(
                    '❌ This command can only be used in a forum channel!',
                    ephemeral=True if ctx.interaction else False
                )
            
            # Ensure player exists
            await db.upsert_player(str(ctx.author.id), ctx.author.name)
            
            # Check max companies limit
            companies = await db.get_player_companies(str(ctx.author.id))
            if len(companies) >= self.max_companies:
                return await ctx.send(
                    f'❌ You\'ve reached the maximum of {self.max_companies} companies! Use `rm!disband-company` to disband one first.',
                    ephemeral=True if ctx.interaction else False
                )
            
            # Show rank selection
            view = RankSelectionView(ctx.author.id)
            
            embed = discord.Embed(
                title="🏢 Create Your Company - Step 1: Select Rank",
                description="Choose the rank of company you want to start.\n\n"
                           "Higher ranks cost more but generate more income!",
                color=discord.Color.blue()
            )
            
            # Add rank options to embed
            for rank in ['F', 'E', 'D', 'C', 'B', 'A', 'S', 'SS', 'SSR']:
                companies_in_rank = COMPANY_DATA[rank]
                min_cost = min(c['cost'] for c in companies_in_rank)
                max_cost = max(c['cost'] for c in companies_in_rank)
                min_income = min(c['income'] for c in companies_in_rank)
                max_income = max(c['income'] for c in companies_in_rank)
                
                cost_range = f"${min_cost:,}" if min_cost == max_cost else f"${min_cost:,} - ${max_cost:,}"
                income_range = f"${min_income:,}" if min_income == max_income else f"${min_income:,} - ${max_income:,}"
                
                embed.add_field(
                    name=f"Rank {rank}",
                    value=f"💰 Cost: {cost_range}\n📊 Income: {income_range}/30s\n🏢 {len(companies_in_rank)} types available",
                    inline=True
                )
            
            player = await db.get_player(str(ctx.author.id))
            embed.add_field(
                name="💵 Your Balance",
                value=f"${player['balance']:,}",
                inline=False
            )
            
            embed.set_footer(text="Select a rank from the dropdown below")
            
            if ctx.interaction:
                await ctx.send(embed=embed, view=view, ephemeral=True)
            else:
                await ctx.send(embed=embed, view=view)
                
        except Exception as e:
            print(f"Error in create_company command: {e}")
            import traceback
            traceback.print_exc()
            try:
                await ctx.send(f"❌ An error occurred: {str(e)}", ephemeral=True if ctx.interaction else False)
            except:
                pass
    
    @commands.hybrid_command(name="upgrade-company", description="Purchase an asset to upgrade your company")
    async def upgrade_company(self, ctx: commands.Context):
        """Purchase an asset to upgrade your company with interactive selection
        
        Can be used anywhere. If you have multiple companies, you'll choose which one to upgrade.
        """
        try:
            # Ensure player exists
            await db.upsert_player(str(ctx.author.id), ctx.author.name)
            
            # Get player data
            player = await db.get_player(str(ctx.author.id))
            
            # Get all companies owned by player
            companies = await db.get_player_companies(str(ctx.author.id))
            
            if not companies:
                return await ctx.send(
                    '❌ You don\'t own any companies! Use `rm!create-company` to create one.',
                    ephemeral=True if ctx.interaction else False
                )
            
            # If player has only one company, skip company selection
            if len(companies) == 1:
                company = companies[0]
                current_assets = await db.get_company_assets(company['id'])
                
                # Show asset category selection directly
                view = AssetCategoryView(ctx.author.id, company, player, current_assets)
                
                # Asset type emojis
                type_emojis = {
                    'upgrade': '🔧',
                    'expansion': '🏗️',
                    'marketing': '📢'
                }
                
                # Count assets by type
                available_assets = ASSET_TYPES[company['rank']]
                asset_counts = {'upgrade': 0, 'expansion': 0, 'marketing': 0}
                for asset in available_assets:
                    asset_counts[asset['type']] += 1
                
                embed = discord.Embed(
                    title=f"🏢 Upgrade {company['name']} - Select Category",
                    description=f"**Rank {company['rank']} Company**\n\n"
                               f"Choose an asset category to view available upgrades.\n\n"
                               f"**Current Company Stats:**\n"
                               f"💰 Income: ${company['current_income']:,}/30s\n"
                               f"📊 Base Income: ${company['base_income']:,}/30s\n"
                               f"🎯 Total Assets: {len(current_assets)}\n\n"
                               f"**Available Categories:**\n"
                               f"{type_emojis['upgrade']} **Upgrades** - {asset_counts['upgrade']} available\n"
                               f"{type_emojis['expansion']} **Expansions** - {asset_counts['expansion']} available\n"
                               f"{type_emojis['marketing']} **Marketing** - {asset_counts['marketing']} available",
                    color=get_rank_color(company['rank'])
                )
                
                embed.add_field(name="💰 Your Balance", value=f"${player['balance']:,}", inline=True)
                embed.add_field(name="📈 Income/Hour", value=f"${company['current_income'] * 120:,}", inline=True)
                embed.set_footer(text="Select a category to view available assets")
                
                if ctx.interaction:
                    await ctx.send(embed=embed, view=view, ephemeral=True)
                else:
                    await ctx.send(embed=embed, view=view)
            
            else:
                # Player has multiple companies - show company selection
                view = CompanySelectionView(ctx.author.id, companies, player)
                
                embed = discord.Embed(
                    title="🏢 Upgrade Company - Select Company",
                    description=f"You own **{len(companies)}** companies. Choose which one to upgrade:",
                    color=discord.Color.blue()
                )
                
                # List companies
                for i, company in enumerate(companies, 1):
                    assets = await db.get_company_assets(company['id'])
                    embed.add_field(
                        name=f"{i}. {company['name']}",
                        value=f"**Rank {company['rank']}** • ${company['current_income']:,}/30s\n"
                              f"🎯 Assets: {len(assets)}",
                        inline=False
                    )
                
                embed.add_field(name="💰 Your Balance", value=f"${player['balance']:,}", inline=True)
                embed.set_footer(text="Select a company from the dropdown below")
                
                if ctx.interaction:
                    await ctx.send(embed=embed, view=view, ephemeral=True)
                else:
                    await ctx.send(embed=embed, view=view)
                
        except Exception as e:
            print(f"Error in upgrade_company command: {e}")
            import traceback
            traceback.print_exc()
            try:
                await ctx.send(f"❌ An error occurred: {str(e)}", ephemeral=True if ctx.interaction else False)
            except:
                pass
    
    @commands.hybrid_command(name="my-companies", description="View all your companies")
    async def my_companies(self, ctx: commands.Context):
        """View all companies you own"""
        try:
            await db.upsert_player(str(ctx.author.id), ctx.author.name)
            
            companies = await db.get_player_companies(str(ctx.author.id))
            
            if not companies:
                return await ctx.send(
                    '❌ You don\'t own any companies! Use `rm!create-company` to create one.',
                    ephemeral=True if ctx.interaction else False
                )
            
            embed = discord.Embed(
                title=f"🏢 {ctx.author.name}'s Companies",
                description=f"You own **{len(companies)}** / {self.max_companies} companies",
                color=discord.Color.blue()
            )
            
            total_income = 0
            for company in companies:
                assets = await db.get_company_assets(company['id'])
                total_income += company['current_income']
                
                thread_link = f"<#{company['thread_id']}>" if company['thread_id'] else "No thread"
                
                embed.add_field(
                    name=f"{company['name']} (Rank {company['rank']})",
                    value=f"💰 Income: ${company['current_income']:,}/30s (${company['current_income'] * 120:,}/hour)\n"
                          f"⭐ Reputation: {company['reputation']}/100\n"
                          f"🎯 Assets: {len(assets)}\n"
                          f"🔗 Thread: {thread_link}",
                    inline=False
                )
            
            embed.add_field(
                name="📊 Total Income",
                value=f"${total_income:,}/30s • ${total_income * 2:,}/min • ${total_income * 120:,}/hour",
                inline=False
            )
            
            embed.set_footer(text="Use rm!upgrade-company to purchase assets!")
            embed.timestamp = discord.utils.utcnow()
            
            if ctx.interaction:
                await ctx.send(embed=embed, ephemeral=True)
            else:
                await ctx.send(embed=embed)
                
        except Exception as e:
            print(f"Error in my_companies command: {e}")
            import traceback
            traceback.print_exc()
            await ctx.send(f"❌ An error occurred: {str(e)}", ephemeral=True if ctx.interaction else False)
    
    @commands.hybrid_command(name="disband-company", description="Disband one of your companies")
    async def disband_company(self, ctx: commands.Context):
        """Disband a company you own"""
        try:
            companies = await db.get_player_companies(str(ctx.author.id))
            
            if not companies:
                return await ctx.send(
                    '❌ You don\'t own any companies!',
                    ephemeral=True if ctx.interaction else False
                )
            
            # Show company selection for disbanding
            view = DisbandCompanyView(ctx.author.id, companies)
            
            embed = discord.Embed(
                title="⚠️ Disband Company",
                description=f"You own **{len(companies)}** companies. Select which one to disband.\n\n"
                           "**Warning:** This action cannot be undone! Your company thread will be deleted.",
                color=discord.Color.red()
            )
            
            for company in companies:
                assets = await db.get_company_assets(company['id'])
                embed.add_field(
                    name=company['name'],
                    value=f"**Rank {company['rank']}** • ${company['current_income']:,}/30s\n"
                          f"🎯 Assets: {len(assets)}",
                    inline=False
                )
            
            embed.set_footer(text="Select a company from the dropdown below")
            
            if ctx.interaction:
                await ctx.send(embed=embed, view=view, ephemeral=True)
            else:
                await ctx.send(embed=embed, view=view)
                
        except Exception as e:
            print(f"Error in disband_company command: {e}")
            import traceback
            traceback.print_exc()
            await ctx.send(f"❌ An error occurred: {str(e)}", ephemeral=True if ctx.interaction else False)
    
    @commands.hybrid_command(name="rename-company", description="Rename one of your companies")
    @app_commands.describe(new_name="The new name for your company")
    async def rename_company(self, ctx: commands.Context, *, new_name: str):
        """Rename a company you own"""
        try:
            # Validate name
            if len(new_name) > 100:
                return await ctx.send(
                    '❌ Company name must be 100 characters or less!',
                    ephemeral=True if ctx.interaction else False
                )
            
            if len(new_name) < 3:
                return await ctx.send(
                    '❌ Company name must be at least 3 characters!',
                    ephemeral=True if ctx.interaction else False
                )
            
            companies = await db.get_player_companies(str(ctx.author.id))
            
            if not companies:
                return await ctx.send(
                    '❌ You don\'t own any companies!',
                    ephemeral=True if ctx.interaction else False
                )
            
            if len(companies) == 1:
                # Only one company, rename it directly
                company = companies[0]
                old_name = company['name']
                
                # Rename company
                await db.rename_company(company['id'], new_name)
                
                # Update thread name if exists
                if company['thread_id']:
                    try:
                        thread = self.bot.get_channel(int(company['thread_id']))
                        if not thread:
                            thread = await self.bot.fetch_channel(int(company['thread_id']))
                        
                        if thread:
                            await thread.edit(name=new_name)
                    except Exception as e:
                        print(f"Failed to rename thread: {e}")
                
                embed = discord.Embed(
                    title="✅ Company Renamed",
                    description=f"**{old_name}** has been renamed to **{new_name}**!",
                    color=discord.Color.green()
                )
                
                return await ctx.send(embed=embed, ephemeral=True if ctx.interaction else False)
            
            else:
                # Multiple companies - show selection
                view = RenameCompanyView(ctx.author.id, companies, new_name, self.bot)
                
                embed = discord.Embed(
                    title="🏢 Rename Company - Select Company",
                    description=f"You own **{len(companies)}** companies. Choose which one to rename to **{new_name}**:",
                    color=discord.Color.blue()
                )
                
                for company in companies:
                    embed.add_field(
                        name=company['name'],
                        value=f"**Rank {company['rank']}** • ${company['current_income']:,}/30s",
                        inline=False
                    )
                
                embed.set_footer(text="Select a company from the dropdown below")
                
                if ctx.interaction:
                    await ctx.send(embed=embed, view=view, ephemeral=True)
                else:
                    await ctx.send(embed=embed, view=view)
                
        except Exception as e:
            print(f"Error in rename_company command: {e}")
            import traceback
            traceback.print_exc()
            await ctx.send(f"❌ An error occurred: {str(e)}", ephemeral=True if ctx.interaction else False)


# ============================================================================
# VIEW CLASSES
# ============================================================================

class RankSelectionView(discord.ui.View):
    """View for selecting company rank"""
    def __init__(self, user_id: int):
        super().__init__(timeout=180)
        self.user_id = user_id
        
        # Create select menu with ranks
        options = []
        for rank in ['F', 'E', 'D', 'C', 'B', 'A', 'S', 'SS', 'SSR']:
            companies = COMPANY_DATA[rank]
            min_cost = min(c['cost'] for c in companies)
            options.append(discord.SelectOption(
                label=f"Rank {rank}",
                description=f"{len(companies)} types • Min ${min_cost:,}",
                value=rank,
                emoji="🏢"
            ))
        
        select = discord.ui.Select(
            placeholder="Choose a rank...",
            options=options,
            custom_id="rank_select"
        )
        select.callback = self.rank_selected
        self.add_item(select)
    
    async def rank_selected(self, interaction: discord.Interaction):
        """Handle rank selection"""
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message(
                "❌ This isn't your company creation menu!", 
                ephemeral=True
            )
        
        selected_rank = interaction.data['values'][0]
        
        # Show company type selection
        view = CompanyTypeSelectionView(self.user_id, selected_rank)
        
        companies = COMPANY_DATA[selected_rank]
        
        embed = discord.Embed(
            title=f"🏢 Create Your Company - Step 2: Select Type (Rank {selected_rank})",
            description=f"Choose which type of **Rank {selected_rank}** company you want to create:",
            color=get_rank_color(selected_rank)
        )
        
        for company in companies:
            embed.add_field(
                name=company['name'],
                value=f"💰 Cost: ${company['cost']:,}\n📊 Income: ${company['income']:,}/30s",
                inline=True
            )
        
        player = await db.get_player(str(self.user_id))
        embed.add_field(
            name="💵 Your Balance",
            value=f"${player['balance']:,}",
            inline=False
        )
        
        embed.set_footer(text="Select a company type from the dropdown below")
        
        await interaction.response.edit_message(embed=embed, view=view)


class CompanyTypeSelectionView(discord.ui.View):
    """View for selecting company type"""
    def __init__(self, user_id: int, rank: str):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.rank = rank
        
        # Create select menu with company types
        options = []
        companies = COMPANY_DATA[rank]
        for i, company in enumerate(companies):
            options.append(discord.SelectOption(
                label=company['name'],
                description=f"${company['cost']:,} • ${company['income']:,}/30s",
                value=str(i),
                emoji="🏢"
            ))
        
        select = discord.ui.Select(
            placeholder="Choose a company type...",
            options=options,
            custom_id="type_select"
        )
        select.callback = self.type_selected
        self.add_item(select)
    
    async def type_selected(self, interaction: discord.Interaction):
        """Handle company type selection and show name input modal"""
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message(
                "❌ This isn't your company creation menu!", 
                ephemeral=True
            )
        
        company_index = int(interaction.data['values'][0])
        company_data = COMPANY_DATA[self.rank][company_index]
        
        # Check balance
        player = await db.get_player(str(self.user_id))
        if player['balance'] < company_data['cost']:
            return await interaction.response.send_message(
                f"❌ You can't afford this! You need ${company_data['cost']:,} but only have ${player['balance']:,}.",
                ephemeral=True
            )
        
        # Show modal for company name
        modal = CompanyNameModal(
            user_id=self.user_id,
            rank=self.rank,
            company_data=company_data,
            player=player
        )
        await interaction.response.send_modal(modal)


class CompanyNameModal(discord.ui.Modal, title="Name Your Company"):
    """Modal for entering custom company name"""
    
    company_name = discord.ui.TextInput(
        label="Company Name",
        placeholder="Enter a name for your company...",
        min_length=3,
        max_length=100,
        required=True
    )
    
    def __init__(self, user_id: int, rank: str, company_data: dict, player: dict):
        super().__init__()
        self.user_id = user_id
        self.rank = rank
        self.company_data = company_data
        self.player = player
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle company name submission and create the company"""
        print(f"CompanyNameModal.on_submit called by {interaction.user.name}")
        
        custom_name = self.company_name.value.strip()
        
        # Validate name
        if len(custom_name) < 3:
            return await interaction.response.send_message(
                "❌ Company name must be at least 3 characters!",
                ephemeral=True
            )
        
        if len(custom_name) > 100:
            return await interaction.response.send_message(
                "❌ Company name must be 100 characters or less!",
                ephemeral=True
            )
        
        print(f"Deferring response for company creation: {custom_name}")
        await interaction.response.defer(ephemeral=True)
        
        try:
            # CHECK MAINTENANCE MODE
            print("Checking maintenance mode...")
            try:
                import bot_maintenance
                if bot_maintenance.is_bot_shutdown():
                    print("Bot is in maintenance mode")
                    return await interaction.followup.send(
                        bot_maintenance.get_shutdown_message(),
                        ephemeral=True
                    )
            except:
                pass  # If bot_maintenance not found, continue normally
            
            print(f"Deducting cost: ${self.company_data['cost']:,}")
            # Deduct cost
            await db.update_player_balance(str(self.user_id), -self.company_data['cost'])
            print("Balance updated")
            
            # Get guild settings for forum
            print("Getting guild settings...")
            settings = await db.get_guild_settings(str(interaction.guild.id))
            forum_id = settings.get('company_forum_id') if settings else None
            print(f"Forum ID: {forum_id}")
            
            # Create thread in forum if forum is set
            thread = None
            thread_message = None
            
            # Format thread title: "Company Name - Username"
            thread_title = f"{custom_name} - {interaction.user.name}"
            
            if forum_id:
                print(f"Creating thread in forum {forum_id}...")
                try:
                    forum = interaction.guild.get_channel(int(forum_id))
                    if not forum:
                        print("Forum not in cache, fetching...")
                        forum = await interaction.guild.fetch_channel(int(forum_id))
                    
                    if forum and isinstance(forum, discord.ForumChannel):
                        # ── Full permission audit ──────────────────────────
                        bot_member = interaction.guild.me
                        perms      = forum.permissions_for(bot_member)

                        required = {
                            'Create Forum Threads': perms.create_forum_threads,
                            'Send Messages':        perms.send_messages,
                            'Manage Threads':       perms.manage_threads,
                            'Read Messages':        perms.read_messages,
                        }
                        missing = [name for name, has in required.items() if not has]

                        if missing:
                            missing_list = "\n".join(f"  • {m}" for m in missing)
                            raise PermissionError(
                                f"The bot is missing the following permissions in {forum.mention}:\n"
                                f"{missing_list}\n\n"
                                f"Ask a server admin to grant these permissions to the bot's role in that channel."
                            )
                        # ── End permission audit ───────────────────────────
                        
                        print("Creating initial embed...")
                        # Create initial embed for thread
                        initial_embed = discord.Embed(
                            title=f"🏢 {custom_name}",
                            description=f"**Rank {self.rank} {self.company_data['name']}**\nOwned by <@{self.user_id}>",
                            color=get_rank_color(self.rank)
                        )
                        initial_embed.add_field(name="💵 Income/30s", value=f"${self.company_data['income']:,}", inline=True)
                        initial_embed.add_field(name="📊 Income/Min", value=f"${self.company_data['income'] * 2:,}", inline=True)
                        initial_embed.add_field(name="🕐 Income/Hour", value=f"${self.company_data['income'] * 120:,}", inline=True)
                        initial_embed.add_field(name="🏢 Type", value=self.company_data['name'], inline=True)
                        initial_embed.add_field(name="⭐ Rank", value=self.rank, inline=True)
                        initial_embed.add_field(name="📈 Current Income", value=f"${self.company_data['income']:,}/30s", inline=True)
                        initial_embed.set_footer(text="Use rm!upgrade-company to purchase assets!")
                        initial_embed.timestamp = discord.utils.utcnow()
                        
                        print("Creating forum thread...")
                        thread_message = await forum.create_thread(
                            name=thread_title,  # "Company Name - Username"
                            content=f"<@{self.user_id}>",
                            embed=initial_embed,
                            reason=f"Company created by {interaction.user.name}"
                        )
                        thread = thread_message.thread
                        print(f"Thread created: {thread.id}")
                        
                        # Pin the embed message
                        if thread_message.message:
                            try:
                                print("Pinning thread message...")
                                await thread_message.message.pin()
                                print("Message pinned")
                            except discord.Forbidden:
                                print("Failed to pin message: Missing PIN_MESSAGES permission")
                            except Exception as pin_error:
                                print(f"Failed to pin message: {pin_error}")
                    else:
                        print(f"Forum is not a ForumChannel or not found: {forum}")
                except PermissionError:
                    # Re-raise so the outer handler surfaces the detailed audit message
                    raise
                except Exception as e:
                    print(f"Failed to create thread: {e}")
                    import traceback
                    traceback.print_exc()
                    raise  # Re-raise to trigger refund
            else:
                print("No forum ID set, skipping thread creation")
            
            # Create company in database with custom name
            print("Creating company in database...")
            company = await db.create_company(
                owner_id=str(self.user_id),
                name=custom_name,  # Use custom name
                rank=self.rank,
                company_type=self.company_data['name'],  # Store original type
                base_income=self.company_data['income'],
                thread_id=str(thread.id) if thread else None
            )
            print(f"Company created in database: ID {company['id']}")
            
            # Success embed
            print("Creating success embed...")
            embed = discord.Embed(
                title="✅ Company Created!",
                description=f"**{custom_name}** has been established!",
                color=discord.Color.green()
            )
            
            embed.add_field(name="🏢 Company Name", value=custom_name, inline=True)
            embed.add_field(name="📋 Type", value=self.company_data['name'], inline=True)
            embed.add_field(name="⭐ Rank", value=self.rank, inline=True)
            embed.add_field(name="🆔 Company ID", value=f"#{company['id']}", inline=True)
            embed.add_field(name="💰 Cost", value=f"${self.company_data['cost']:,}", inline=True)
            embed.add_field(name="💵 New Balance", value=f"${self.player['balance'] - self.company_data['cost']:,}", inline=True)
            embed.add_field(name="📊 Income", value=f"${self.company_data['income']:,}/30s", inline=True)
            
            if thread:
                embed.add_field(name="🔗 Thread", value=thread.mention, inline=False)
            
            embed.set_footer(text="Your company will start generating income every 30 seconds!")
            embed.timestamp = discord.utils.utcnow()
            
            print("Sending success message...")
            await interaction.followup.send(embed=embed, ephemeral=True)
            print("Company creation complete!")
            
        except Exception as e:
            print(f"Error in company creation: {e}")
            import traceback
            traceback.print_exc()
            try:
                await interaction.followup.send(
                    f"❌ Error creating company: {str(e)}\n\nYour money has been refunded.",
                    ephemeral=True
                )
                # Try to refund
                await db.update_player_balance(str(self.user_id), self.company_data['cost'])
            except Exception as refund_error:
                print(f"Failed to send error message or refund: {refund_error}")


class CompanySelectionView(discord.ui.View):
    """View for selecting which company to upgrade (when player has multiple)"""
    def __init__(self, user_id: int, companies: list, player: dict):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.companies = companies
        self.player = player
        
        # Create a select menu with all companies
        options = []
        for company in companies:
            options.append(discord.SelectOption(
                label=company['name'],
                description=f"Rank {company['rank']} • ${company['current_income']:,}/30s",
                value=str(company['id']),
                emoji="🏢"
            ))
        
        select = discord.ui.Select(
            placeholder="Choose a company to upgrade...",
            options=options,
            custom_id="company_select"
        )
        select.callback = self.company_selected
        self.add_item(select)
    
    async def company_selected(self, interaction: discord.Interaction):
        """Handle company selection"""
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message(
                "❌ This isn't your upgrade menu!", 
                ephemeral=True
            )
        
        # Get selected company ID
        company_id = int(interaction.data['values'][0])
        company = next((c for c in self.companies if c['id'] == company_id), None)
        
        if not company:
            return await interaction.response.send_message(
                "❌ Company not found!", 
                ephemeral=True
            )
        
        # Get current assets
        current_assets = await db.get_company_assets(company['id'])
        
        # Show asset category selection
        view = AssetCategoryView(self.user_id, company, self.player, current_assets)
        
        # Asset type emojis
        type_emojis = {
            'upgrade': '🔧',
            'expansion': '🏗️',
            'marketing': '📢'
        }
        
        # Count assets by type
        available_assets = ASSET_TYPES[company['rank']]
        asset_counts = {'upgrade': 0, 'expansion': 0, 'marketing': 0}
        for asset in available_assets:
            asset_counts[asset['type']] += 1
        
        embed = discord.Embed(
            title=f"🏢 Upgrade {company['name']} - Select Category",
            description=f"**Rank {company['rank']} Company**\n\n"
                       f"Choose an asset category to view available upgrades.\n\n"
                       f"**Current Company Stats:**\n"
                       f"💰 Income: ${company['current_income']:,}/30s\n"
                       f"📊 Base Income: ${company['base_income']:,}/30s\n"
                       f"🎯 Total Assets: {len(current_assets)}\n\n"
                       f"**Available Categories:**\n"
                       f"{type_emojis['upgrade']} **Upgrades** - {asset_counts['upgrade']} available\n"
                       f"{type_emojis['expansion']} **Expansions** - {asset_counts['expansion']} available\n"
                       f"{type_emojis['marketing']} **Marketing** - {asset_counts['marketing']} available",
            color=get_rank_color(company['rank'])
        )
        
        embed.add_field(name="💰 Your Balance", value=f"${self.player['balance']:,}", inline=True)
        embed.add_field(name="📈 Income/Hour", value=f"${company['current_income'] * 120:,}", inline=True)
        embed.set_footer(text="Select a category to view available assets")
        
        await interaction.response.edit_message(embed=embed, view=view)


class AssetCategoryView(discord.ui.View):
    """View for selecting asset category (upgrade, expansion, marketing)"""
    def __init__(self, user_id: int, company: dict, player: dict, current_assets: list):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.company = company
        self.player = player
        self.current_assets = current_assets
    
    @discord.ui.button(label="🔧 Upgrades", style=discord.ButtonStyle.primary, custom_id="upgrade")
    async def upgrade_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ This isn't your upgrade menu!", ephemeral=True)
        
        await self.show_assets(interaction, 'upgrade')
    
    @discord.ui.button(label="🏗️ Expansions", style=discord.ButtonStyle.primary, custom_id="expansion")
    async def expansion_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ This isn't your upgrade menu!", ephemeral=True)
        
        await self.show_assets(interaction, 'expansion')
    
    @discord.ui.button(label="📢 Marketing", style=discord.ButtonStyle.primary, custom_id="marketing")
    async def marketing_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ This isn't your upgrade menu!", ephemeral=True)
        
        await self.show_assets(interaction, 'marketing')
    
    async def show_assets(self, interaction: discord.Interaction, asset_type: str):
        """Show available assets for the selected category"""
        # Get assets for this rank and type
        available_assets = [a for a in ASSET_TYPES[self.company['rank']] if a['type'] == asset_type]
        
        # Get owned asset names
        owned_asset_names = [a['asset_name'] for a in self.current_assets]
        
        # Filter out already owned assets
        purchasable_assets = [a for a in available_assets if a['name'] not in owned_asset_names]
        
        if not purchasable_assets:
            return await interaction.response.send_message(
                f"❌ You already own all {asset_type} assets for this rank!",
                ephemeral=True
            )
        
        # Create asset selection view
        view = AssetSelectionView(self.user_id, self.company, self.player, purchasable_assets, asset_type)
        
        # Type emoji mapping
        type_emojis = {
            'upgrade': '🔧',
            'expansion': '🏗️',
            'marketing': '📢'
        }
        
        # Build embed
        embed = discord.Embed(
            title=f"{type_emojis[asset_type]} {self.company['name']} - {asset_type.capitalize()} Assets",
            description=f"**Rank {self.company['rank']} Company**\n\nSelect an asset to purchase:",
            color=get_rank_color(self.company['rank'])
        )
        
        # Add assets to embed
        for i, asset in enumerate(purchasable_assets[:10], 1):  # Show max 10
            can_afford = "✅" if self.player['balance'] >= asset['cost'] else "❌"
            embed.add_field(
                name=f"{i}. {asset['name']} {can_afford}",
                value=f"💰 **Cost:** ${asset['cost']:,}\n"
                      f"📈 **Income Boost:** +${asset['boost']:,}/30s",
                inline=False
            )
        
        embed.add_field(
            name="💰 Your Balance",
            value=f"${self.player['balance']:,}",
            inline=True
        )
        embed.add_field(
            name="📊 Current Income",
            value=f"${self.company['current_income']:,}/30s",
            inline=True
        )
        
        embed.set_footer(text="Select an asset from the dropdown below")
        
        await interaction.response.edit_message(embed=embed, view=view)


class AssetSelectionView(discord.ui.View):
    """View for selecting and purchasing a specific asset"""
    def __init__(self, user_id: int, company: dict, player: dict, assets: list, asset_type: str):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.company = company
        self.player = player
        self.assets = assets
        self.asset_type = asset_type
        
        # Create select menu with assets (max 25 options)
        options = []
        for asset in assets[:25]:
            can_afford = "✅" if player['balance'] >= asset['cost'] else "❌"
            options.append(discord.SelectOption(
                label=asset['name'][:100],  # Discord limit
                description=f"${asset['cost']:,} • +${asset['boost']:,}/30s {can_afford}"[:100],
                value=str(assets.index(asset)),
                emoji="💎"
            ))
        
        select = discord.ui.Select(
            placeholder="Choose an asset to purchase...",
            options=options,
            custom_id="asset_select"
        )
        select.callback = self.asset_selected
        self.add_item(select)
        
        # Add back button
        back_button = discord.ui.Button(
            label="⬅️ Back to Categories",
            style=discord.ButtonStyle.secondary,
            custom_id="back"
        )
        back_button.callback = self.back_to_categories
        self.add_item(back_button)
    
    async def asset_selected(self, interaction: discord.Interaction):
        """Handle asset purchase"""
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message(
                "❌ This isn't your upgrade menu!", 
                ephemeral=True
            )
        
        # Get selected asset
        asset_index = int(interaction.data['values'][0])
        asset = self.assets[asset_index]
        
        # Refresh player data
        player = await db.get_player(str(self.user_id))
        
        # Check if can afford
        if player['balance'] < asset['cost']:
            return await interaction.response.send_message(
                f"❌ You can't afford this! You need ${asset['cost']:,} but only have ${player['balance']:,}.",
                ephemeral=True
            )
        
        # Check if already owns this asset
        current_assets = await db.get_company_assets(self.company['id'])
        if asset['name'] in [a['asset_name'] for a in current_assets]:
            return await interaction.response.send_message(
                f"❌ You already own **{asset['name']}**!",
                ephemeral=True
            )
        
        # CHECK MAINTENANCE MODE
        try:
            import bot_maintenance
            if bot_maintenance.is_bot_shutdown():
                return await interaction.response.send_message(
                    bot_maintenance.get_shutdown_message(),
                    ephemeral=True
                )
        except:
            pass
        
        # Purchase the asset
        try:
            # Deduct cost from balance
            await db.update_player_balance(str(self.user_id), -asset['cost'])
            
            # Add asset to company
            await db.add_company_asset(
                self.company['id'],
                asset['name'],
                asset['type'],
                asset['boost'],
                asset['cost']
            )
            
            # Success embed
            embed = discord.Embed(
                title="✅ Asset Purchased!",
                description=f"**{asset['name']}** has been added to **{self.company['name']}**!",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="💰 Cost",
                value=f"${asset['cost']:,}",
                inline=True
            )
            embed.add_field(
                name="📈 Income Boost",
                value=f"+${asset['boost']:,}/30s",
                inline=True
            )
            embed.add_field(
                name="💵 New Balance",
                value=f"${player['balance'] - asset['cost']:,}",
                inline=True
            )
            embed.add_field(
                name="📊 New Company Income",
                value=f"${self.company['current_income'] + asset['boost']:,}/30s",
                inline=True
            )
            embed.add_field(
                name="🕐 New Income/Hour",
                value=f"${(self.company['current_income'] + asset['boost']) * 120:,}",
                inline=True
            )
            
            embed.set_footer(text=f"Type: {asset['type'].capitalize()}")
            embed.timestamp = discord.utils.utcnow()
            
            await interaction.response.edit_message(embed=embed, view=None)
            
        except Exception as e:
            print(f"Error purchasing asset: {e}")
            import traceback
            traceback.print_exc()
            await interaction.response.send_message(
                f"❌ An error occurred while purchasing the asset: {str(e)}",
                ephemeral=True
            )
    
    async def back_to_categories(self, interaction: discord.Interaction):
        """Go back to category selection"""
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message(
                "❌ This isn't your upgrade menu!", 
                ephemeral=True
            )
        
        # Refresh data
        player = await db.get_player(str(self.user_id))
        current_assets = await db.get_company_assets(self.company['id'])
        company = await db.get_company_by_id(self.company['id'])
        
        # Show category selection again
        view = AssetCategoryView(self.user_id, company, player, current_assets)
        
        # Asset type emojis
        type_emojis = {
            'upgrade': '🔧',
            'expansion': '🏗️',
            'marketing': '📢'
        }
        
        # Count assets by type
        available_assets = ASSET_TYPES[company['rank']]
        asset_counts = {'upgrade': 0, 'expansion': 0, 'marketing': 0}
        for asset in available_assets:
            asset_counts[asset['type']] += 1
        
        embed = discord.Embed(
            title=f"🏢 Upgrade {company['name']} - Select Category",
            description=f"**Rank {company['rank']} Company**\n\n"
                       f"Choose an asset category to view available upgrades.\n\n"
                       f"**Current Company Stats:**\n"
                       f"💰 Income: ${company['current_income']:,}/30s\n"
                       f"📊 Base Income: ${company['base_income']:,}/30s\n"
                       f"🎯 Total Assets: {len(current_assets)}\n\n"
                       f"**Available Categories:**\n"
                       f"{type_emojis['upgrade']} **Upgrades** - {asset_counts['upgrade']} available\n"
                       f"{type_emojis['expansion']} **Expansions** - {asset_counts['expansion']} available\n"
                       f"{type_emojis['marketing']} **Marketing** - {asset_counts['marketing']} available",
            color=get_rank_color(company['rank'])
        )
        
        embed.add_field(name="💰 Your Balance", value=f"${player['balance']:,}", inline=True)
        embed.add_field(name="📈 Income/Hour", value=f"${company['current_income'] * 120:,}", inline=True)
        embed.set_footer(text="Select a category to view available assets")
        
        await interaction.response.edit_message(embed=embed, view=view)


class DisbandCompanyView(discord.ui.View):
    """View for disbanding a company"""
    def __init__(self, user_id: int, companies: list):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.companies = companies
        
        # Create select menu
        options = []
        for company in companies:
            options.append(discord.SelectOption(
                label=company['name'],
                description=f"Rank {company['rank']} • ${company['current_income']:,}/30s",
                value=str(company['id']),
                emoji="🏢"
            ))
        
        select = discord.ui.Select(
            placeholder="Choose a company to disband...",
            options=options,
            custom_id="company_select"
        )
        select.callback = self.company_selected
        self.add_item(select)
    
    async def company_selected(self, interaction: discord.Interaction):
        """Handle company selection"""
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message(
                "❌ This isn't your menu!", 
                ephemeral=True
            )
        
        company_id = int(interaction.data['values'][0])
        company = next((c for c in self.companies if c['id'] == company_id), None)
        
        if not company:
            return await interaction.response.send_message(
                "❌ Company not found!", 
                ephemeral=True
            )
        
        # Show confirmation
        view = DisbandConfirmView(self.user_id, company, interaction.client)
        
        embed = discord.Embed(
            title="⚠️ Confirm Disbandment",
            description=f"Are you sure you want to disband **{company['name']}**?\n\n"
                       f"**This action cannot be undone!**\n\n"
                       f"Your company thread will be deleted and all progress will be lost.",
            color=discord.Color.red()
        )
        
        embed.add_field(name="Company", value=company['name'], inline=True)
        embed.add_field(name="Rank", value=company['rank'], inline=True)
        embed.add_field(name="Income", value=f"${company['current_income']:,}/30s", inline=True)
        
        embed.set_footer(text="Click the button below to confirm")
        
        await interaction.response.edit_message(embed=embed, view=view)


class DisbandConfirmView(discord.ui.View):
    """View for confirming company disbandment"""
    def __init__(self, user_id: int, company: dict, bot):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.company = company
        self.bot = bot
    
    @discord.ui.button(label="✅ Yes, Disband Company", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ This isn't your company!", ephemeral=True)
        
        # Delete company from database
        await db.delete_company(self.company['id'])
        
        # Delete thread if exists
        if self.company['thread_id']:
            try:
                thread = self.bot.get_channel(int(self.company['thread_id']))
                if not thread:
                    thread = await self.bot.fetch_channel(int(self.company['thread_id']))
                
                if thread:
                    await thread.delete()
            except Exception as e:
                print(f"Failed to delete thread {self.company['thread_id']}: {e}")
        
        embed = discord.Embed(
            title="✅ Company Disbanded",
            description=f"**{self.company['name']}** has been disbanded.",
            color=discord.Color.green()
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ This isn't your company!", ephemeral=True)
        
        await interaction.response.edit_message(content="❌ Disbandment cancelled.", embed=None, view=None)


class RenameCompanyView(discord.ui.View):
    """View for renaming a company"""
    def __init__(self, user_id: int, companies: list, new_name: str, bot):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.companies = companies
        self.new_name = new_name
        self.bot = bot
        
        # Create select menu
        options = []
        for company in companies:
            options.append(discord.SelectOption(
                label=company['name'],
                description=f"Rank {company['rank']}",
                value=str(company['id']),
                emoji="🏢"
            ))
        
        select = discord.ui.Select(
            placeholder="Choose a company to rename...",
            options=options,
            custom_id="company_select"
        )
        select.callback = self.company_selected
        self.add_item(select)
    
    async def company_selected(self, interaction: discord.Interaction):
        """Handle company selection and rename"""
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message(
                "❌ This isn't your menu!", 
                ephemeral=True
            )
        
        company_id = int(interaction.data['values'][0])
        company = next((c for c in self.companies if c['id'] == company_id), None)
        
        if not company:
            return await interaction.response.send_message(
                "❌ Company not found!", 
                ephemeral=True
            )
        
        old_name = company['name']
        
        # Rename company
        await db.rename_company(company_id, self.new_name)
        
        # Update thread name if exists
        if company['thread_id']:
            try:
                thread = self.bot.get_channel(int(company['thread_id']))
                if not thread:
                    thread = await self.bot.fetch_channel(int(company['thread_id']))
                
                if thread:
                    await thread.edit(name=self.new_name)
            except Exception as e:
                print(f"Failed to rename thread: {e}")
        
        embed = discord.Embed(
            title="✅ Company Renamed",
            description=f"**{old_name}** has been renamed to **{self.new_name}**!",
            color=discord.Color.green()
        )
        
        await interaction.response.edit_message(embed=embed, view=None)


async def setup(bot):
    await bot.add_cog(CompanyCommands(bot))
