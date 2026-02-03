# Boss Events System - Community Economic Crisis Events

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
import asyncio

import database as db
from cogs.admin_commands import is_admin_or_authorized


class ContributeModal(discord.ui.Modal, title="Contribute to Boss Event"):
    """Modal for players to contribute money to beat the boss event"""
    
    amount = discord.ui.TextInput(
        label="Amount to Contribute",
        placeholder="Enter the amount you want to contribute...",
        required=True,
        min_length=1,
        max_length=20
    )
    
    def __init__(self, boss_event_id: int, guild_id: str):
        super().__init__()
        self.boss_event_id = boss_event_id
        self.guild_id = guild_id
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle contribution submission"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Parse amount
            amount_str = self.amount.value.strip().replace(',', '').replace('$', '')
            try:
                amount = int(amount_str)
            except ValueError:
                return await interaction.followup.send(
                    '❌ Invalid amount! Please enter a valid number.',
                    ephemeral=True
                )
            
            if amount <= 0:
                return await interaction.followup.send(
                    '❌ Amount must be greater than 0!',
                    ephemeral=True
                )
            
            # Check if player has enough balance
            player = await db.get_player(str(interaction.user.id))
            if not player:
                return await interaction.followup.send(
                    '❌ You are not registered! Use `/register` first.',
                    ephemeral=True
                )
            
            if player['balance'] < amount:
                return await interaction.followup.send(
                    f'❌ Insufficient balance! You have ${player["balance"]:,} but need ${amount:,}.',
                    ephemeral=True
                )
            
            # Get boss event details
            boss_event = await db.get_boss_event(self.boss_event_id)
            if not boss_event:
                return await interaction.followup.send(
                    '❌ Boss event not found!',
                    ephemeral=True
                )
            
            if boss_event['is_completed']:
                return await interaction.followup.send(
                    '❌ This boss event has already been completed!',
                    ephemeral=True
                )
            
            # Add contribution
            await db.add_boss_contribution(
                self.boss_event_id,
                str(interaction.user.id),
                amount
            )
            
            # Deduct from player balance
            await db.update_player_balance(str(interaction.user.id), -amount)
            
            # Get updated boss event
            updated_boss = await db.get_boss_event(self.boss_event_id)
            
            # Update the boss event message
            await self.update_boss_embed(interaction.client, updated_boss)
            
            # Calculate progress
            progress_pct = min((updated_boss['current_progress'] / updated_boss['goal_amount']) * 100, 100)
            
            await interaction.followup.send(
                f'✅ Successfully contributed ${amount:,} to the boss event!\n'
                f'📊 Progress: {progress_pct:.1f}% (${updated_boss["current_progress"]:,} / ${updated_boss["goal_amount"]:,})',
                ephemeral=True
            )
            
            # Check if event is completed
            if updated_boss['current_progress'] >= updated_boss['goal_amount'] and not updated_boss['is_completed']:
                await db.complete_boss_event(self.boss_event_id)
                await self.announce_completion(interaction.client, updated_boss)
            
        except Exception as e:
            print(f"Error in contribution: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(
                f'❌ An error occurred: {e}',
                ephemeral=True
            )
    
    async def update_boss_embed(self, bot: commands.Bot, boss_event: dict):
        """Update the boss event embed with current progress"""
        try:
            channel = bot.get_channel(int(boss_event['channel_id']))
            if not channel:
                channel = await bot.fetch_channel(int(boss_event['channel_id']))
            
            if not channel:
                return
            
            message = await channel.fetch_message(int(boss_event['message_id']))
            if not message:
                return
            
            # Calculate progress
            progress_pct = min((boss_event['current_progress'] / boss_event['goal_amount']) * 100, 100)
            progress_bar = self.create_progress_bar(progress_pct)
            
            # Determine color based on progress
            if progress_pct >= 100:
                color = discord.Color.green()
            elif progress_pct >= 75:
                color = discord.Color.blue()
            elif progress_pct >= 50:
                color = discord.Color.gold()
            elif progress_pct >= 25:
                color = discord.Color.orange()
            else:
                color = discord.Color.red()
            
            embed = discord.Embed(
                title="# ▬▬▬▬▬ ECONOMIC CRISIS EVENT ▬▬▬▬▬",
                description=f"**{boss_event['name']}**\n\n{boss_event['description']}",
                color=color
            )
            
            embed.add_field(
                name="💰 Goal Amount",
                value=f"${boss_event['goal_amount']:,}",
                inline=True
            )
            embed.add_field(
                name="💵 Current Progress",
                value=f"${boss_event['current_progress']:,}",
                inline=True
            )
            embed.add_field(
                name="📊 Completion",
                value=f"{progress_pct:.1f}%",
                inline=True
            )
            embed.add_field(
                name="📈 Progress Bar",
                value=f"{progress_bar}",
                inline=False
            )
            
            # Get top contributors
            contributors = await db.get_boss_contributors(boss_event['id'], limit=5)
            if contributors:
                contrib_text = ""
                for i, contrib in enumerate(contributors, 1):
                    medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, "🔹")
                    user = bot.get_user(int(contrib['user_id']))
                    username = user.name if user else "Unknown User"
                    contrib_text += f"{medal} **{username}**: ${contrib['total_contributed']:,}\n"
                
                embed.add_field(
                    name="🏆 Top Contributors",
                    value=contrib_text,
                    inline=False
                )
            
            if boss_event['is_completed']:
                embed.add_field(
                    name="✅ EVENT COMPLETED",
                    value="The community has successfully overcome this economic crisis!",
                    inline=False
                )
            else:
                embed.add_field(
                    name="💡 How to Help",
                    value="Click the **Contribute** button below to donate money and help beat this crisis!",
                    inline=False
                )
            
            embed.set_footer(text=f"Boss Event ID: {boss_event['id']} | Community Event")
            embed.timestamp = discord.utils.utcnow()
            
            # Create view with buttons
            view = BossEventView(boss_event['id'], boss_event['guild_id'], boss_event['is_completed'])
            
            await message.edit(embed=embed, view=view)
            
        except Exception as e:
            print(f"Error updating boss embed: {e}")
            import traceback
            traceback.print_exc()
    
    def create_progress_bar(self, progress_pct: float, length: int = 20) -> str:
        """Create a visual progress bar"""
        filled = int((progress_pct / 100) * length)
        empty = length - filled
        bar = "█" * filled + "░" * empty
        return f"[{bar}] {progress_pct:.1f}%"
    
    async def announce_completion(self, bot: commands.Bot, boss_event: dict):
        """Announce the completion of a boss event"""
        try:
            channel = bot.get_channel(int(boss_event['channel_id']))
            if not channel:
                channel = await bot.fetch_channel(int(boss_event['channel_id']))
            
            if channel:
                embed = discord.Embed(
                    title="# ▬▬▬▬▬ CRISIS AVERTED! ▬▬▬▬▬",
                    description=(
                        f"**{boss_event['name']} has been overcome!**\n\n"
                        f"The community came together and contributed **${boss_event['current_progress']:,}** "
                        f"to successfully beat this economic crisis event!\n\n"
                        f"🎉 Congratulations to all contributors!"
                    ),
                    color=discord.Color.green()
                )
                
                # Get top contributors for celebration
                contributors = await db.get_boss_contributors(boss_event['id'], limit=10)
                if contributors:
                    contrib_text = ""
                    for i, contrib in enumerate(contributors, 1):
                        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, "🔹")
                        user = bot.get_user(int(contrib['user_id']))
                        username = user.name if user else "Unknown User"
                        contrib_text += f"{medal} **{username}**: ${contrib['total_contributed']:,}\n"
                    
                    embed.add_field(
                        name="🏆 Hall of Heroes",
                        value=contrib_text,
                        inline=False
                    )
                
                embed.set_footer(text="The economy is saved!")
                embed.timestamp = discord.utils.utcnow()
                
                await channel.send(embed=embed)
                
        except Exception as e:
            print(f"Error announcing completion: {e}")


