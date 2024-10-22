from lib.bot import TMWBot
import discord
import os
import yaml
from datetime import timedelta
from discord.ext import commands
from discord.ext import tasks

SERVER_SETTINGS_PATH = os.getenv("ALT_SETTINGS_PATH") or "config/settings.yml"
with open(SERVER_SETTINGS_PATH, "r") as f:
    server_settings = yaml.safe_load(f)


async def _get_channel(bot: TMWBot, channel_id: int) -> discord.TextChannel:
    channel = bot.get_channel(channel_id)
    if not channel:
        channel = await bot.fetch_channel(channel_id)
    return channel


async def _get_message(bot: TMWBot, channel_id: int, message_id: int) -> discord.Message:
    channel = await _get_channel(bot, channel_id)
    message = discord.utils.get(bot.cached_messages, id=message_id)
    if not message:
        message = await channel.fetch_message(message_id)
    return message


class Resolver(commands.Cog):
    def __init__(self, bot: TMWBot):
        self.bot = bot

    async def cog_load(self):
        self.ask_if_solved.start()

    async def get_guild_help_forums(self, guild_id: int):
        guild = self.bot.get_guild(guild_id)
        return [channel for channel in guild.forums if channel.id in server_settings["help_channels"][guild_id]]

    @discord.app_commands.command(name="solved", description="Marks a thread as solved.")
    async def solved(self, interaction: discord.Interaction):
        if interaction.guild_id not in server_settings["help_channels"]:
            return await interaction.response.send_message("This server does not have any help channels set up.", ephemeral=True)
        if not isinstance(interaction.channel, discord.Thread):
            await interaction.response.send_message("This command can only be used in a help thread.", ephemeral=True)
        question_forums = await self.get_guild_help_forums(interaction.guild_id)
        if interaction.channel.parent not in question_forums:
            return await interaction.response.send_message("This channel is not a help channel.", ephemeral=True)
        if not "[SOLVED]" in interaction.channel.name or interaction.channel.archived:
            await interaction.response.send_message(f'{interaction.user} closed the thread.')
        else:
            await interaction.response.send_message("This thread is already marked as solved.", ephemeral=True)
        new_thread_name = "[SOLVED] " + \
            interaction.channel.name if not "[SOLVED]" in interaction.channel.name else interaction.channel.name

        await interaction.channel.edit(reason=f'Marked as solved by {interaction.user}', name=new_thread_name, archived=True)

    async def ask_if_solved_for_guild(self, guild: discord.Guild):
        question_forums = await self.get_guild_help_forums(guild.id)
        if not question_forums:
            return
        for question_forum in question_forums:
            for thread in question_forum.threads:
                if "[SOLVED]" in thread.name or thread.archived:
                    continue
                last_message = await _get_message(self.bot, thread.id, thread.last_message_id)
                if discord.utils.utcnow() - last_message.created_at > timedelta(hours=24):
                    await thread.send(f'{thread.owner.mention} has your problem been solved? If so, do  ``/solved`` to close this thread.')

    @tasks.loop(hours=1)
    async def ask_if_solved(self):
        for guild in self.bot.guilds:
            if guild.id not in server_settings["help_channels"]:
                continue
            else:
                await self.ask_if_solved_for_guild(guild)


async def setup(bot):
    await bot.add_cog(Resolver(bot))
