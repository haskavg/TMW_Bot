from lib.bot import TMWBot
import discord
import os
import yaml
from typing import Optional
from datetime import timedelta
from discord.ext import commands
from discord.ext import tasks

SERVER_SETTINGS_PATH = os.getenv("ALT_SETTINGS_PATH") or "config/settings.yml"
with open(SERVER_SETTINGS_PATH, "r") as f:
    server_settings = yaml.safe_load(f)


async def anime_manga_name_autocomplete(interaction: discord.Interaction, current_input: str):
    pass


async def vn_name_autocomplete(interaction: discord.Interaction, current_input: str):
    pass


async def listening_autocomplete(interaction: discord.Interaction, current_input: str):
    pass


async def log_name_autocomplete(interaction: discord.Interaction, current_input: str):
    media_type = interaction.namespace['media_type']
    if MEDIA_TYPES[media_type]['autocomplete']:
        return await MEDIA_TYPES[media_type]['autocomplete'](interaction, current_input)
    return []

MEDIA_TYPES = {
    "Visual Novel": {"log_name": "Visual Novel (in characters read)", "short_id": "VN", "max_logged": 2000000, "autocomplete": vn_name_autocomplete},
    "Manga": {"log_name": "Manga (in pages read)", "short_id": "MANGA", "max_logged": 1000, "autocomplete": anime_manga_name_autocomplete},
    "Anime": {"log_name": "Anime (in episodes watched)", "short_id": "ANIME", "max_logged": 100, "autocomplete": anime_manga_name_autocomplete},
    "Book": {"log_name": "Book (in pages read)", "short_id": "BOOK", "max_logged": 500, "autocomplete": None},
    "Reading Time": {"log_name": "Reading Time (in minutes)", "short_id": "RT", "max_logged": 420, "autocomplete": None},
    "Listening Time": {"log_name": "Listening Time (in minutes)", "short_id": "LT", "max_logged": 420, "autocomplete": listening_autocomplete},
    "Reading": {"log_name": "Reading (in characters read)", "short_id": "READING", "max_logged": 2000000, "autocomplete": None},
}

LOG_CHOICES = [discord.app_commands.Choice(
    name=MEDIA_TYPES[media_type]['log_name'], value=media_type) for media_type in MEDIA_TYPES.keys()]


class ImmersionLog(commands.Cog):
    def __init__(self, bot: TMWBot):
        self.bot = bot

    async def cog_load(self):
        pass

    @discord.app_commands.command(name='log', description=f'Log your immersion!')
    @discord.app_commands.describe(amount='Amount. For time based logs, use the amount of minutes')
    @discord.app_commands.describe(comment='Additional comment')
    @discord.app_commands.describe(name='You can use VNDB ID/Titles and AniList ID/Titles. Or free text.')
    @discord.app_commands.choices(media_type=LOG_CHOICES)
    async def log(self, interaction: discord.Interaction, media_type: str, amount: str, name: Optional[str], comment: Optional[str]):
        pass


async def setup(bot):
    await bot.add_cog(ImmersionLog(bot))
