from lib.bot import TMWBot
import discord
import os
import yaml
from typing import Optional
from datetime import timedelta, datetime
from discord.ext import commands
from discord.ext import tasks

SERVER_SETTINGS_PATH = os.getenv("ALT_SETTINGS_PATH") or "config/settings.yml"
with open(SERVER_SETTINGS_PATH, "r") as f:
    server_settings = yaml.safe_load(f)

CREATE_LOGS_TABLE = """
    CREATE TABLE IF NOT EXISTS logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    media_type TEXT NOT NULL,
    media_name TEXT,
    comment TEXT,
    amount_logged INTEGER NOT NULL,
    points_received REAL NOT NULL,
    log_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"""

CREATE_LOG_QUERY = """
    INSERT INTO logs (user_id, media_type, media_name, comment, amount_logged, points_received, log_date)
    VALUES (?, ?, ?, ?, ?, ?, ?);"""


async def anime_manga_name_autocomplete(interaction: discord.Interaction, current_input: str):
    # TODO: AniList API
    pass


async def vn_name_autocomplete(interaction: discord.Interaction, current_input: str):
    # TODO: VNDB API
    pass


async def listening_autocomplete(interaction: discord.Interaction, current_input: str):
    # TODO: TMDB API
    pass


async def log_name_autocomplete(interaction: discord.Interaction, current_input: str):
    media_type = interaction.namespace['media_type']
    if MEDIA_TYPES[media_type]['autocomplete']:
        return await MEDIA_TYPES[media_type]['autocomplete'](interaction, current_input)
    return []

MEDIA_TYPES = {
    "Visual Novel": {"log_name": "Visual Novel (in characters read)", "short_id": "VN", "max_logged": 2000000, "autocomplete": vn_name_autocomplete, "points_multiplier": 0.0028571428571429},
    "Manga": {"log_name": "Manga (in pages read)", "short_id": "MANGA", "max_logged": 1000, "autocomplete": anime_manga_name_autocomplete, "points_multiplier": 0.125},
    "Anime": {"log_name": "Anime (in episodes watched)", "short_id": "ANIME", "max_logged": 100, "autocomplete": anime_manga_name_autocomplete, "points_multiplier": 13.0},
    "Book": {"log_name": "Book (in pages read)", "short_id": "BOOK", "max_logged": 500, "autocomplete": None, "points_multiplier": 1},
    "Reading Time": {"log_name": "Reading Time (in minutes)", "short_id": "RT", "max_logged": 420, "autocomplete": None, "points_multiplier": 0.67},
    "Listening Time": {"log_name": "Listening Time (in minutes)", "short_id": "LT", "max_logged": 420, "autocomplete": listening_autocomplete, "points_multiplier": 0.67},
    "Reading": {"log_name": "Reading (in characters read)", "short_id": "READING", "max_logged": 2000000, "autocomplete": None, "points_multiplier": 0.0028571428571429},
}

LOG_CHOICES = [discord.app_commands.Choice(
    name=MEDIA_TYPES[media_type]['log_name'], value=media_type) for media_type in MEDIA_TYPES.keys()]


def is_valid_channel(interaction: discord.Interaction) -> bool:
    if interaction.channel.id in server_settings['immersion_bot']['allowed_log_channels']:
        return True
    if interaction.channel == interaction.user.dm_channel:
        return True
    return False


class ImmersionLog(commands.Cog):
    def __init__(self, bot: TMWBot):
        self.bot = bot

    async def cog_load(self):
        await self.bot.RUN(CREATE_LOGS_TABLE)

    # TODO: (MAYBE) USE OPTIONAL FIELDS FOR API ACCESS -> ALL FIELDS SUPPORT API ACCESS

    @discord.app_commands.command(name='log', description='Log your immersion!')
    @discord.app_commands.describe(
        media_type='The type of media you are logging.',
        amount='Amount. For time-based logs, use the number of minutes.',
        name='You can use VNDB ID/Titles and AniList ID/Titles, or provide free text.',
        comment='Short comment about your log.',
        backfill_date='The date for the log, in YYYY-MM-DD format. You can log no more than 7 days into the past.'
    )
    @discord.app_commands.choices(media_type=LOG_CHOICES)
    async def log(self, interaction: discord.Interaction, media_type: str, amount: str, name: Optional[str], comment: Optional[str], backfill_date: Optional[str]):
        if not is_valid_channel(interaction):
            return await interaction.response.send_message("You can only use this command in DM or in the log channels.", ephemeral=True)
        if not amount.isdigit():
            return await interaction.response.send_message("Amount must be a valid number.", ephemeral=True)
        amount = int(amount)
        if amount < 0:
            return await interaction.response.send_message("Amount must be a positive number.", ephemeral=True)
        allowed_limit = MEDIA_TYPES[media_type]['max_logged']
        if amount > allowed_limit:
            return await interaction.response.send_message(f"Amount must be less than {allowed_limit} for `{MEDIA_TYPES[media_type]['log_name']}`.", ephemeral=True)

        if name and len(name) > 150:
            return await interaction.response.send_message("Name must be less than 150 characters.", ephemeral=True)
        if comment and len(comment) > 200:
            return await interaction.response.send_message("Comment must be less than 200 characters.", ephemeral=True)

        if backfill_date is None:
            backfill_date = discord.utils.utcnow().strftime('%Y-%m-%d')
        try:
            log_date = datetime.strptime(backfill_date, '%Y-%m-%d')
            today = discord.utils.utcnow().date()
            if log_date.date() > today:
                return await interaction.response.send_message("You cannot log a date in the future.", ephemeral=True)
            if (today - log_date.date()).days > 7:
                return await interaction.response.send_message("You cannot log a date more than 7 days in the past.", ephemeral=True)
        except ValueError:
            return await interaction.response.send_message("Invalid date format. Please use YYYY-MM-DD.", ephemeral=True)

        await interaction.response.defer()

        # TODO: IF API ACCESS, SAVE RESPONSE DATA

        # Restrict to two decimal places
        points_received = round(amount * MEDIA_TYPES[media_type]['points_multiplier'], 2)

        # TODO: CHECK IF GOALS FULFILLED

        # TODO: CHECK IF ACHIEVEMENTS UNLOCKED

        await self.bot.RUN(
            CREATE_LOG_QUERY,
            (interaction.user.id, media_type, name, comment, amount, points_received, log_date)
        )

        # TODO: CREATE NICE EMBED FOR LOGS

        await interaction.followup.send("Your log has been recorded successfully!", ephemeral=True)


async def setup(bot):
    await bot.add_cog(ImmersionLog(bot))
