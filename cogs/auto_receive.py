"""Cog that enables certain roles to automatically receive other roles."""
import discord
import aiosqlite
import asyncio

from discord.ext import commands
from discord.ext import tasks

from lib.bot import TMWBot

CREATE_AUTO_RECEIVE_TABLE_SQL = """
        CREATE TABLE IF NOT EXISTS auto_receive_roles (
        guild_id INTEGER NOT NULL,
        role_id_to_have INTEGER NOT NULL,
        role_name_to_have TEXT,
        role_id_to_get INTEGER NOT NULL,
        role_name_to_get TEXT,
        PRIMARY KEY (guild_id, role_id_to_have, role_id_to_get))"""

CREATE_FORBIDDEN_USERS_TABLE_SQL = """
        CREATE TABLE IF NOT EXISTS auto_receive_roles_banned (
        guild_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        user_name TEXT,
        role_id INTEGER NOT NULL,
        role_name TEXT,
        PRIMARY KEY (guild_id, user_id, role_id))"""

GET_AUTO_RECEIVE_ROLES_SQL = "SELECT * FROM auto_receive_roles WHERE guild_id = ?"

SET_AUTO_RECEIVE_ROLE_SQL = """INSERT INTO auto_receive_roles (guild_id, role_id_to_have, role_name_to_have,
                            role_id_to_get, role_name_to_get) VALUES (?, ?, ?, ?, ?)"""

DELETE_AUTO_RECEIVE_ROLE_SQL = "DELETE FROM auto_receive_roles WHERE guild_id = ? AND role_id_to_have = ? AND role_id_to_get = ?"

GET_FORBIDDEN_USERS_SQL = "SELECT * FROM auto_receive_roles_banned WHERE guild_id = ?"

SET_FORBIDDEN_USER_SQL = """INSERT INTO auto_receive_roles_banned (guild_id, user_id, user_name, role_id, role_name)
                        VALUES (?, ?, ?, ?, ?)"""

DELETE_FORBIDDEN_USER_SQL = "DELETE FROM auto_receive_roles_banned WHERE guild_id = ? AND user_id = ?"


class AutoReceive(commands.Cog):
    def __init__(self, bot: TMWBot):
        self.bot = bot

    async def cog_load(self):
        await self.bot.RUN(CREATE_AUTO_RECEIVE_TABLE_SQL)
        await self.bot.RUN(CREATE_FORBIDDEN_USERS_TABLE_SQL)
        self.give_auto_roles.start()

    async def get_auto_receive_roles(self, guild_id):
        data = await self.bot.GET(GET_AUTO_RECEIVE_ROLES_SQL, (guild_id,))
        if data:
            return [{"role_id_to_have": row[1], "role_id_to_get": row[3]} for row in data]
        return []

    async def get_forbidden_users(self, guild_id):
        data = await self.bot.GET(GET_FORBIDDEN_USERS_SQL, (guild_id,))
        if data:
            return [{"user_id": row[1], "role_id": row[3]} for row in data]
        return []

    @discord.app_commands.command(name="_ban_auto_receive", description="Ban a member from automatically receiving roles.")
    @discord.app_commands.guild_only()
    @discord.app_commands.describe(member="The member that should be banned.", role="The role that should no longer be given.")
    @discord.app_commands.default_permissions(administrator=True)
    async def ban_auto_receive(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        if role in member.roles:
            await member.remove_roles(role)

        try:
            await self.bot.RUN(SET_FORBIDDEN_USER_SQL, (interaction.guild.id,
                                                        member.id, member.name, role.id, role.name))

            await interaction.response.send_message(f"Banned {member.mention} from automatically getting the role {role.mention}.", ephemeral=True)
        except aiosqlite.IntegrityError:
            await interaction.response.send_message(f"{member.mention} is already banned from getting the role {role.mention}.", ephemeral=True)

    @discord.app_commands.command(name="_unban_auto_receive", description="Unban a member from automatically receiving roles (unban all roles).")
    @discord.app_commands.guild_only()
    @discord.app_commands.describe(member="The member that should be unbanned.")
    @discord.app_commands.default_permissions(administrator=True)
    async def unban_auto_receive(self, interaction: discord.Interaction, member: discord.Member):
        await self.bot.RUN(DELETE_FORBIDDEN_USER_SQL, (interaction.guild.id, member.id))
        await interaction.response.send_message(f"Unbanned {member} from automatically receiving roles.", ephemeral=True)

    @discord.app_commands.command(name="_add_auto_receive", description="Add a role that should automatically receive another role.")
    @discord.app_commands.guild_only()
    @discord.app_commands.describe(role_to_have="The role that should have the role to get.",
                                   role_to_get="The role that should be given to the role to have.")
    @discord.app_commands.default_permissions(administrator=True)
    async def add_auto_receive(self, interaction: discord.Interaction, role_to_have: discord.Role, role_to_get: discord.Role):
        try:
            await self.bot.RUN(SET_AUTO_RECEIVE_ROLE_SQL, (interaction.guild.id, role_to_have.id, role_to_have.name,
                                                           role_to_get.id, role_to_get.name))
            await interaction.response.send_message(f"Added {role_to_have.mention} as a role that should automatically receive {role_to_get.mention}.", ephemeral=True)
        except aiosqlite.IntegrityError:
            await interaction.response.send_message(f"{role_to_have.mention} already automatically receives {role_to_get.mention}.", ephemeral=True)

    @discord.app_commands.command(name="_remove_auto_receive", description="Remove a role that should automatically receive another role.")
    @discord.app_commands.guild_only()
    @discord.app_commands.describe(role_to_have="The role that should have the role to get.",
                                   role_to_get="The role that should be given to the role to have.")
    @discord.app_commands.default_permissions(administrator=True)
    async def remove_auto_receive(self, interaction: discord.Interaction, role_to_have: discord.Role, role_to_get: discord.Role):
        await self.bot.RUN(DELETE_AUTO_RECEIVE_ROLE_SQL, (interaction.guild.id, role_to_have.id, role_to_get.id))
        await interaction.response.send_message(f"Removed {role_to_have.mention} as a role that should automatically receive {role_to_get.mention}.", ephemeral=True)

    @tasks.loop(minutes=1)
    async def give_auto_roles(self):
        print("AUTO-RECEIVE: Checking for roles to give...")
        for guild in self.bot.guilds:
            auto_receive_settings = await self.get_auto_receive_roles(guild.id)
            banned_user_data = await self.get_forbidden_users(guild.id)
            for role_data in auto_receive_settings:
                role_to_have = discord.utils.get(guild.roles, id=role_data["role_id_to_have"])
                role_to_get = discord.utils.get(guild.roles, id=role_data["role_id_to_get"])
                if not role_to_have or not role_to_get:
                    self.bot.RUN(DELETE_AUTO_RECEIVE_ROLE_SQL,
                                 (guild.id, role_data["role_id_to_have"], role_data["role_id_to_get"]))

                banned_ids = [data["user_id"] for data in banned_user_data if data["role_id"] == role_to_get.id]

                for member in role_to_have.members:
                    if member.id in banned_ids:
                        print(f"AUTO-RECEIVE: Did not give {member} the role {role_to_get} due to being banned.")
                        continue

                    if role_to_get not in member.roles:
                        print(f"AUTO-RECEIVE: Gave {member} the role {role_to_get}")
                        await asyncio.sleep(1)
                        await member.add_roles(role_to_get)

        print("AUTO-RECEIVE: Done checking for roles to give.")


async def setup(bot):
    await bot.add_cog(AutoReceive(bot))
