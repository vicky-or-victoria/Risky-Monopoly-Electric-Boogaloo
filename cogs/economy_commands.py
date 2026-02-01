# Economy commands: balance, loans, collect

import discord
from discord import app_commands
from discord.ext import commands
import os
from datetime import datetime, timedelta

import database as db
from registration_check import check_registration

# Loan tiers - designed to cover upgrades, NOT next rank company purchases
LOAN_TIERS = {
    'F': {'amount': 2000, 'description': 'Small loan for F-rank upgrades', 'days': 4},
    'E': {'amount': 6000, 'description': 'Loan for E-rank upgrades', 'days': 4},
    'D': {'amount': 25000, 'description': 'Loan for D-rank upgrades', 'days': 5},
    'C': {'amount': 80000, 'description': 'Loan for C-rank upgrades', 'days': 5},
    'B': {'amount': 300000, 'description': 'Loan for B-rank upgrades', 'days': 7},
    'A': {'amount': 1200000, 'description': 'Loan for A-rank upgrades', 'days': 7},
    'S': {'amount': 4500000, 'description': 'Loan for S-rank upgrades', 'days': 10},
    'SS': {'amount': 15000000, 'description': 'Loan for SS-rank upgrades', 'days': 10},
    'SSR': {'amount': 50000000, 'description': 'Loan for SSR-rank upgrades', 'days': 14},
}

class LoanTierSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=f"Tier {tier} - ${LOAN_TIERS[tier]['amount']:,}",
                description=f"{LOAN_TIERS[tier]['description']} ({LOAN_TIERS[tier]['days']} days)",
                value=tier,
                emoji="💰"
            )
            for tier in ['F', 'E', 'D', 'C', 'B', 'A', 'S', 'SS', 'SSR']
        ]
        
        super().__init__(
            placeholder="Choose a loan tier...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        tier = self.values[0]
        self.view.selected_tier = tier
        
        # Move to company selection
        await self.view.show_company_selection(interaction, tier)

class CompanyCollateralSelect(discord.ui.Select):
    def __init__(self, companies, tier, already_pledged_ids=None):
        self.tier = tier
        
        # Filter companies to only show those matching the loan tier
        # AND exclude any already pledged as collateral on an active loan
        already_pledged_ids = already_pledged_ids or set()
        matching_companies = [
            c for c in companies
            if c['rank'] == tier and c['id'] not in already_pledged_ids
        ]
        
        options = []
        
        # Only show placeholder option if no eligible companies remain
        if not matching_companies:
            all_of_tier = [c for c in companies if c['rank'] == tier]
            if all_of_tier:
                # Companies exist but every one is already pledged
                options.append(
                    discord.SelectOption(
                        label="No Available Companies",
                        description=f"All your Rank {tier} companies are already pledged as collateral",
                        value="none",
                        emoji="❌"
                    )
                )
            else:
                options.append(
                    discord.SelectOption(
                        label="No Matching Companies",
                        description=f"You need a Rank {tier} company for this loan tier",
                        value="none",
                        emoji="❌"
                    )
                )
        else:
            # Add matching company options
            for i, company in enumerate(matching_companies):
                options.append(
                    discord.SelectOption(
                        label=f"#{company['id']} - {company['name']}",
                        description=f"{company['rank']} Rank - ${company['current_income']:,}/30s",
                        value=str(company['id']),
                        emoji="🏢"
                    )
                )
        
        super().__init__(
            placeholder=f"Choose Rank {tier} company as collateral..." if matching_companies else "No eligible companies",
            min_values=1,
            max_values=1,
            options=options[:25],  # Discord limit
            disabled=not matching_companies  # Disable if no matching companies
        )
    
    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            return await interaction.response.send_message(
                f"❌ No eligible Rank {self.tier} company available. "
                f"Either you don't have one, or all of them are already pledged as collateral on active loans.",
                ephemeral=True
            )
        
        company_id = int(self.values[0])
        
        # Process the loan
        await self.view.process_loan(interaction, self.tier, company_id)

class LoanRequestView(discord.ui.View):
    def __init__(self, user_id: int, companies: list, interest_rate: float):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.companies = companies
        self.interest_rate = interest_rate
        self.selected_tier = None
        
        # Add tier selector
        self.add_item(LoanTierSelect())
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ This is not your loan request!",
                ephemeral=True
            )
            return False
        return True
    
    async def show_company_selection(self, interaction: discord.Interaction, tier: str):
        """Show company selection after tier is chosen"""
        loan_info = LOAN_TIERS[tier]
        
        # Filter companies to matching rank
        matching_companies = [c for c in self.companies if c['rank'] == tier]
        
        # Check if user has a matching rank company at all
        if not matching_companies:
            return await interaction.response.send_message(
                f"❌ You need a **Rank {tier}** company to request this loan tier!\n\n"
                f"💡 Create a Rank {tier} company first, then come back to request this loan.",
                ephemeral=True
            )
        
        # Fetch company IDs already pledged as collateral on active (unpaid) loans
        active_loans = await db.get_player_loans(str(self.user_id), unpaid_only=True)
        already_pledged_ids = {loan['company_id'] for loan in active_loans if loan.get('company_id')}
        
        # Filter out pledged companies for the eligibility check
        available_companies = [c for c in matching_companies if c['id'] not in already_pledged_ids]
        
        if not available_companies:
            return await interaction.response.send_message(
                f"❌ All of your Rank {tier} companies are already pledged as collateral on active loans.\n\n"
                f"💡 Pay off an existing loan first, or create a new Rank {tier} company.",
                ephemeral=True
            )
        
        # Create new view with company selector
        new_view = discord.ui.View(timeout=180)
        new_view.user_id = self.user_id
        new_view.interest_rate = self.interest_rate
        new_view.process_loan = self.process_loan
        
        # Add company selector (exclude already-pledged companies)
        company_select = CompanyCollateralSelect(self.companies, tier, already_pledged_ids)
        new_view.add_item(company_select)
        
        # Add cancel button
        cancel_button = discord.ui.Button(
            label="Cancel",
            style=discord.ButtonStyle.danger,
            emoji="❌"
        )
        
        async def cancel_callback(button_interaction: discord.Interaction):
            if button_interaction.user.id != self.user_id:
                return await button_interaction.response.send_message(
                    "❌ This is not your loan request!",
                    ephemeral=True
                )
            await button_interaction.response.edit_message(
                content="❌ Loan request cancelled.",
                embed=None,
                view=None
            )
        
        cancel_button.callback = cancel_callback
        new_view.add_item(cancel_button)
        
        # Show collateral selection
        total_owed = int(loan_info['amount'] * (1 + self.interest_rate / 100))
        
        embed = discord.Embed(
            title=f"🏦 Loan Request - Tier {tier}",
            description=f"You're requesting a **${loan_info['amount']:,}** loan.\n\n"
                       f"✅ You have **{len(available_companies)}** available Rank {tier} compan{'y' if len(available_companies) == 1 else 'ies'}.",
            color=discord.Color.blue()
        )
        embed.add_field(name="💰 Amount", value=f"${loan_info['amount']:,}", inline=True)
        embed.add_field(name="📈 Interest", value=f"{self.interest_rate}%", inline=True)
        embed.add_field(name="💸 Total to Repay", value=f"${total_owed:,}", inline=True)
        embed.add_field(name="📅 Repayment Period", value=f"{loan_info['days']} days", inline=True)
        embed.add_field(name="ℹ️ Purpose", value=loan_info['description'], inline=False)
        embed.add_field(
            name="🏢 Collateral (REQUIRED)",
            value=f"⚠️ **You must select a Rank {tier} company as collateral.**\n"
                  f"If you default on this loan, the collateral company will be **liquidated**!",
            inline=False
        )
        embed.set_footer(text=f"Select which Rank {tier} company to use as collateral")
        
        await interaction.response.edit_message(embed=embed, view=new_view)
    
    async def process_loan(self, interaction: discord.Interaction, tier: str, company_id: int):
        """Process the loan after tier and collateral are selected"""
        await interaction.response.defer()
        
        # CHECK MAINTENANCE MODE
        try:
            import bot_maintenance
            if bot_maintenance.is_bot_shutdown():
                return await interaction.followup.send(
                    bot_maintenance.get_shutdown_message(),
                    ephemeral=True
                )
        except:
            pass
        
        try:
            loan_info = LOAN_TIERS[tier]
            amount = loan_info['amount']
            due_days = loan_info['days']
            
            # Get company info (REQUIRED)
            company = await db.get_company_by_id(company_id)
            if not company or company['owner_id'] != str(self.user_id):
                return await interaction.followup.send(
                    "❌ Invalid company selected!",
                    ephemeral=True
                )
            
            # Verify company rank matches loan tier
            if company['rank'] != tier:
                return await interaction.followup.send(
                    f"❌ Company rank mismatch! You need a Rank {tier} company for this loan tier.",
                    ephemeral=True
                )
            
            # Verify this company is not already pledged on another active loan
            existing_loans = await db.get_player_loans(str(self.user_id), unpaid_only=True)
            for existing in existing_loans:
                if existing.get('company_id') == company_id:
                    return await interaction.followup.send(
                        f"❌ **{company['name']}** is already pledged as collateral on Loan #{existing['id']}. "
                        f"Pay off that loan first or choose a different company.",
                        ephemeral=True
                    )
            
            # Calculate loan terms
            total_owed = int(amount * (1 + self.interest_rate / 100))
            
            # Create embed for loan thread
            loan_embed = discord.Embed(
                title="🏦 Loan Agreement",
                description=f"**{tier}-Tier Loan** issued to <@{self.user_id}>",
                color=discord.Color.blue()
            )
            loan_embed.add_field(name="💵 Loan Tier", value=tier, inline=True)
            loan_embed.add_field(name="💰 Principal", value=f"${amount:,}", inline=True)
            loan_embed.add_field(name="📈 Interest", value=f"{self.interest_rate}%", inline=True)
            loan_embed.add_field(name="💸 Total Owed", value=f"${total_owed:,}", inline=True)
            loan_embed.add_field(
                name="📅 Due Date", 
                value=discord.utils.format_dt(discord.utils.utcnow() + timedelta(days=due_days), 'D'), 
                inline=True
            )
            loan_embed.add_field(name="🏢 Collateral", value=f"{company['name']} (Rank {company['rank']})", inline=True)
            loan_embed.add_field(name="ℹ️ Purpose", value=loan_info['description'], inline=False)
            loan_embed.set_footer(text="⚠️ Failure to repay by due date will result in company liquidation!")
            loan_embed.timestamp = discord.utils.utcnow()
            
            # Get the forum channel
            forum_channel = interaction.channel
            if isinstance(interaction.channel, discord.Thread):
                forum_channel = interaction.channel.parent
            
            # Create thread in the forum
            # ForumChannel.create_thread() returns a ThreadWithMessage object
            # with .thread and .message attributes (not a tuple).
            thread_result = await forum_channel.create_thread(
                name=f"💳 Loan - {interaction.user.name} - ${amount:,} ({tier})",
                content=f"<@{self.user_id}>'s loan is being processed...",
                auto_archive_duration=10080  # 7 days
            )
            
            # Extract thread and its starter message from the result object
            thread = thread_result.thread
            starter_message = thread_result.message
            
            # Send the embed
            embed_message = await thread.send(embed=loan_embed)
            await embed_message.pin()
            
            # Create loan in database
            due_date = datetime.utcnow() + timedelta(days=due_days)
            loan = await db.create_loan(
                borrower_id=str(self.user_id),
                company_id=company_id,
                principal=amount,
                interest_rate=self.interest_rate,
                total_owed=total_owed,
                loan_tier=tier,
                due_date=due_date,
                thread_id=str(thread.id)
            )
            
            # Store the embed message ID in the database
            await db.set_loan_embed_message(loan['id'], str(embed_message.id))
            
            # Give money to player
            await db.update_player_balance(str(self.user_id), amount)
            player = await db.get_player(str(self.user_id))
            
            # Edit the starter message to show approval
            if starter_message:
                await starter_message.edit(content=f"✅ Loan #{loan['id']} approved for <@{self.user_id}>")
            else:
                # Safety fallback: fetch the thread's first message by ID
                try:
                    first_msg = await thread.fetch_message(thread.id)
                    if first_msg and "being processed" in first_msg.content:
                        await first_msg.edit(content=f"✅ Loan #{loan['id']} approved for <@{self.user_id}>")
                except Exception as e:
                    print(f"Warning: could not edit starter message: {e}")
            
            # Send success message
            success_embed = discord.Embed(
                title="✅ Loan Approved!",
                description=f"Your **Tier {tier}** loan has been approved!",
                color=discord.Color.green()
            )
            success_embed.add_field(name="💰 Amount Received", value=f"${amount:,}", inline=True)
            success_embed.add_field(name="💸 Total to Repay", value=f"${total_owed:,}", inline=True)
            success_embed.add_field(name="📅 Due", value=discord.utils.format_dt(discord.utils.utcnow() + timedelta(days=due_days), "R"), inline=True)
            success_embed.add_field(name="💵 New Balance", value=f"${player['balance']:,}", inline=True)
            success_embed.add_field(name="🆔 Loan ID", value=f"#{loan['id']}", inline=True)
            success_embed.add_field(name="🏦 Loan Thread", value=thread.mention, inline=True)
            success_embed.set_footer(text=f"Use rm!pay-loan {loan['id']} to repay")
            success_embed.timestamp = discord.utils.utcnow()
            
            # Edit the original message
            await interaction.edit_original_response(
                content=None,
                embed=success_embed,
                view=None
            )
            
            print(f"✅ Successfully created loan #{loan['id']} for user {self.user_id}")
            
        except Exception as e:
            print(f"Error creating loan: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(
                '❌ Failed to process loan. Please try again.',
                ephemeral=True
            )