class BossEventView(discord.ui.View):
    """View with buttons for boss events"""
    
    def __init__(self, boss_event_id: int, guild_id: str, is_completed: bool = False):
        super().__init__(timeout=None)  # Persistent view
        self.boss_event_id = boss_event_id
        self.guild_id = guild_id
        
        # Disable buttons if completed
        if is_completed:
            for item in self.children:
                item.disabled = True
    
    @discord.ui.button(label="💰 Contribute", style=discord.ButtonStyle.green, custom_id="boss_contribute")
    async def contribute_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open contribution modal"""
        modal = ContributeModal(self.boss_event_id, self.guild_id)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="📊 My Contributions", style=discord.ButtonStyle.blurple, custom_id="boss_my_contrib")
    async def my_contributions_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show user's contributions to this boss event"""
        contribution = await db.get_user_boss_contribution(self.boss_event_id, str(interaction.user.id))
        
        if not contribution or contribution['total_contributed'] == 0:
            await interaction.response.send_message(
                "❌ You haven't contributed to this boss event yet!",
                ephemeral=True
            )
        else:
            boss_event = await db.get_boss_event(self.boss_event_id)
            contribution_pct = (contribution['total_contributed'] / boss_event['goal_amount']) * 100
            
            embed = discord.Embed(
                title="💰 Your Contributions",
                description=f"**{boss_event['name']}**",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Total Contributed",
                value=f"${contribution['total_contributed']:,}",
                inline=True
            )
            embed.add_field(
                name="% of Goal",
                value=f"{contribution_pct:.2f}%",
                inline=True
            )
            embed.set_footer(text="Thank you for your contribution!")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)


class BossEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="create-boss-event", description="[ADMIN] Create a new boss event")
    @app_commands.describe(
        name="Name of the boss event",
        description="Description of the economic crisis",
        goal_amount="Total amount needed to beat the event"
    )
    async def create_boss_event(
        self,
        interaction: discord.Interaction,
        name: str,
        description: str,
        goal_amount: int
    ):
        """[ADMIN] Create a new boss event"""
        # Check admin permissions
        if not await is_admin_or_authorized(interaction):
            return await interaction.response.send_message(
                '❌ You need to be an admin, have an authorized admin role, or be the bot owner to use this command!',
                ephemeral=True
            )
        
        if goal_amount <= 0:
            return await interaction.response.send_message(
                '❌ Goal amount must be greater than 0!',
                ephemeral=True
            )
        
        try:
            # Create the boss event in database
            boss_event_id = await db.create_boss_event(
                str(interaction.guild.id),
                name,
                description,
                goal_amount
            )
            
            embed = discord.Embed(
                title="✅ Boss Event Created",
                description=f"**{name}** has been created!",
                color=discord.Color.green()
            )
            embed.add_field(name="Goal Amount", value=f"${goal_amount:,}", inline=True)
            embed.add_field(name="Event ID", value=f"#{boss_event_id}", inline=True)
            embed.add_field(
                name="Next Step",
                value=f"Use `/start-boss-event event_id:{boss_event_id}` to start this event!",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            print(f"Error creating boss event: {e}")
            import traceback
            traceback.print_exc()
            await interaction.response.send_message(
                f'❌ Error creating boss event: {e}',
                ephemeral=True
            )
    
    @app_commands.command(name="start-boss-event", description="[ADMIN] Start a boss event in this channel")
    @app_commands.describe(event_id="ID of the boss event to start")
    async def start_boss_event(self, interaction: discord.Interaction, event_id: int):
        """[ADMIN] Start a boss event in the current channel"""
        # Check admin permissions
        if not await is_admin_or_authorized(interaction):
            return await interaction.response.send_message(
                '❌ You need to be an admin, have an authorized admin role, or be the bot owner to use this command!',
                ephemeral=True
            )
        
        await interaction.response.defer()
        
        try:
            # Get boss event
            boss_event = await db.get_boss_event(event_id)
            if not boss_event:
                return await interaction.followup.send(
                    f'❌ Boss event #{event_id} not found!',
                    ephemeral=True
                )
            
            if boss_event['guild_id'] != str(interaction.guild.id):
                return await interaction.followup.send(
                    f'❌ This boss event belongs to a different server!',
                    ephemeral=True
                )
            
            if boss_event['message_id']:
                return await interaction.followup.send(
                    f'❌ This boss event has already been started!',
                    ephemeral=True
                )
            
            # Create the boss event embed
            progress_bar = self.create_progress_bar(0)
            
            embed = discord.Embed(
                title="# ▬▬▬▬▬ ECONOMIC CRISIS EVENT ▬▬▬▬▬",
                description=f"**{boss_event['name']}**\n\n{boss_event['description']}",
                color=discord.Color.red()
            )
            
            embed.add_field(
                name="💰 Goal Amount",
                value=f"${boss_event['goal_amount']:,}",
                inline=True
            )
            embed.add_field(
                name="💵 Current Progress",
                value=f"$0",
                inline=True
            )
            embed.add_field(
                name="📊 Completion",
                value=f"0.0%",
                inline=True
            )
            embed.add_field(
                name="📈 Progress Bar",
                value=f"{progress_bar}",
                inline=False
            )
            embed.add_field(
                name="💡 How to Help",
                value="Click the **Contribute** button below to donate money and help beat this crisis!",
                inline=False
            )
            
            embed.set_footer(text=f"Boss Event ID: {boss_event['id']} | Community Event")
            embed.timestamp = discord.utils.utcnow()
            
            # Create view with buttons
            view = BossEventView(boss_event['id'], boss_event['guild_id'])
            
            # Send the message
            message = await interaction.channel.send(embed=embed, view=view)
            
            # Update boss event with channel and message IDs
            await db.update_boss_event_message(
                event_id,
                str(interaction.channel.id),
                str(message.id)
            )
            
            await interaction.followup.send(
                f'✅ Boss event **{boss_event["name"]}** has been started!',
                ephemeral=True
            )
            
        except Exception as e:
            print(f"Error starting boss event: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(
                f'❌ Error starting boss event: {e}',
                ephemeral=True
            )
    
    @app_commands.command(name="list-boss-events", description="[ADMIN] List all boss events for this server")
    async def list_boss_events(self, interaction: discord.Interaction):
        """[ADMIN] List all boss events"""
        # Check admin permissions
        if not await is_admin_or_authorized(interaction):
            return await interaction.response.send_message(
                '❌ You need to be an admin, have an authorized admin role, or be the bot owner to use this command!',
                ephemeral=True
            )
        
        try:
            events = await db.get_guild_boss_events(str(interaction.guild.id))
            
            if not events:
                return await interaction.response.send_message(
                    '❌ No boss events found for this server!',
                    ephemeral=True
                )
            
            embed = discord.Embed(
                title="📋 Boss Events",
                description=f"All boss events for this server",
                color=discord.Color.blue()
            )
            
            for event in events:
                status = "✅ Completed" if event['is_completed'] else "🔴 Active" if event['message_id'] else "⏸️ Not Started"
                progress_pct = (event['current_progress'] / event['goal_amount']) * 100 if event['goal_amount'] > 0 else 0
                
                embed.add_field(
                    name=f"#{event['id']} - {event['name']} {status}",
                    value=(
                        f"**Goal:** ${event['goal_amount']:,}\n"
                        f"**Progress:** ${event['current_progress']:,} ({progress_pct:.1f}%)\n"
                        f"**Description:** {event['description'][:100]}..."
                    ),
                    inline=False
                )
            
            embed.set_footer(text=f"Total events: {len(events)}")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            print(f"Error listing boss events: {e}")
            import traceback
            traceback.print_exc()
            await interaction.response.send_message(
                f'❌ Error listing boss events: {e}',
                ephemeral=True
            )
    
    @app_commands.command(name="delete-boss-event", description="[ADMIN] Delete a boss event")
    @app_commands.describe(event_id="ID of the boss event to delete")
    async def delete_boss_event(self, interaction: discord.Interaction, event_id: int):
        """[ADMIN] Delete a boss event"""
        # Check admin permissions
        if not await is_admin_or_authorized(interaction):
            return await interaction.response.send_message(
                '❌ You need to be an admin, have an authorized admin role, or be the bot owner to use this command!',
                ephemeral=True
            )
        
        try:
            # Get boss event to verify it belongs to this guild
            boss_event = await db.get_boss_event(event_id)
            if not boss_event:
                return await interaction.response.send_message(
                    f'❌ Boss event #{event_id} not found!',
                    ephemeral=True
                )
            
            if boss_event['guild_id'] != str(interaction.guild.id):
                return await interaction.response.send_message(
                    f'❌ This boss event belongs to a different server!',
                    ephemeral=True
                )
            
            await db.delete_boss_event(event_id)
            
            await interaction.response.send_message(
                f'✅ Boss event **{boss_event["name"]}** (#{event_id}) has been deleted!',
                ephemeral=True
            )
            
        except Exception as e:
            print(f"Error deleting boss event: {e}")
            import traceback
            traceback.print_exc()
            await interaction.response.send_message(
                f'❌ Error deleting boss event: {e}',
                ephemeral=True
            )
    
    def create_progress_bar(self, progress_pct: float, length: int = 20) -> str:
        """Create a visual progress bar"""
        filled = int((progress_pct / 100) * length)
        empty = length - filled
        bar = "█" * filled + "░" * empty
        return f"[{bar}] {progress_pct:.1f}%"
    
    @app_commands.command(name="grant-buff", description="[ADMIN] Grant a temporary server-wide buff")
    @app_commands.describe(
        buff_type="Type of buff to grant",
        buff_value="Percentage value of the buff (e.g., 25 for +25%)",
        duration_hours="How many hours the buff should last",
        description="Description of the buff"
    )
    @app_commands.choices(buff_type=[
        app_commands.Choice(name="Income Generation Boost", value="income_boost"),
        app_commands.Choice(name="Stock Trading Tax Reduction", value="stock_tax_reduction"),
        app_commands.Choice(name="Stock Trading Profit Increase", value="stock_profit_boost"),
        app_commands.Choice(name="Company Income Boost", value="company_income"),
        app_commands.Choice(name="Global Efficiency Boost", value="global_efficiency")
    ])
    async def grant_buff(
        self,
        interaction: discord.Interaction,
        buff_type: app_commands.Choice[str],
        buff_value: float,
        duration_hours: int,
        description: str
    ):
        """[ADMIN] Grant a temporary server-wide buff"""
        # Check admin permissions
        if not await is_admin_or_authorized(interaction):
            return await interaction.response.send_message(
                '❌ You need to be an admin, have an authorized admin role, or be the bot owner to use this command!',
                ephemeral=True
            )
        
        if buff_value <= 0:
            return await interaction.response.send_message(
                '❌ Buff value must be greater than 0!',
                ephemeral=True
            )
        
        if duration_hours <= 0:
            return await interaction.response.send_message(
                '❌ Duration must be at least 1 hour!',
                ephemeral=True
            )
        
        try:
            # Create the buff
            buff_id = await db.create_temporary_buff(
                str(interaction.guild.id),
                buff_type.value,
                buff_value,
                duration_hours,
                description
            )
            
            # Determine color based on buff type
            buff_colors = {
                'income_boost': discord.Color.green(),
                'stock_tax_reduction': discord.Color.blue(),
                'stock_profit_boost': discord.Color.gold(),
                'company_income': discord.Color.purple(),
                'global_efficiency': discord.Color.orange()
            }
            color = buff_colors.get(buff_type.value, discord.Color.green())
            
            # Determine emoji based on buff type
            buff_emojis = {
                'income_boost': '💰',
                'stock_tax_reduction': '📉',
                'stock_profit_boost': '📈',
                'company_income': '🏢',
                'global_efficiency': '⚡'
            }
            emoji = buff_emojis.get(buff_type.value, '✨')
            
            embed = discord.Embed(
                title=f"{emoji} Server Buff Activated!",
                description=f"**{buff_type.name}**\n\n{description}",
                color=color
            )
            embed.add_field(name="💪 Buff Value", value=f"+{buff_value}%", inline=True)
            embed.add_field(name="⏱️ Duration", value=f"{duration_hours} hours", inline=True)
            embed.add_field(name="🆔 Buff ID", value=f"#{buff_id}", inline=True)
            
            # Calculate expiry time
            from datetime import datetime, timedelta
            expires_at = datetime.now() + timedelta(hours=duration_hours)
            embed.add_field(
                name="⏰ Expires At",
                value=f"<t:{int(expires_at.timestamp())}:F>",
                inline=False
            )
            
            embed.set_footer(text="This buff applies to all players in the server!")
            embed.timestamp = discord.utils.utcnow()
            
            # Send announcement in current channel
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            print(f"Error granting buff: {e}")
            import traceback
            traceback.print_exc()
            await interaction.response.send_message(
                f'❌ Error granting buff: {e}',
                ephemeral=True
            )
    
    @app_commands.command(name="view-buffs", description="View all active server buffs")
    async def view_buffs(self, interaction: discord.Interaction):
        """View all active server buffs"""
        try:
            buffs = await db.get_active_buffs(str(interaction.guild.id))
            
            if not buffs:
                embed = discord.Embed(
                    title="📋 Active Server Buffs",
                    description="No active buffs at the moment!",
                    color=discord.Color.orange()
                )
                return await interaction.response.send_message(embed=embed)
            
            embed = discord.Embed(
                title="✨ Active Server Buffs",
                description=f"Current buffs active in this server:",
                color=discord.Color.green()
            )
            
            # Buff type names
            buff_names = {
                'income_boost': '💰 Income Generation Boost',
                'stock_tax_reduction': '📉 Stock Trading Tax Reduction',
                'stock_profit_boost': '📈 Stock Trading Profit Increase',
                'company_income': '🏢 Company Income Boost',
                'global_efficiency': '⚡ Global Efficiency Boost'
            }
            
            for buff in buffs:
                buff_name = buff_names.get(buff['buff_type'], buff['buff_type'])
                
                from datetime import datetime
                time_left = buff['expires_at'] - datetime.now()
                hours_left = int(time_left.total_seconds() / 3600)
                minutes_left = int((time_left.total_seconds() % 3600) / 60)
                
                embed.add_field(
                    name=f"{buff_name}",
                    value=(
                        f"**Value:** +{buff['buff_value']}%\n"
                        f"**Description:** {buff['description']}\n"
                        f"**Time Left:** {hours_left}h {minutes_left}m\n"
                        f"**Expires:** <t:{int(buff['expires_at'].timestamp())}:R>\n"
                        f"**Buff ID:** #{buff['id']}"
                    ),
                    inline=False
                )
            
            embed.set_footer(text=f"Total active buffs: {len(buffs)}")
            embed.timestamp = discord.utils.utcnow()
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            print(f"Error viewing buffs: {e}")
            import traceback
            traceback.print_exc()
            await interaction.response.send_message(
                f'❌ Error viewing buffs: {e}',
                ephemeral=True
            )
    
    @app_commands.command(name="remove-buff", description="[ADMIN] Remove an active buff")
    @app_commands.describe(buff_id="ID of the buff to remove")
    async def remove_buff(self, interaction: discord.Interaction, buff_id: int):
        """[ADMIN] Remove an active buff"""
        # Check admin permissions
        if not await is_admin_or_authorized(interaction):
            return await interaction.response.send_message(
                '❌ You need to be an admin, have an authorized admin role, or be the bot owner to use this command!',
                ephemeral=True
            )
        
        try:
            # Get all buffs to verify this one belongs to the guild
            all_buffs = await db.get_all_guild_buffs(str(interaction.guild.id))
            buff = next((b for b in all_buffs if b['id'] == buff_id), None)
            
            if not buff:
                return await interaction.response.send_message(
                    f'❌ Buff #{buff_id} not found in this server!',
                    ephemeral=True
                )
            
            if not buff['is_active']:
                return await interaction.response.send_message(
                    f'❌ Buff #{buff_id} is already inactive!',
                    ephemeral=True
                )
            
            await db.deactivate_buff(buff_id)
            
            embed = discord.Embed(
                title="🚫 Buff Removed",
                description=f"**{buff['description']}**\n\nThis buff has been deactivated.",
                color=discord.Color.red()
            )
            embed.add_field(name="Buff Type", value=buff['buff_type'], inline=True)
            embed.add_field(name="Buff Value", value=f"+{buff['buff_value']}%", inline=True)
            embed.set_footer(text=f"Buff ID: #{buff_id}")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            print(f"Error removing buff: {e}")
            import traceback
            traceback.print_exc()
            await interaction.response.send_message(
                f'❌ Error removing buff: {e}',
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(BossEvents(bot))
