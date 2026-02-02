# Corporations (Player Clans) System

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

import database as db
from registration_check import check_registration

class Corporations(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="create-corporation", description="🏢 Create a corporation (player clan)")
    @app_commands.describe(
        name="Corporation name",
        tag="Corporation tag (3-5 characters)"
    )
    async def create_corporation(
        self,
        interaction: discord.Interaction,
        name: app_commands.Range[str, 3, 50],
        tag: app_commands.Range[str, 3, 5]
    ):
        """Create a new corporation"""
        # Registration check
        if not await check_registration(interaction):
            return
        
        await interaction.response.defer()
        
        # Check if player is already in a corporation
        existing = await db.get_player_corporation(str(interaction.user.id))
        if existing:
            await interaction.followup.send(
                f"❌ You're already in corporation **{existing['name']}**! Leave it first with `/leave-corporation`.",
                ephemeral=True
            )
            return
        
        # Check if name/tag is taken
        if await db.corporation_name_exists(name):
            await interaction.followup.send(f"❌ Corporation name **{name}** is already taken!", ephemeral=True)
            return
        
        if await db.corporation_tag_exists(tag.upper()):
            await interaction.followup.send(f"❌ Corporation tag **{tag.upper()}** is already taken!", ephemeral=True)
            return
        
        # Creation cost
        creation_cost = 5000000  # $5M
        player = await db.get_player(str(interaction.user.id))
        
        if not player or player['balance'] < creation_cost:
            await interaction.followup.send(
                f"❌ You need ${creation_cost:,} to create a corporation! You have ${player['balance'] if player else 0:,}.",
                ephemeral=True
            )
            return
        
        # Get forum channel
        forum_channel_id = await db.get_corporation_forum_channel(str(interaction.guild.id))
        if not forum_channel_id:
            await interaction.followup.send(
                "❌ Corporation forum has not been set up yet! Ask an admin to use `/setup-corporation-forum` first.",
                ephemeral=True
            )
            return
        
        forum_channel = interaction.guild.get_channel(int(forum_channel_id))
        if not forum_channel or not isinstance(forum_channel, discord.ForumChannel):
            await interaction.followup.send(
                "❌ Corporation forum channel is invalid! Ask an admin to set it up again.",
                ephemeral=True
            )
            return
        
        # Create corporation
        await db.update_player_balance(str(interaction.user.id), -creation_cost)
        corp_id = await db.create_corporation(
            name,
            tag.upper(),
            str(interaction.user.id),
            str(interaction.guild.id)
        )
        
        # Create forum post for the corporation
        try:
            forum_embed = discord.Embed(
                title=f"🏢 [{tag.upper()}] {name}",
                description=f"**Corporation Hub**\n\nWelcome to the official forum for **{name}**!",
                color=discord.Color.gold()
            )
            forum_embed.add_field(name="👑 Leader", value=interaction.user.mention, inline=True)
            forum_embed.add_field(name="🆔 Corporation ID", value=f"#{corp_id}", inline=True)
            forum_embed.add_field(name="👥 Members", value="1", inline=True)
            forum_embed.add_field(
                name="📋 Available Commands",
                value=(
                    "• `/view-mega-projects` - View and select mega projects\n"
                    "• `/contribute-to-project` - Contribute to active project\n"
                    "• `/corporation-info` - View corporation details"
                ),
                inline=False
            )
            forum_embed.set_footer(text=f"Created on {discord.utils.format_dt(discord.utils.utcnow(), 'F')}")
            
            # Create the forum post
            forum_post = await forum_channel.create_thread(
                name=f"[{tag.upper()}] {name}",
                embed=forum_embed,
                reason=f"Corporation forum created by {interaction.user.name}"
            )
            
            # Store the forum post ID
            await db.set_corporation_forum_post(corp_id, str(forum_post.id))
            
            # Send a welcome message in the forum post
            welcome_msg = await forum_post.send(
                f"🎉 Welcome {interaction.user.mention}! This is your corporation's private forum.\n\n"
                f"**Only members of [{tag.upper()}] {name} can post here.**\n"
                f"Use this space to coordinate with your corporation members!"
            )
            
        except discord.Forbidden:
            # Rollback corporation creation if forum post fails
            await db.disband_corporation(corp_id)
            await db.update_player_balance(str(interaction.user.id), creation_cost)
            await interaction.followup.send(
                "❌ I don't have permission to create forum posts! Ask an admin to grant me the necessary permissions.",
                ephemeral=True
            )
            return
        except Exception as e:
            # Rollback corporation creation if forum post fails
            await db.disband_corporation(corp_id)
            await db.update_player_balance(str(interaction.user.id), creation_cost)
            await interaction.followup.send(
                f"❌ Error creating corporation forum post: {e}",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="🏢 Corporation Created!",
            description=f"**[{tag.upper()}] {name}** has been established!",
            color=discord.Color.gold()
        )
        embed.add_field(name="👑 Leader", value=interaction.user.mention, inline=True)
        embed.add_field(name="🆔 Corporation ID", value=f"#{corp_id}", inline=True)
        embed.add_field(name="💰 Cost", value=f"${creation_cost:,}", inline=True)
        embed.add_field(name="📍 Forum", value=f"Your corporation forum: {forum_post.mention}", inline=False)
        embed.add_field(
            name="📋 Next Steps",
            value=(
                "• Use `/invite-to-corporation` to invite members\n"
                "• Visit your forum to view and manage mega projects\n"
                "• Build up your corporation's wealth\n"
                "• Compete on the corporation leaderboard!"
            ),
            inline=False
        )
        embed.set_footer(text=f"New balance: ${player['balance'] - creation_cost:,}")
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="invite-to-corporation", description="📨 Invite a player to your corporation")
    @app_commands.describe(
        member="Member to invite"
    )
    async def invite_to_corporation(self, interaction: discord.Interaction, member: discord.Member):
        """Invite a player to join your corporation"""
        # Check if inviter is a corporation leader
        corp = await db.get_corporation_by_leader(str(interaction.user.id))
        if not corp:
            await interaction.response.send_message("❌ You must be a corporation leader to invite members!", ephemeral=True)
            return
        
        # Check if target is already in a corporation
        target_corp = await db.get_player_corporation(str(member.id))
        if target_corp:
            await interaction.response.send_message(
                f"❌ {member.mention} is already in corporation **{target_corp['name']}**!",
                ephemeral=True
            )
            return
        
        # Check corporation member limit
        max_members = await db.get_corporation_member_limit(str(interaction.guild.id))
        current_members = await db.get_corporation_member_count(corp['id'])
        
        if current_members >= max_members:
            await interaction.response.send_message(
                f"❌ Your corporation is full! Maximum: {max_members} members. Ask an admin to increase the limit with `/set-corp-member-limit`.",
                ephemeral=True
            )
            return
        
        # Create invitation
        await db.create_corporation_invite(corp['id'], str(member.id))
        
        # Send invite to target
        embed = discord.Embed(
            title="📨 Corporation Invitation",
            description=f"You've been invited to join **[{corp['tag']}] {corp['name']}**!",
            color=discord.Color.blue()
        )
        embed.add_field(name="👑 Leader", value=f"<@{corp['leader_id']}>", inline=True)
        embed.add_field(name="👥 Members", value=f"{current_members}/{max_members}", inline=True)
        embed.add_field(
            name="✅ Accept",
            value="Use `/accept-corporation-invite` to join!",
            inline=False
        )
        
        try:
            await member.send(embed=embed)
            await interaction.response.send_message(f"✅ Invitation sent to {member.mention}!")
        except:
            await interaction.response.send_message(
                f"❌ Couldn't send invitation to {member.mention}. They may have DMs disabled.",
                ephemeral=True
            )
    
    @app_commands.command(name="accept-corporation-invite", description="✅ Accept a corporation invitation")
    async def accept_invite(self, interaction: discord.Interaction):
        """Accept a pending corporation invitation"""
        # Check for pending invites
        invite = await db.get_pending_corporation_invite(str(interaction.user.id))
        if not invite:
            await interaction.response.send_message("❌ You don't have any pending corporation invitations!", ephemeral=True)
            return
        
        # Check if player is already in a corporation
        existing = await db.get_player_corporation(str(interaction.user.id))
        if existing:
            await interaction.response.send_message(
                f"❌ You're already in corporation **{existing['name']}**!",
                ephemeral=True
            )
            return
        
        # Accept invite
        corp = await db.get_corporation_by_id(invite['corporation_id'])
        await db.accept_corporation_invite(invite['id'], str(interaction.user.id))
        
        embed = discord.Embed(
            title="✅ Joined Corporation!",
            description=f"Welcome to **[{corp['tag']}] {corp['name']}**!",
            color=discord.Color.green()
        )
        embed.add_field(name="👑 Leader", value=f"<@{corp['leader_id']}>", inline=True)
        embed.add_field(name="🆔 Corporation ID", value=f"#{corp['id']}", inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="corporation-info", description="ℹ️ View corporation information")
    @app_commands.describe(
        corporation_id="Corporation ID (leave empty for your own)"
    )
    async def corporation_info(self, interaction: discord.Interaction, corporation_id: Optional[int] = None):
        """View corporation details"""
        if corporation_id:
            corp = await db.get_corporation_by_id(corporation_id)
        else:
            corp = await db.get_player_corporation(str(interaction.user.id))
        
        if not corp:
            await interaction.response.send_message("❌ Corporation not found!", ephemeral=True)
            return
        
        # Get members
        members = await db.get_corporation_members(corp['id'])
        total_wealth = sum(member['balance'] for member in members)
        
        embed = discord.Embed(
            title=f"🏢 [{corp['tag']}] {corp['name']}",
            description=f"Corporation ID #{corp['id']}",
            color=discord.Color.gold()
        )
        embed.add_field(name="👑 Leader", value=f"<@{corp['leader_id']}>", inline=True)
        embed.add_field(name="👥 Members", value=f"{len(members)}", inline=True)
        embed.add_field(name="💰 Total Wealth", value=f"${total_wealth:,}", inline=True)
        embed.add_field(name="📅 Established", value=discord.utils.format_dt(corp['created_at'], 'D'), inline=True)
        
        # List members
        member_list = []
        for i, member in enumerate(members[:10], 1):  # Show top 10
            crown = "👑 " if member['user_id'] == corp['leader_id'] else ""
            member_list.append(f"{i}. {crown}<@{member['user_id']}> - ${member['balance']:,}")
        
        if len(members) > 10:
            member_list.append(f"*...and {len(members) - 10} more*")
        
        embed.add_field(
            name="👥 Members List",
            value="\n".join(member_list) if member_list else "No members",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="leave-corporation", description="🚪 Leave your current corporation")
    async def leave_corporation(self, interaction: discord.Interaction):
        """Leave your corporation"""
        corp = await db.get_player_corporation(str(interaction.user.id))
        if not corp:
            await interaction.response.send_message("❌ You're not in a corporation!", ephemeral=True)
            return
        
        # Leaders can't leave (must transfer leadership first)
        if corp['leader_id'] == str(interaction.user.id):
            await interaction.response.send_message(
                "❌ As the leader, you must transfer leadership with `/transfer-corporation-leadership` before leaving, or use `/disband-corporation` to delete it!",
                ephemeral=True
            )
            return
        
        await db.remove_player_from_corporation(str(interaction.user.id))
        
        embed = discord.Embed(
            title="🚪 Left Corporation",
            description=f"You've left **[{corp['tag']}] {corp['name']}**",
            color=discord.Color.orange()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="disband-corporation", description="💥 Disband your corporation (Leader only)")
    async def disband_corporation(self, interaction: discord.Interaction):
        """Disband your corporation - Leader only"""
        corp = await db.get_player_corporation(str(interaction.user.id))
        if not corp:
            await interaction.response.send_message("❌ You're not in a corporation!", ephemeral=True)
            return
        
        # Only leader can disband
        if corp['leader_id'] != str(interaction.user.id):
            await interaction.response.send_message(
                "❌ Only the corporation leader can disband the corporation!",
                ephemeral=True
            )
            return
        
        # Get member count for confirmation
        members = await db.get_corporation_members(corp['id'])
        member_count = len(members)
        
        # Create confirmation view
        class DisbandConfirmView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)
                self.value = None
            
            @discord.ui.button(label="Confirm Disband", style=discord.ButtonStyle.danger)
            async def confirm(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                if button_interaction.user.id != interaction.user.id:
                    await button_interaction.response.send_message("❌ Only the leader can confirm this!", ephemeral=True)
                    return
                
                self.value = True
                self.stop()
                
                # Delete the corporation
                await db.delete_corporation(corp['id'])
                
                embed = discord.Embed(
                    title="💥 Corporation Disbanded",
                    description=f"**[{corp['tag']}] {corp['name']}** has been disbanded!",
                    color=discord.Color.red()
                )
                embed.add_field(name="👥 Members Released", value=str(member_count), inline=True)
                embed.add_field(name="👑 Former Leader", value=interaction.user.mention, inline=True)
                
                await button_interaction.response.edit_message(embed=embed, view=None)
            
            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.gray)
            async def cancel(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                if button_interaction.user.id != interaction.user.id:
                    await button_interaction.response.send_message("❌ Only the leader can cancel this!", ephemeral=True)
                    return
                
                self.value = False
                self.stop()
                
                await button_interaction.response.edit_message(
                    content="❌ Disbandment cancelled.",
                    embed=None,
                    view=None
                )
        
        view = DisbandConfirmView()
        
        embed = discord.Embed(
            title="⚠️ Confirm Corporation Disbandment",
            description=f"Are you sure you want to disband **[{corp['tag']}] {corp['name']}**?\n\n"
                       f"This will:\n"
                       f"• Remove all {member_count} member(s)\n"
                       f"• Delete all corporation data\n"
                       f"• **Cannot be undone!**",
            color=discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="corporation-leaderboard", description="🏆 View corporation rankings")
    async def corporation_leaderboard(self, interaction: discord.Interaction):
        """Display corporation leaderboard"""
        corps = await db.get_corporation_leaderboard(str(interaction.guild.id), limit=25)
        
        if not corps:
            await interaction.response.send_message("No corporations have been created yet!", ephemeral=True)
            return
        
        # Build formatted leaderboard text
        leaderboard_text = "```\n"
        for i, corp in enumerate(corps, 1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, "  ")
            rank_str = str(i).rjust(3)
            # Truncate and pad name to 25 characters
            corp_name = f"[{corp['tag']}] {corp['name']}"[:25].ljust(25)
            wealth = f"${corp['total_wealth']:,}"
            leaderboard_text += f"{medal} #{rank_str} | {corp_name} | {wealth}\n"
        leaderboard_text += "```"
        
        embed = discord.Embed(
            title="🏆 Corporation Leaderboard",
            description=f"Top {len(corps)} corporations by total member wealth\n{leaderboard_text}",
            color=discord.Color.gold()
        )
        
        embed.set_footer(text=f"Total corporations: {len(corps)}")
        embed.timestamp = discord.utils.utcnow()
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="set-corp-member-limit", description="⚙️ Set corporation member limit (Admin only)")
    @app_commands.describe(
        limit="Maximum members per corporation (1-50)"
    )
    async def set_member_limit(self, interaction: discord.Interaction, limit: app_commands.Range[int, 1, 50]):
        """Set the maximum members per corporation"""
        # Check if user is bot owner
        app_info = interaction.client.application
        is_bot_owner = interaction.user.id == app_info.owner.id if app_info and app_info.owner else False
        
        if not is_bot_owner:
            # Check if user is server owner
            if interaction.user.id != interaction.guild.owner_id:
                # Check if user has administrator permissions
                if not interaction.user.guild_permissions.administrator:
                    # Check if user has an authorized admin role
                    settings = await db.get_guild_settings(str(interaction.guild.id))
                    if settings and settings.get('admin_role_ids'):
                        admin_role_ids = settings['admin_role_ids']
                        user_role_ids = [str(role.id) for role in interaction.user.roles]
                        
                        if not any(role_id in admin_role_ids for role_id in user_role_ids):
                            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
                            return
                    else:
                        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
                        return
        
        await db.set_corporation_member_limit(str(interaction.guild.id), limit)
        
        embed = discord.Embed(
            title="✅ Corporation Member Limit Updated",
            description=f"Corporations can now have up to **{limit}** members",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="setup-corporation-leaderboard", description="⚙️ Set up auto-updating corporation leaderboard (Admin only)")
    @app_commands.describe(
        channel="Channel where the corporation leaderboard will be posted"
    )
    async def setup_corporation_leaderboard(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set up an auto-updating corporation leaderboard"""
        # Check if user is bot owner
        app_info = interaction.client.application
        is_bot_owner = interaction.user.id == app_info.owner.id if app_info and app_info.owner else False
        
        if not is_bot_owner:
            # Check if user is server owner
            if interaction.user.id != interaction.guild.owner_id:
                # Check if user has administrator permissions
                if not interaction.user.guild_permissions.administrator:
                    # Check if user has an authorized admin role
                    settings = await db.get_guild_settings(str(interaction.guild.id))
                    if settings and settings.get('admin_role_ids'):
                        admin_role_ids = settings['admin_role_ids']
                        user_role_ids = [str(role.id) for role in interaction.user.roles]
                        
                        if not any(role_id in admin_role_ids for role_id in user_role_ids):
                            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
                            return
                    else:
                        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
                        return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Create initial leaderboard embed
            corps = await db.get_corporation_leaderboard(str(interaction.guild.id), limit=25)
            
            # Build formatted leaderboard text
            if corps:
                leaderboard_text = "```\n"
                for i, corp in enumerate(corps[:25], 1):
                    medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, "  ")
                    rank_str = str(i).rjust(3)
                    # Truncate and pad name to 25 characters
                    corp_name = f"[{corp['tag']}] {corp['name']}"[:25].ljust(25)
                    wealth = f"${corp['total_wealth']:,}"
                    leaderboard_text += f"{medal} #{rank_str} | {corp_name} | {wealth}\n"
                leaderboard_text += "```"
            else:
                leaderboard_text = "No corporations yet!"
            
            embed = discord.Embed(
                title="🏆 Corporation Leaderboard",
                description=f"Top 25 corporations by total member wealth\n{leaderboard_text}",
                color=discord.Color.gold()
            )
            
            embed.set_footer(text=f"Total corporations: {len(corps)} | Last updated")
            embed.timestamp = discord.utils.utcnow()
            
            # Send the message to the channel
            message = await channel.send(embed=embed)
            
            # Store the channel and message IDs
            await db.set_corporation_leaderboard_channel(str(interaction.guild.id), str(channel.id))
            await db.set_corporation_leaderboard_message(str(interaction.guild.id), str(message.id))
            
            success_embed = discord.Embed(
                title="✅ Corporation Leaderboard Set Up!",
                description=f"The corporation leaderboard will now auto-update every 30 seconds in {channel.mention}",
                color=discord.Color.green()
            )
            success_embed.add_field(
                name="📋 Features",
                value=(
                    "• Updates automatically every 30 seconds\n"
                    "• Shows top 25 corporations by total member wealth\n"
                    "• Formatted like the wealth leaderboard"
                ),
                inline=False
            )
            
            await interaction.followup.send(embed=success_embed, ephemeral=True)
            
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ I don't have permission to send messages in that channel!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ Failed to set up corporation leaderboard: {e}",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Corporations(bot))
