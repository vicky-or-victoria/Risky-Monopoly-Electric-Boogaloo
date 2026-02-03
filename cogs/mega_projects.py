# Mega Projects System for Corporations

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

import database as db
from cogs.admin_commands import is_admin_or_authorized


class MegaProjectSelectView(discord.ui.View):
    """View for selecting a mega project"""
    def __init__(self, corporation_id: int, leader_id: str, projects: list):
        super().__init__(timeout=180)
        self.corporation_id = corporation_id
        self.leader_id = leader_id
        
        # Create select menu
        options = []
        for project in projects:
            # Display cost in billions for clarity
            if project['total_cost'] >= 1_000_000_000:
                cost_billions = project['total_cost'] / 1_000_000_000
                cost_display = f"${cost_billions:.1f}B"
            else:
                cost_millions = project['total_cost'] / 1_000_000
                cost_display = f"${cost_millions:.1f}M"
            
            options.append(
                discord.SelectOption(
                    label=project['name'],
                    description=f"{cost_display} - {project['buff_type']}",
                    value=str(project['id'])
                )
            )
        
        select = discord.ui.Select(
            placeholder="Choose a mega project...",
            options=options,
            custom_id="project_select"
        )
        select.callback = self.select_callback
        self.add_item(select)
    
    def _create_progress_bar(self, progress_pct: float, length: int = 20) -> str:
        """Create a visual progress bar"""
        filled = int((progress_pct / 100) * length)
        empty = length - filled
        bar = "█" * filled + "░" * empty
        return f"[{bar}]"
    
    async def select_callback(self, interaction: discord.Interaction):
        """Handle project selection"""
        # Defer immediately to prevent timeout
        await interaction.response.defer()
        
        user_id_str = str(interaction.user.id)
        
        # Debug logging
        print(f"[DEBUG select_callback] User ID: {user_id_str}, Leader ID: {self.leader_id}, Match: {user_id_str == self.leader_id}")
        
        if user_id_str != self.leader_id:
            return await interaction.followup.send(
                f"❌ Only the corporation leader can select mega projects!",
                ephemeral=True
            )
        
        project_id = int(interaction.values[0])
        
        # Start the project
        try:
            await db.start_mega_project(self.corporation_id, project_id)
            
            # Get project details
            projects = await db.get_all_mega_projects()
            selected_project = next((p for p in projects if p['id'] == project_id), None)
            
            if selected_project:
                # Delete the original view-mega-projects message
                try:
                    await interaction.message.delete()
                except:
                    pass  # If deletion fails, just continue
                
                # Display cost in billions for clarity
                if selected_project['total_cost'] >= 1_000_000_000:
                    cost_billions = selected_project['total_cost'] / 1_000_000_000
                    cost_display = f"${cost_billions:.1f}B"
                else:
                    cost_display = f"${selected_project['total_cost']:,}"
                
                # Create progress bar
                progress_pct = 0
                progress_bar = self._create_progress_bar(progress_pct)
                
                embed = discord.Embed(
                    title="🏗️ Active Mega Project",
                    description=f"**{selected_project['name']}**\n{selected_project['description']}",
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="💰 Total Cost",
                    value=cost_display,
                    inline=True
                )
                embed.add_field(
                    name="🎁 Buff",
                    value=f"{selected_project['buff_type']}: +{selected_project['buff_value']}%",
                    inline=True
                )
                embed.add_field(
                    name="📊 Progress",
                    value=f"{progress_bar}\n$0 / {cost_display} (0.0%)",
                    inline=False
                )
                embed.add_field(
                    name="💡 How to Contribute",
                    value="Use `/contribute-to-project <amount>` to help complete this project!",
                    inline=False
                )
                embed.set_footer(text=f"Project ID: {selected_project['id']}")
                
                # Pin the message
                message = await interaction.followup.send(embed=embed)
                try:
                    await message.pin()
                except:
                    pass  # If pinning fails, just continue
                    
                # Store the message ID for future updates
                await db.set_corporation_project_message(self.corporation_id, str(message.id))
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"[ERROR] Mega project selection failed: {error_details}")
            
            error_message = str(e)
            if "duplicate key" in error_message.lower() or "unique constraint" in error_message.lower():
                error_message = "Your corporation already has an active mega project! Complete or cancel it first."
            
            await interaction.followup.send(
                f"❌ Error starting project: {error_message}",
                ephemeral=True
            )