class PayLoanView(discord.ui.View):
    """View for selecting which loan to pay"""
    def __init__(self, user_id: int, loans: list, bot, cog):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.loans = loans
        self.bot = bot
        self.cog = cog
        
        # Create select menu for loans
        options = []
        for loan in loans:
            is_overdue = loan['due_date'] < datetime.now()
            status_emoji = "⚠️" if is_overdue else "💳"
            
            options.append(
                discord.SelectOption(
                    label=f"Loan #{loan['id']} - ${loan['total_owed']:,}",
                    description=f"Tier {loan.get('loan_tier', 'N/A')} | Due {loan['due_date'].strftime('%Y-%m-%d')} | {'OVERDUE' if is_overdue else 'Active'}",
                    value=str(loan['id']),
                    emoji=status_emoji
                )
            )
        
        select = discord.ui.Select(
            placeholder="Choose a loan to pay off...",
            min_values=1,
            max_values=1,
            options=options[:25]  # Discord limit
        )
        select.callback = self.loan_selected
        self.add_item(select)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ This is not your loan payment menu!",
                ephemeral=True
            )
            return False
        return True
    
    async def loan_selected(self, interaction: discord.Interaction):
        """Handle loan selection and process payment"""
        loan_id = int(interaction.data['values'][0])
        loan = await db.get_loan_by_id(loan_id)
        
        if not loan:
            return await interaction.response.send_message(
                "❌ Loan not found!",
                ephemeral=True
            )
        
        # Check if already paid
        if loan['is_paid']:
            return await interaction.response.send_message(
                "❌ This loan has already been paid!",
                ephemeral=True
            )
        
        # Check if player has enough money
        player = await db.get_player(str(self.user_id))
        if player['balance'] < loan['total_owed']:
            return await interaction.response.send_message(
                f"❌ Insufficient funds! You need ${loan['total_owed']:,} but only have ${player['balance']:,}.",
                ephemeral=True
            )
        
        # Show confirmation
        confirm_view = PayLoanConfirmView(self.user_id, loan, self.bot, self.cog)
        
        embed = discord.Embed(
            title="💳 Confirm Loan Payment",
            description=f"Are you sure you want to pay off **Loan #{loan_id}**?",
            color=discord.Color.blue()
        )
        embed.add_field(name="💵 Amount to Pay", value=f"${loan['total_owed']:,}", inline=True)
        embed.add_field(name="💰 Your Balance", value=f"${player['balance']:,}", inline=True)
        embed.add_field(name="💸 Remaining After", value=f"${player['balance'] - loan['total_owed']:,}", inline=True)
        
        if loan.get('company_id'):
            company = await db.get_company_by_id(loan['company_id'])
            if company:
                embed.add_field(name="🏢 Collateral", value=company['name'], inline=False)
        
        embed.set_footer(text="Click the button below to confirm payment")
        
        await interaction.response.edit_message(embed=embed, view=confirm_view)


