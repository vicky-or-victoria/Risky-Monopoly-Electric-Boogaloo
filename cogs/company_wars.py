# Company Wars/Raids System

import discord
from discord import app_commands
from discord.ext import commands
import random
from datetime import datetime, timedelta

import database as db

class CompanyWars(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_wars = {}  # war_id: war_data
    
    def rank_to_number(self, rank: str) -> int:
        """Convert rank letter to number for comparison (higher number = better rank)"""
        rank_map = {
            'F': 0,
            'E': 1,
            'D': 2,
            'C': 3,
            'B': 4,
            'A': 5,
            'S': 6,
            'SS': 7,
            'SSR': 8
        }
        return rank_map.get(rank.upper(), 0)
    
    @app_commands.command(name="raid-company", description="⚔️ Initiate a raid on another company")
    @app_commands.describe(
        target_company_id="ID of the company to raid"
    )
    async def raid_company(self, interaction: discord.Interaction, target_company_id: int):
        """Initiate a company raid"""
        await interaction.response.defer()
        
        # Get attacker's company
        attacker_company = await db.get_company_by_owner(str(interaction.user.id))
        if not attacker_company:
            await interaction.followup.send("❌ You don't own a company! Create one first.", ephemeral=True)
            return
        
        # Get target company
        target_company = await db.get_company_by_id(target_company_id)
        if not target_company:
            await interaction.followup.send("❌ Target company not found.", ephemeral=True)
            return
        
        # Can't raid yourself
        if attacker_company['id'] == target_company['id']:
            await interaction.followup.send("❌ You can't raid your own company!", ephemeral=True)
            return
        
        # Check raid cooldown
        last_raid = await db.get_last_raid_time(attacker_company['id'])
        if last_raid:
            time_since = datetime.now() - last_raid
            cooldown = timedelta(hours=2)
            if time_since < cooldown:
                remaining = cooldown - time_since
                minutes = int(remaining.total_seconds() / 60)
                await interaction.followup.send(
                    f"❌ Your company is still recovering from the last raid! Wait {minutes} more minutes.",
                    ephemeral=True
                )
                return
        
        # Check if companies can raid based on rank difference
        attacker_rank_num = self.rank_to_number(attacker_company['rank'])
        target_rank_num = self.rank_to_number(target_company['rank'])
        rank_diff = abs(attacker_rank_num - target_rank_num)
        if rank_diff > 2:
            await interaction.followup.send(
                f"❌ You can only raid companies within 2 ranks of yours! (Your rank: {attacker_company['rank']}, Their rank: {target_company['rank']})",
                ephemeral=True
            )
            return
        
        # Calculate raid success chance based on income and reputation
        attacker_power = attacker_company['current_income'] + (attacker_company['reputation'] * 100)
        defender_power = target_company['current_income'] + (target_company['reputation'] * 100)
        
        total_power = attacker_power + defender_power
        success_chance = (attacker_power / total_power) * 100
        
        # Execute raid
        raid_successful = random.random() * 100 < success_chance
        
        if raid_successful:
            # Calculate loot (10-20% of target's income for 1 hour)
            loot_multiplier = random.uniform(0.1, 0.2)
            loot = int(target_company['current_income'] * 120 * loot_multiplier)  # 120 = 2 updates per minute * 60 minutes
            
            # Reduce target's reputation
            reputation_loss = random.randint(5, 15)
            
            # Update companies
            await db.update_company_income(target_company['id'], -int(target_company['current_income'] * 0.05))  # 5% income loss
            await db.update_company_reputation(target_company['id'], -reputation_loss)
            await db.update_player_balance(attacker_company['owner_id'], loot)
            await db.update_company_reputation(attacker_company['id'], random.randint(5, 10))
            
            # Log the raid
            await db.log_company_raid(
                attacker_company['id'],
                target_company['id'],
                True,
                loot,
                reputation_loss
            )
            
            embed = discord.Embed(
                title="⚔️ RAID SUCCESSFUL!",
                description=f"**{attacker_company['name']}** has successfully raided **{target_company['name']}**!",
                color=discord.Color.green()
            )
            embed.add_field(name="💰 Loot Stolen", value=f"${loot:,}", inline=True)
            embed.add_field(name="📉 Target Reputation Loss", value=f"-{reputation_loss}", inline=True)
            embed.add_field(name="📊 Success Rate", value=f"{success_chance:.1f}%", inline=True)
            embed.add_field(
                name="🎯 Consequences",
                value=f"• {target_company['name']} lost 5% income rate\n• You gained ${loot:,}\n• Your reputation increased",
                inline=False
            )
            
            # Notify target
            try:
                target_user = await self.bot.fetch_user(int(target_company['owner_id']))
                notify_embed = discord.Embed(
                    title="⚠️ YOUR COMPANY WAS RAIDED!",
                    description=f"**{attacker_company['name']}** raided your company **{target_company['name']}**!",
                    color=discord.Color.red()
                )
                notify_embed.add_field(name="💔 Losses", value=f"${loot:,} stolen\n-{reputation_loss} reputation\n-5% income rate", inline=False)
                await target_user.send(embed=notify_embed)
            except:
                pass
            
        else:
            # Raid failed
            penalty = int(attacker_company['current_income'] * 50)  # Lose some income as penalty
            
            await db.update_player_balance(attacker_company['owner_id'], -penalty)
            await db.update_company_reputation(attacker_company['id'], -random.randint(3, 8))
            
            # Log the raid
            await db.log_company_raid(
                attacker_company['id'],
                target_company['id'],
                False,
                0,
                0
            )
            
            embed = discord.Embed(
                title="❌ RAID FAILED!",
                description=f"**{attacker_company['name']}** failed to raid **{target_company['name']}**!",
                color=discord.Color.red()
            )
            embed.add_field(name="💸 Penalty", value=f"-${penalty:,}", inline=True)
            embed.add_field(name="📉 Reputation Loss", value=f"-{random.randint(3, 8)}", inline=True)
            embed.add_field(name="📊 Success Rate", value=f"{success_chance:.1f}%", inline=True)
            embed.add_field(
                name="⏰ Cooldown",
                value="Your company must wait 2 hours before raiding again",
                inline=False
            )
        
        embed.set_footer(text=f"Company ID #{attacker_company['id']} vs Company ID #{target_company['id']}")
        embed.timestamp = discord.utils.utcnow()
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="declare-war", description="⚔️ Declare war on another company (24-hour conflict)")
    @app_commands.describe(
        target_company_id="ID of the company to declare war on"
    )
    async def declare_war(self, interaction: discord.Interaction, target_company_id: int):
        """Declare a 24-hour war against another company"""
        await interaction.response.defer()
        
        # Get attacker's company
        attacker_company = await db.get_company_by_owner(str(interaction.user.id))
        if not attacker_company:
            await interaction.followup.send("❌ You don't own a company!", ephemeral=True)
            return
        
        # Get target company
        target_company = await db.get_company_by_id(target_company_id)
        if not target_company:
            await interaction.followup.send("❌ Target company not found.", ephemeral=True)
            return
        
        # Can't declare war on yourself
        if attacker_company['id'] == target_company['id']:
            await interaction.followup.send("❌ You can't declare war on your own company!", ephemeral=True)
            return
        
        # Check if already at war
        existing_war = await db.get_active_war(attacker_company['id'], target_company['id'])
        if existing_war:
            await interaction.followup.send("❌ You're already at war with this company!", ephemeral=True)
            return
        
        # War cost (must be Rank B or higher)
        attacker_rank_num = self.rank_to_number(attacker_company['rank'])
        if attacker_rank_num < 4:  # Rank B = 4, so anything below is C or lower
            await interaction.followup.send("❌ Your company must be Rank B or higher to declare war!", ephemeral=True)
            return
        
        war_cost = 1000000  # $1M to declare war
        player = await db.get_player(str(interaction.user.id))
        
        if player['balance'] < war_cost:
            await interaction.followup.send(
                f"❌ You need ${war_cost:,} to declare war! You only have ${player['balance']:,}.",
                ephemeral=True
            )
            return
        
        # Deduct war cost
        await db.update_player_balance(str(interaction.user.id), -war_cost)
        
        # Create war
        war_id = await db.create_company_war(attacker_company['id'], target_company['id'])
        
        embed = discord.Embed(
            title="⚔️ WAR DECLARED!",
            description=f"**{attacker_company['name']}** has declared war on **{target_company['name']}**!",
            color=discord.Color.dark_red()
        )
        embed.add_field(name="⏰ Duration", value="24 hours", inline=True)
        embed.add_field(name="💰 War Cost", value=f"${war_cost:,}", inline=True)
        embed.add_field(name="🆔 War ID", value=f"#{war_id}", inline=True)
        embed.add_field(
            name="📜 War Rules",
            value=(
                "• Both companies can raid each other without cooldown\n"
                "• No rank restrictions during war\n"
                "• Winner determined by total damage dealt\n"
                "• Loser loses 20% income permanently"
            ),
            inline=False
        )
        embed.set_footer(text=f"Company ID #{attacker_company['id']} ⚔️ Company ID #{target_company['id']}")
        embed.timestamp = discord.utils.utcnow()
        
        # Notify target
        try:
            target_user = await self.bot.fetch_user(int(target_company['owner_id']))
            await target_user.send(embed=embed)
        except:
            pass
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="war-status", description="📊 Check status of ongoing wars")
    async def war_status(self, interaction: discord.Interaction):
        """View active wars involving your company"""
        company = await db.get_company_by_owner(str(interaction.user.id))
        if not company:
            await interaction.response.send_message("❌ You don't own a company!", ephemeral=True)
            return
        
        wars = await db.get_company_wars(company['id'])
        
        if not wars:
            await interaction.response.send_message("You're not involved in any wars.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="⚔️ Active Wars",
            color=discord.Color.red()
        )
        
        for war in wars:
            attacker = await db.get_company_by_id(war['attacker_id'])
            defender = await db.get_company_by_id(war['defender_id'])
            
            time_remaining = war['ends_at'] - datetime.now()
            hours = int(time_remaining.total_seconds() / 3600)
            minutes = int((time_remaining.total_seconds() % 3600) / 60)
            
            embed.add_field(
                name=f"War #{war['id']}: {attacker['name']} vs {defender['name']}",
                value=(
                    f"**Attacker Damage:** ${war['attacker_damage']:,}\n"
                    f"**Defender Damage:** ${war['defender_damage']:,}\n"
                    f"**Time Remaining:** {hours}h {minutes}m"
                ),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="force-end-war", description="⚠️ Force end a war (Admin only)")
    @app_commands.describe(
        war_id="ID of the war to end"
    )
    async def force_end_war(self, interaction: discord.Interaction, war_id: int):
        """Forcefully end an active war (Admin/Owner only)"""
        # Import the admin check function
        from cogs.admin_commands import is_admin_or_authorized
        
        if not await is_admin_or_authorized(interaction):
            return await interaction.response.send_message(
                "❌ You don't have permission to use this command.",
                ephemeral=True
            )
        
        await interaction.response.defer()
        
        # Get the war details
        war = await db.get_war_by_id(war_id)
        if not war:
            return await interaction.followup.send(
                f"❌ War with ID #{war_id} not found.",
                ephemeral=True
            )
        
        # Check if war is already ended
        if not war['active']:
            return await interaction.followup.send(
                f"❌ War #{war_id} has already ended.",
                ephemeral=True
            )
        
        # Get company details
        attacker = await db.get_company_by_id(war['attacker_id'])
        defender = await db.get_company_by_id(war['defender_id'])
        
        # End the war without declaring a winner (admin intervention)
        await db.end_company_war(war_id, force_end=True)
        
        embed = discord.Embed(
            title="⚠️ WAR FORCEFULLY ENDED",
            description=f"War #{war_id} has been forcefully ended by an administrator.",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="⚔️ Combatants",
            value=f"**Attacker:** {attacker['name'] if attacker else 'Unknown'}\n"
                  f"**Defender:** {defender['name'] if defender else 'Unknown'}",
            inline=False
        )
        embed.add_field(
            name="📊 Final Stats",
            value=f"**Attacker Damage:** ${war['attacker_damage']:,}\n"
                  f"**Defender Damage:** ${war['defender_damage']:,}",
            inline=False
        )
        embed.add_field(
            name="ℹ️ Note",
            value="This war was ended by admin intervention. No winner declared, no penalties applied.",
            inline=False
        )
        embed.set_footer(text=f"Ended by {interaction.user.name}")
        embed.timestamp = discord.utils.utcnow()
        
        await interaction.followup.send(embed=embed)
        
        # Notify the company owners
        try:
            if attacker:
                attacker_user = await self.bot.fetch_user(int(attacker['owner_id']))
                notify_embed = discord.Embed(
                    title="⚠️ War Ended by Admin",
                    description=f"Your war (#{war_id}) with **{defender['name'] if defender else 'Unknown'}** has been forcefully ended by an administrator.",
                    color=discord.Color.orange()
                )
                await attacker_user.send(embed=notify_embed)
        except:
            pass
        
        try:
            if defender:
                defender_user = await self.bot.fetch_user(int(defender['owner_id']))
                notify_embed = discord.Embed(
                    title="⚠️ War Ended by Admin",
                    description=f"Your war (#{war_id}) with **{attacker['name'] if attacker else 'Unknown'}** has been forcefully ended by an administrator.",
                    color=discord.Color.orange()
                )
                await defender_user.send(embed=notify_embed)
        except:
            pass

async def setup(bot):
    await bot.add_cog(CompanyWars(bot))
