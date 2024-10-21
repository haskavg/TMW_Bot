from lib.bot import TMWBot
import yaml
from typing import Optional

import discord
from discord.ext import commands
from discord.ext import tasks

from datetime import datetime, timedelta

SELFMUTE_CONFIG = 'config/selfmute.yml'
with open(SELFMUTE_CONFIG, 'r') as config_file:
    selfmute_config = yaml.safe_load(config_file)

CREATE_ACTIVE_MUTES_TABLE = """
CREATE TABLE IF NOT EXISTS active_mutes (
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    mute_role_id INTEGER NOT NULL,
    roles_to_restore TEXT NOT NULL,
    end_time INTEGER NOT NULL,
    PRIMARY KEY (guild_id, user_id));
"""
STORE_MUTE_QUERY = """INSERT INTO active_mutes (guild_id, user_id, mute_role_id, roles_to_restore, end_time)
                    VALUES (?,?,?,?,?)
                    ON CONFLICT (guild_id, user_id) DO UPDATE SET
                    mute_role_id = excluded.mute_role_id,
                    roles_to_restore = excluded.roles_to_restore,
                    end_time = excluded.end_time;"""

GET_ALL_MUTES_QUERY = """SELECT * FROM active_mutes WHERE guild_id = ? ORDER BY end_time ASC"""

GET_USER_MUTE_QUERY = """SELECT guild_id, user_id, mute_role_id, roles_to_restore, end_time FROM active_mutes WHERE guild_id = ? AND user_id = ?"""

REMOVE_MUTE_QUERY = """DELETE FROM active_mutes WHERE guild_id = ? AND user_id = ?"""


class Selfmute(commands.Cog):
    def __init__(self, bot: TMWBot):
        self.bot = bot

    async def cog_load(self):
        await self.bot.RUN(CREATE_ACTIVE_MUTES_TABLE)
        self.clear_mutes.start()

    async def perform_mute(self, member: discord.Member, mute_role_id: str, unmute_time: datetime):
        roles_to_save = [role for role in member.roles if not role.is_default(
        ) and not role.is_premium_subscriber() and role.is_assignable()]
        current_roles_string = ",".join([str(role.id) for role in roles_to_save])
        unmute_time_string = unmute_time.strftime("%Y-%m-%d %H:%M:%S")
        mute_role = member.guild.get_role(int(mute_role_id))
        await self.bot.RUN(STORE_MUTE_QUERY, (member.guild.id, member.id, mute_role_id, current_roles_string, unmute_time_string))
        await member.edit(roles=[mute_role])

    @discord.app_commands.command(name="unmute_user",  description="Removes a mute from a user.")
    @discord.app_commands.guild_only()
    @discord.app_commands.describe(member="The user to unmute.")
    @discord.app_commands.default_permissions(administrator=True)
    async def unmute_user(self, interaction: discord.Interaction, member: discord.Member):
        mute_data = await self.bot.GET_ONE(GET_USER_MUTE_QUERY, (interaction.guild.id, member.id))

        if not mute_data:
            await interaction.response.send_message("This user was not found in the muted data. Removing muted role.", ephemeral=True)

        await self.perform_user_unmute(member, interaction.channel, mute_data)
        if mute_data:
            await interaction.response.send_message(f"{member.mention} has been unmuted and roles restored when possible.", ephemeral=True)

    async def perform_user_unmute(self, member: discord.Member, channel: discord.TextChannel, mute_data):
        all_selftmute_roles = [member.guild.get_role(role_id) for role_id in selfmute_config.get(member.guild.id, [])]
        await member.edit(roles=[role for role in member.roles if role not in all_selftmute_roles])
        if not mute_data:
            return
        guild_id, user_id, mute_role_id, role_ids_to_restore, _ = mute_data
        if role_ids_to_restore:
            roles_to_restore = [member.guild.get_role(int(role_id)) for role_id in role_ids_to_restore.split(",")]
            roles_to_restore = [role for role in roles_to_restore if not role.is_default(
            ) and not role.is_premium_subscriber() and role.is_assignable()]
            await member.add_roles(*roles_to_restore)
            await channel.send(f"Unmuted {member.mention} and restored the following roles:\n{', '.join([role.mention for role in roles_to_restore])}",
                               allowed_mentions=discord.AllowedMentions.none())
        await self.bot.RUN(REMOVE_MUTE_QUERY, (guild_id, user_id))

    @discord.app_commands.command(name="selfmute",  description="Mute yourself for a specified amount of time.")
    @discord.app_commands.guild_only()
    async def selfmute(self, interaction: discord.Interaction, hours: Optional[int] = 0, minutes: Optional[int] = 0):
        all_selftmute_roles = [interaction.guild.get_role(
            role_id) for role_id in selfmute_config.get(interaction.guild_id, [])]

        if not all_selftmute_roles:
            await interaction.response.send_message("This server has no selfmute roles configured.", ephemeral=True)
            return

        if any(role in interaction.user.roles for role in all_selftmute_roles):
            await interaction.response.send_message("You are already muted.", ephemeral=True)
            return

        unmute_time = discord.utils.utcnow() + timedelta(hours=hours, minutes=minutes)

        async def mute_callback(interaction: discord.Interaction):
            await self.perform_mute(interaction.user, interaction.data["values"][0], unmute_time)
            await interaction.response.send_message("You are now muted.", ephemeral=True)
            await interaction.channel.send(f"User {interaction.user.mention} has been muted for {hours} hours and {minutes} minutes.\nUser had the following roles: {', '.join([role.mention for role in interaction.user.roles if not role.is_default()])}",
                                           allowed_mentions=discord.AllowedMentions.none())

        my_view = discord.ui.View()
        my_select = discord.ui.Select()
        for role in all_selftmute_roles:
            my_select.add_option(label=role.name, value=str(role.id))

        my_view.add_item(my_select)
        my_select.callback = mute_callback
        await interaction.response.send_message("Select a role to mute yourself with.", view=my_view, ephemeral=True)

    @tasks.loop(minutes=1)
    async def clear_mutes(self):
        for guild in self.bot.guilds:
            active_mutes = await self.bot.GET(GET_ALL_MUTES_QUERY, (guild.id))
            for mute_data in active_mutes:
                guild_id, user_id, mute_role_id, role_ids_to_restore, unmute_time = mute_data


async def setup(bot):
    await bot.add_cog(Selfmute(bot))
