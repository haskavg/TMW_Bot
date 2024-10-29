import discord
import yaml
import os
from discord.ext import commands
from typing import Optional

INFO_COMMANDS_PATH = "config/info_commands.yml"
with open(INFO_COMMANDS_PATH, "r") as f:
    info_commands = yaml.safe_load(f)


async def help_autocomplete(interaction: discord.Interaction, current: str):
    if not current:
        return [discord.app_commands.Choice(name=key, value=key) for key in info_commands.keys()][:25]
    else:
        return [discord.app_commands.Choice(name=key, value=key)
                for key in info_commands.keys()
                if current.lower() in key.lower()][:25]


class HelpCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="help", description="Get various pieces of valuable knowledge!")
    @discord.app_commands.describe(help_key="The topic.")
    @discord.app_commands.autocomplete(help_key=help_autocomplete)
    async def help(self, interaction: discord.Interaction, help_key: str):
        if help_key not in info_commands.keys():
            await interaction.response.send_message("Help key not found.", ephemeral=True)
            return

        text_info = info_commands.get(help_key)
        embed = discord.Embed(title=f"Help for `{help_key}`", description=text_info, color=discord.Color.random())
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(HelpCommand(bot))