class PayLoanConfirmView(discord.ui.View):
    """View for confirming loan payment"""
    def __init__(self, user_id: int, loan: dict, bot, cog):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.loan = loan
        self.bot = bot
        self.cog = cog
    
    @discord.ui.button(label="✅ Confirm Payment", style=discord.ButtonStyle.success)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ This is not your loan!", ephemeral=True)
        
        # Create a mock context for the payment processing
        class MockContext:
            def __init__(self, interaction):
                self.interaction = interaction
                self.author = interaction.user
                self.guild = interaction.guild
                self.channel = interaction.channel
                self.bot = interaction.client
            
            async def send(self, *args, **kwargs):
                return await self.interaction.followup.send(*args, **kwargs)
        
        ctx = MockContext(interaction)
        await interaction.response.defer()
        await self.cog._process_loan_payment(ctx, self.loan)
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(view=self)
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ This is not your loan!", ephemeral=True)
        
        await interaction.response.edit_message(content="❌ Payment cancelled.", embed=None, view=None)


class EconomyCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.interest_rate = float(os.getenv('LOAN_INTEREST_RATE', 5.0))
    
    @app_commands.command(name="balance", description="Check your current balance")
    async def balance(self, interaction: discord.Interaction):
        # Registration check
        if not await check_registration(interaction):
            return
        
        player = await db.get_player(str(interaction.user.id))
        
        if not player:
            await db.upsert_player(str(interaction.user.id), interaction.user.name)
            player = await db.get_player(str(interaction.user.id))
        
        embed = discord.Embed(
            title=f"💰 {interaction.user.name}'s Balance",
            description=f"**${player['balance']:,}**",
            color=discord.Color.gold()
        )
        
        # Get companies
        companies = await db.get_player_companies(str(interaction.user.id))
        if companies:
            total_per_30s = sum(c['current_income'] for c in companies)
            total_per_min = total_per_30s * 2
            total_per_hour = total_per_30s * 120
            embed.add_field(name="📊 Income/30s", value=f"${total_per_30s:,}", inline=True)
            embed.add_field(name="⏱️ Income/Min", value=f"${total_per_min:,}", inline=True)
            embed.add_field(name="🕐 Income/Hour", value=f"${total_per_hour:,}", inline=True)
            embed.add_field(name="🏢 Companies", value=str(len(companies)), inline=True)
        
        # Get loans
        loans = await db.get_player_loans(str(interaction.user.id), unpaid_only=True)
        if loans:
            total_debt = sum(loan['total_owed'] for loan in loans)
            embed.add_field(name="💳 Total Debt", value=f"${total_debt:,}", inline=True)
        
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @commands.hybrid_command(name="request-loan", description="Request a loan from the bank")
    async def request_loan(self, ctx: commands.Context):
        """Request a loan with interactive selection (similar to company creation)"""
        # Check if in bank forum
        settings = await db.get_guild_settings(str(ctx.guild.id))
        
        # Get the actual channel ID (could be thread or forum)
        channel_id = str(ctx.channel.id)
        if isinstance(ctx.channel, discord.Thread):
            # If in a thread, check the parent forum
            channel_id = str(ctx.channel.parent_id)
        
        # If settings exist and bank forum is set, validate
        if settings and settings.get('bank_forum_id'):
            if channel_id != settings['bank_forum_id']:
                if ctx.interaction:
                    return await ctx.send(
                        f'❌ This command can only be used in <#{settings["bank_forum_id"]}>!',
                        ephemeral=True
                    )
                else:
                    return await ctx.send(
                        f'❌ This command can only be used in <#{settings["bank_forum_id"]}>!',
                        delete_after=10
                    )
        elif not isinstance(ctx.channel, (discord.ForumChannel, discord.Thread)):
            # Fallback: at least check it's a forum-related channel
            if ctx.interaction:
                return await ctx.send(
                    '❌ This command can only be used in a forum channel! Please ask an admin to set up the bank forum with `/setup-bank-forum`.',
                    ephemeral=True
                )
            else:
                return await ctx.send(
                    '❌ This command can only be used in a forum channel! Please ask an admin to set up the bank forum with `/setup-bank-forum`.',
                    delete_after=10
                )
        
        # Ensure player exists
        await db.upsert_player(str(ctx.author.id), ctx.author.name)
        
        # Get player's companies
        companies = await db.get_player_companies(str(ctx.author.id))
        
        # Create interactive view
        view = LoanRequestView(ctx.author.id, companies, self.interest_rate)
        
        # Create initial embed
        embed = discord.Embed(
            title="🏦 Bank of Risky Monopoly",
            description="Welcome! Let's get you a loan to grow your empire.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="📋 How it works",
            value="1️⃣ Choose a loan tier based on your needs\n"
                  "2️⃣ Optionally select a company as collateral\n"
                  "3️⃣ Receive funds instantly!",
            inline=False
        )
        embed.add_field(
            name="💡 Loan Tiers",
            value="Each tier offers different amounts with different repayment periods.\n"
                  "Choose the tier that matches your business needs!",
            inline=False
        )
        embed.add_field(
            name="⚠️ Important",
            value=f"• Interest Rate: **{self.interest_rate}%**\n"
                  "• Failure to repay = **company liquidation** (if collateral provided)\n"
                  "• Repay using `rm!pay-loan <id>`",
            inline=False
        )
        embed.set_footer(text="Select a loan tier below to get started")
        
        # Send as ephemeral for both slash and prefix commands
        if ctx.interaction:
            await ctx.send(embed=embed, view=view, ephemeral=True)
        else:
            # For prefix commands, send ephemeral-like (delete after timeout)
            msg = await ctx.send(embed=embed, view=view)
            # Optionally delete the user's command message
            try:
                await ctx.message.delete()
            except:
                pass
    
    @app_commands.command(name="my-loans", description="View your active loans")
    async def my_loans(self, interaction: discord.Interaction):
        loans = await db.get_player_loans(str(interaction.user.id), unpaid_only=True)
        
        if not loans:
            return await interaction.response.send_message(
                '✅ You have no active loans!',
                ephemeral=True
            )
        
        embed = discord.Embed(
            title=f"💳 {interaction.user.name}'s Active Loans",
            description=f"You have {len(loans)} active loan(s)",
            color=discord.Color.red()
        )
        
        total_debt = 0
        for loan in loans:
            total_debt += loan['total_owed']
            
            company_info = "N/A"
            if loan['company_id']:
                company = await db.get_company_by_id(loan['company_id'])
                if company:
                    company_info = company['name']
            
            # Check if overdue
            is_overdue = loan['due_date'] < datetime.now()
            status = "⚠️ OVERDUE" if is_overdue else "✅ Active"
            
            field_value = (
                f"**Status:** {status}\n"
                f"**Tier:** {loan.get('loan_tier', 'Unknown')}\n"
                f"**Principal:** ${loan['principal_amount']:,}\n"
                f"**Total Owed:** ${loan['total_owed']:,}\n"
                f"**Interest Rate:** {loan['interest_rate']}%\n"
                f"**Due:** {discord.utils.format_dt(loan['due_date'], 'R')}\n"
                f"**Collateral:** {company_info}"
            )
            embed.add_field(
                name=f"Loan #{loan['id']}",
                value=field_value,
                inline=False
            )
        
        embed.set_footer(text=f"Total Debt: ${total_debt:,} | Use rm!pay-loan <id> to repay")
        embed.timestamp = discord.utils.utcnow()
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @commands.hybrid_command(name="pay-loan", description="Pay off a loan")
    async def pay_loan(self, ctx: commands.Context, loan_id: int = None):
        """Pay off a loan with interactive dropdown selection"""
        # Get player's unpaid loans
        loans = await db.get_player_loans(str(ctx.author.id), unpaid_only=True)
        
        if not loans:
            if ctx.interaction:
                return await ctx.send('✅ You have no active loans!', ephemeral=True)
            else:
                return await ctx.send('✅ You have no active loans!', delete_after=10)
        
        # If loan_id provided, pay that specific loan
        if loan_id is not None:
            loan = await db.get_loan_by_id(loan_id)
            
            if not loan:
                return await ctx.send('❌ Loan not found!', ephemeral=True if ctx.interaction else False, delete_after=None if ctx.interaction else 10)
            
            # Check if user owns the loan
            if loan['borrower_id'] != str(ctx.author.id):
                return await ctx.send('❌ This is not your loan!', ephemeral=True if ctx.interaction else False, delete_after=None if ctx.interaction else 10)
            
            # Check if already paid
            if loan['is_paid']:
                return await ctx.send('❌ This loan has already been paid!', ephemeral=True if ctx.interaction else False, delete_after=None if ctx.interaction else 10)
            
            # Check if player has enough money
            player = await db.get_player(str(ctx.author.id))
            if player['balance'] < loan['total_owed']:
                return await ctx.send(
                    f'❌ Insufficient funds! You need ${loan["total_owed"]:,} but only have ${player["balance"]:,}.',
                    ephemeral=True if ctx.interaction else False, delete_after=None if ctx.interaction else 10
                )
            
            # Process payment
            await self._process_loan_payment(ctx, loan)
            return
        
        # No loan_id provided, show interactive dropdown
        view = PayLoanView(ctx.author.id, loans, self.bot, self)
        
        embed = discord.Embed(
            title="💳 Pay Off Loan",
            description=f"You have **{len(loans)}** active loan(s). Select which loan you'd like to pay off:",
            color=discord.Color.blue()
        )
        
        player = await db.get_player(str(ctx.author.id))
        embed.add_field(name="💰 Your Balance", value=f"${player['balance']:,}", inline=False)
        embed.set_footer(text="Select a loan from the dropdown below")
        
        if ctx.interaction:
            await ctx.send(embed=embed, view=view, ephemeral=True)
        else:
            await ctx.send(embed=embed, view=view)
            try:
                await ctx.message.delete()
            except:
                pass
    
    async def _process_loan_payment(self, ctx: commands.Context, loan: dict):
        """Helper method to process a loan payment"""
        loan_id = loan['id']
        
        # Deduct payment and mark loan as paid
        await db.update_player_balance(str(ctx.author.id), -loan['total_owed'])
        await db.pay_loan(loan_id)
        
        updated_player = await db.get_player(str(ctx.author.id))
        
        embed = discord.Embed(
            title="✅ Loan Paid Off!",
            description=f"Loan #{loan_id} has been successfully repaid",
            color=discord.Color.green()
        )
        embed.add_field(name="💵 Amount Paid", value=f"${loan['total_owed']:,}", inline=True)
        embed.add_field(name="💰 Remaining Balance", value=f"${updated_player['balance']:,}", inline=True)
        embed.timestamp = discord.utils.utcnow()
        
        if ctx.interaction:
            await ctx.send(embed=embed)
        else:
            await ctx.send(embed=embed)
        
        # Update the loan thread embed and close/lock it
        if loan.get('thread_id') and loan.get('embed_message_id'):
            try:
                thread = self.bot.get_channel(int(loan['thread_id']))
                if not thread:
                    thread = await self.bot.fetch_channel(int(loan['thread_id']))
                
                if thread:
                    try:
                        # Update the embed message
                        message = await thread.fetch_message(int(loan['embed_message_id']))
                        
                        # Update the embed to show PAID
                        old_embed = message.embeds[0] if message.embeds else None
                        if old_embed:
                            new_embed = discord.Embed(
                                title="✅ Loan PAID",
                                description=old_embed.description,
                                color=discord.Color.green()
                            )
                            for field in old_embed.fields:
                                new_embed.add_field(name=field.name, value=field.value, inline=field.inline)
                            new_embed.add_field(name="💚 Status", value="PAID IN FULL", inline=False)
                            new_embed.set_footer(text="This loan has been fully repaid!")
                            new_embed.timestamp = discord.utils.utcnow()
                            
                            await message.edit(embed=new_embed)
                        
                        # Update the starter message (thread's first message)
                        try:
                            starter_message = await thread.fetch_message(thread.id)
                            if starter_message:
                                await starter_message.edit(content=f"✅ Loan #{loan_id} - PAID IN FULL by <@{loan['borrower_id']}>")
                        except Exception as e:
                            print(f"Error updating starter message: {e}")
                            
                        # Archive and lock the thread
                        await thread.edit(archived=True, locked=True)
                        print(f"✅ Closed and locked loan thread for loan #{loan_id}")
                    except Exception as e:
                        print(f"Error updating loan embed: {e}")
            except Exception as e:
                print(f"Error accessing loan thread: {e}")

async def setup(bot):
    await bot.add_cog(EconomyCommands(bot))