class MegaProjects(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="view-mega-projects", description="📋 View available mega projects")
    async def view_mega_projects(self, interaction: discord.Interaction):
        """View all available mega projects"""
        # Check if player is in a corporation
        corp = await db.get_player_corporation(str(interaction.user.id))
        if not corp:
            return await interaction.response.send_message(
                "❌ You must be in a corporation to view mega projects!",
                ephemeral=True
            )
        
        # Check if command is being used in the corporation's forum post
        if not isinstance(interaction.channel, discord.Thread):
            return await interaction.response.send_message(
                "❌ This command can only be used in your corporation's forum post!",
                ephemeral=True
            )
        
        # Verify this is the correct corporation's forum post
        channel_id = str(interaction.channel.id)
        forum_corp = await db.get_corporation_by_forum_post(channel_id)
        
        # Debug logging
        print(f"[DEBUG view-mega-projects] User: {interaction.user.id} | Channel: {channel_id}")
        print(f"[DEBUG view-mega-projects] User's corp: ID={corp['id']}, Name={corp['name']}")
        print(f"[DEBUG view-mega-projects] Forum corp lookup: {forum_corp}")
        
        if not forum_corp:
            return await interaction.response.send_message(
                f"❌ This thread is not registered as a corporation forum post!\n"
                f"If this is your corporation's forum, please contact an admin.\n"
                f"Debug Info: Channel ID `{channel_id}`",
                ephemeral=True
            )
        
        if forum_corp['id'] != corp['id']:
            return await interaction.response.send_message(
                f"❌ This command can only be used in your own corporation's forum post!\n"
                f"• This forum belongs to: **{forum_corp['name']}** (ID: {forum_corp['id']})\n"
                f"• Your corporation is: **{corp['name']}** (ID: {corp['id']})",
                ephemeral=True
            )
        
        await interaction.response.defer()
        
        # Check if corporation already has an active project
        active_project = await db.get_corporation_active_project(corp['id'])
        
        if active_project:
            # Display current active project
            if active_project['total_cost'] >= 1_000_000_000:
                cost_billions = active_project['total_cost'] / 1_000_000_000
                cost_display = f"${cost_billions:.1f}B"
            else:
                cost_display = f"${active_project['total_cost']:,}"
            
            progress_pct = (active_project['current_funding'] / active_project['total_cost']) * 100
            progress_bar = self._create_progress_bar(progress_pct)
            
            status = "✅ COMPLETED!" if active_project['completed'] else "🔨 IN PROGRESS"
            
            embed = discord.Embed(
                title=f"{status} - {active_project['name']}",
                description=active_project['description'],
                color=discord.Color.gold() if active_project['completed'] else discord.Color.blue()
            )
            embed.add_field(
                name="💰 Total Cost",
                value=cost_display,
                inline=True
            )
            embed.add_field(
                name="🎁 Buff",
                value=f"{active_project['buff_type']}: +{active_project['buff_value']}%",
                inline=True
            )
            embed.add_field(
                name="📊 Progress",
                value=f"{progress_bar}\n${active_project['current_funding']:,} / {cost_display} ({progress_pct:.1f}%)",
                inline=False
            )
            
            if active_project['completed']:
                embed.add_field(
                    name="🎉 Buff Active!",
                    value="All corporation members are now benefiting from this bonus!",
                    inline=False
                )
            else:
                embed.add_field(
                    name="💡 How to Contribute",
                    value="Use `/contribute-to-project <amount>` to help complete this project!",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
        else:
            # Show available projects
            projects = await db.get_all_mega_projects()
            
            embed = discord.Embed(
                title="🏗️ Available Mega Projects",
                description="**[TEST] test**\n\nChoose a mega project for your corporation!\nOnly the corporation leader can select a project.",
                color=discord.Color.blue()
            )
            
            for project in projects:
                if project['total_cost'] >= 1_000_000_000:
                    cost_billions = project['total_cost'] / 1_000_000_000
                    cost_display = f"${cost_billions:.1f}B"
                else:
                    cost_millions = project['total_cost'] / 1_000_000
                    cost_display = f"${cost_millions:.1f}M"
                
                embed.add_field(
                    name=f"🏢 {project['name']}",
                    value=(
                        f"{project['description']}\n"
                        f"**Cost:** {cost_display}\n"
                        f"**Buff:** {project['buff_type']} +{project['buff_value']}%"
                    ),
                    inline=False
                )
            
            embed.set_footer(text="Select a project from the dropdown below")
            
            # Check if user is the leader
            if str(interaction.user.id) == corp['leader_id']:
                view = MegaProjectSelectView(corp['id'], corp['leader_id'], projects)
                await interaction.followup.send(embed=embed, view=view)
            else:
                embed.set_footer(text="Ask your corporation leader to select a project")
                await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="contribute-to-project", description="💰 Contribute funds to your corporation's mega project")
    @app_commands.describe(
        amount="Amount to contribute"
    )
    async def contribute_to_project(self, interaction: discord.Interaction, amount: app_commands.Range[int, 1000, 100000000]):
        """Contribute to corporation's active mega project"""
        # Check if player is in a corporation
        corp = await db.get_player_corporation(str(interaction.user.id))
        if not corp:
            return await interaction.response.send_message(
                "❌ You must be in a corporation to contribute to mega projects!",
                ephemeral=True
            )
        
        # Check if command is being used in the corporation's forum post
        if not isinstance(interaction.channel, discord.Thread):
            return await interaction.response.send_message(
                "❌ This command can only be used in your corporation's forum post!",
                ephemeral=True
            )
        
        # Verify this is the correct corporation's forum post
        channel_id = str(interaction.channel.id)
        forum_corp = await db.get_corporation_by_forum_post(channel_id)
        
        if not forum_corp or forum_corp['id'] != corp['id']:
            return await interaction.response.send_message(
                "❌ This command can only be used in your corporation's forum post!",
                ephemeral=True
            )
        
        # Check if corporation has an active project
        active_project = await db.get_corporation_active_project(corp['id'])
        
        if not active_project:
            return await interaction.response.send_message(
                "❌ Your corporation doesn't have an active mega project!\n"
                "Use `/view-mega-projects` to select one.",
                ephemeral=True
            )
        
        if active_project['completed']:
            return await interaction.response.send_message(
                "❌ This project is already completed!\n"
                "You can view it with `/view-mega-projects`",
                ephemeral=True
            )
        
        # Check if player has enough balance
        player = await db.get_player(str(interaction.user.id))
        if player['balance'] < amount:
            return await interaction.response.send_message(
                f"❌ You don't have enough money!\n"
                f"Your balance: ${player['balance']:,}\n"
                f"Amount needed: ${amount:,}",
                ephemeral=True
            )
        
        await interaction.response.defer()
        
        # Deduct money from player and contribute to project
        await db.update_player_balance(str(interaction.user.id), -amount)
        updated_project = await db.contribute_to_mega_project(
            active_project['id'],
            str(interaction.user.id),
            amount
        )
        
        # Calculate new progress
        new_funding = updated_project['current_funding'] + amount
        progress_pct = (new_funding / updated_project['total_cost']) * 100
        was_completed = new_funding >= updated_project['total_cost']
        
        # Display cost
        if updated_project['total_cost'] >= 1_000_000_000:
            cost_billions = updated_project['total_cost'] / 1_000_000_000
            cost_display = f"${cost_billions:.1f}B"
        else:
            cost_display = f"${updated_project['total_cost']:,}"
        
        embed = discord.Embed(
            title="✅ Contribution Successful!",
            description=f"You've contributed **${amount:,}** to **{active_project['name']}**",
            color=discord.Color.gold() if was_completed else discord.Color.green()
        )
        embed.add_field(
            name="💰 New Funding Total",
            value=f"${new_funding:,} / {cost_display}",
            inline=True
        )
        embed.add_field(
            name="📊 Progress",
            value=f"{progress_pct:.1f}%",
            inline=True
        )
        
        if was_completed:
            embed.add_field(
                name="🎉 PROJECT COMPLETED!",
                value=f"The mega project is now complete!\n"
                      f"🎁 **Buff Active:** {active_project['buff_type']} +{active_project['buff_value']}%\n\n"
                      f"All corporation members now benefit from this bonus!",
                inline=False
            )
        
        player = await db.get_player(str(interaction.user.id))
        embed.set_footer(text=f"New balance: ${player['balance']:,}")
        
        await interaction.followup.send(embed=embed)
        
        # Update the pinned project message
        await self._update_project_message(corp['id'], interaction.channel)
    
    async def _update_project_message(self, corporation_id: int, channel: discord.Thread):
        """Update the pinned mega project message with current progress"""
        try:
            # Get the project message ID
            project_message_id = await db.get_corporation_project_message(corporation_id)
            if not project_message_id:
                return
            
            # Get current project status
            active_project = await db.get_corporation_active_project(corporation_id)
            if not active_project:
                return
            
            # Fetch the message
            try:
                message = await channel.fetch_message(int(project_message_id))
            except:
                return  # Message not found or deleted
            
            # Calculate progress
            progress_pct = (active_project['current_funding'] / active_project['total_cost']) * 100
            progress_bar = self._create_progress_bar(progress_pct)
            
            # Display cost
            if active_project['total_cost'] >= 1_000_000_000:
                cost_billions = active_project['total_cost'] / 1_000_000_000
                cost_display = f"${cost_billions:.1f}B"
            else:
                cost_display = f"${active_project['total_cost']:,}"
            
            status = "✅ COMPLETED!" if active_project['completed'] else "🔨 IN PROGRESS"
            
            embed = discord.Embed(
                title=f"🏗️ Active Mega Project - {status}",
                description=f"**{active_project['name']}**\n{active_project['description']}",
                color=discord.Color.gold() if active_project['completed'] else discord.Color.blue()
            )
            embed.add_field(
                name="💰 Total Cost",
                value=cost_display,
                inline=True
            )
            embed.add_field(
                name="🎁 Buff",
                value=f"{active_project['buff_type']}: +{active_project['buff_value']}%",
                inline=True
            )
            embed.add_field(
                name="📊 Progress",
                value=f"{progress_bar}\n${active_project['current_funding']:,} / {cost_display} ({progress_pct:.1f}%)",
                inline=False
            )
            
            if active_project['completed']:
                embed.add_field(
                    name="🎉 Buff Active!",
                    value="All corporation members are now benefiting from this bonus!",
                    inline=False
                )
            else:
                embed.add_field(
                    name="💡 How to Contribute",
                    value="Use `/contribute-to-project <amount>` to help complete this project!",
                    inline=False
                )
            
            embed.set_footer(text=f"Last updated")
            embed.timestamp = discord.utils.utcnow()
            
            await message.edit(embed=embed)
            
        except Exception as e:
            print(f"[ERROR] Failed to update project message: {e}")
    
    def _create_progress_bar(self, progress_pct: float, length: int = 20) -> str:
        """Create a visual progress bar"""
        filled = int((progress_pct / 100) * length)
        empty = length - filled
        bar = "█" * filled + "░" * empty
        return f"[{bar}]"
    
    @app_commands.command(name="setup-corporation-forum", description="⚙️ Set up corporation forum channel (Admin only)")
    @app_commands.describe(
        channel="Forum channel for corporation discussions"
    )
    async def setup_corporation_forum(self, interaction: discord.Interaction, channel: discord.ForumChannel):
        """Set up a forum channel where corporations can have their own threads"""
        if not await is_admin_or_authorized(interaction):
            return await interaction.response.send_message(
                "❌ You don't have permission to use this command.",
                ephemeral=True
            )
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Save forum channel
            await db.set_corporation_forum_channel(str(interaction.guild.id), str(channel.id))
            
            # Create initial post explaining the forum
            embed = discord.Embed(
                title="🏢 Corporation Forum",
                description="This forum is dedicated to corporation discussions.\n\n"
                           "**How it works:**\n"
                           "• Each corporation gets its own thread\n"
                           "• Only corporation members can post in their thread\n"
                           "• View mega projects and contribute to them\n"
                           "• Coordinate with your corporation members",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="📋 Commands",
                value="• `/view-mega-projects` - View and select mega projects\n"
                      "• `/contribute-to-project` - Contribute to active project\n"
                      "• `/corporation-info` - View corporation details",
                inline=False
            )
            
            # Note: Forum channels don't support sending direct messages
            # Corporations will need to create their own threads
            
            success_embed = discord.Embed(
                title="✅ Corporation Forum Setup Complete",
                description=f"Corporation forum has been set up in {channel.mention}",
                color=discord.Color.green()
            )
            success_embed.add_field(
                name="📋 Next Steps",
                value="• Corporation leaders can create threads for their corporations\n"
                      "• Members can discuss and coordinate in their threads\n"
                      "• Mega projects will be visible in corporation threads",
                inline=False
            )
            
            await interaction.followup.send(embed=success_embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Error setting up corporation forum: {e}",
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(MegaProjects(bot))
