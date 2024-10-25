from lib.bot import TMWBot
from lib.anilist_autocomplete import anime_manga_name_autocomplete, CACHED_ANILIST_RESULTS_CREATE_TABLE_QUERY, CREATE_ANILIST_INDEX_QUERY_1, CREATE_ANILIST_INDEX_QUERY_2, CACHED_ANILIST_THUMBNAIL_QUERY
from lib.vndb_autocomplete import vn_name_autocomplete, CACHED_VNDB_RESULTS_CREATE_TABLE_QUERY, CREATE_VNDB_INDEX_QUERY, CACHED_VNDB_THUMBNAIL_QUERY
from lib.tmdb_autocomplete import listening_autocomplete, CACHED_TMDB_RESULTS_CREATE_TABLE_QUERY, CREATE_TMDB_INDEX_QUERY_1, CREATE_TMDB_INDEX_QUERY_2, CACHED_TMDB_THUMBNAIL_QUERY

import discord
import os
import yaml
import random
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

GET_CONSECUTIVE_DAYS_QUERY = """
    SELECT log_date
    FROM logs
    WHERE user_id = ?
    GROUP BY log_date
    ORDER BY log_date DESC;
"""

GET_POINTS_FOR_CURRENT_MONTH_QUERY = """
    SELECT SUM(points_received) AS total_points
    FROM logs
    WHERE user_id = ? AND strftime('%Y-%m', log_date) = strftime('%Y-%m', 'now');
"""


async def log_name_autocomplete(interaction: discord.Interaction, current_input: str):
    current_input = current_input.strip()
    if not current_input:
        return []
    if len(current_input) <= 1:
        return []
    media_type = interaction.namespace['media_type']
    if MEDIA_TYPES[media_type]['autocomplete']:
        result = await MEDIA_TYPES[media_type]['autocomplete'](interaction, current_input)
        return result
    return []

MEDIA_TYPES = {
    "Visual Novel": {"log_name": "Visual Novel (in characters read)", "short_id": "VN", "max_logged": 2000000, "autocomplete": vn_name_autocomplete, "points_multiplier": 0.0028571428571429, "thumbnail_query": CACHED_VNDB_THUMBNAIL_QUERY},
    "Manga": {"log_name": "Manga (in pages read)", "short_id": "MANGA", "max_logged": 1000, "autocomplete": anime_manga_name_autocomplete, "points_multiplier": 0.125, "thumbnail_query": CACHED_ANILIST_THUMBNAIL_QUERY},
    "Anime": {"log_name": "Anime (in episodes watched)", "short_id": "ANIME", "max_logged": 100, "autocomplete": anime_manga_name_autocomplete, "points_multiplier": 13.0, "thumbnail_query": CACHED_ANILIST_THUMBNAIL_QUERY},
    "Book": {"log_name": "Book (in pages read)", "short_id": "BOOK", "max_logged": 500, "autocomplete": None, "points_multiplier": 1, "thumbnail_query": None},
    "Reading Time": {"log_name": "Reading Time (in minutes)", "short_id": "RT", "max_logged": 420, "autocomplete": None, "points_multiplier": 0.67, "thumbnail_query": None},
    "Listening Time": {"log_name": "Listening Time (in minutes)", "short_id": "LT", "max_logged": 420, "autocomplete": listening_autocomplete, "points_multiplier": 0.67, "thumbnail_query": CACHED_TMDB_THUMBNAIL_QUERY},
    "Reading": {"log_name": "Reading (in characters read)", "short_id": "READING", "max_logged": 2000000, "autocomplete": None, "points_multiplier": 0.0028571428571429, "thumbnail_query": None},
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
        await self.bot.RUN(CACHED_ANILIST_RESULTS_CREATE_TABLE_QUERY)
        await self.bot.RUN(CREATE_ANILIST_INDEX_QUERY_1)
        await self.bot.RUN(CREATE_ANILIST_INDEX_QUERY_2)
        await self.bot.RUN(CACHED_VNDB_RESULTS_CREATE_TABLE_QUERY)
        await self.bot.RUN(CREATE_VNDB_INDEX_QUERY)
        await self.bot.RUN(CACHED_TMDB_RESULTS_CREATE_TABLE_QUERY)
        await self.bot.RUN(CREATE_TMDB_INDEX_QUERY_1)
        await self.bot.RUN(CREATE_TMDB_INDEX_QUERY_2)

    @discord.app_commands.command(name='log', description='Log your immersion!')
    @discord.app_commands.describe(
        media_type='The type of media you are logging.',
        amount='Amount. For time-based logs, use the number of minutes.',
        name='You can use VNDB ID/Title for VNs, AniList ID/Titlefor Anime/Manga, TMDB titles for Listening or provide free text.',
        comment='Short comment about your log.',
        backfill_date='The date for the log, in YYYY-MM-DD format. You can log no more than 7 days into the past.'
    )
    @discord.app_commands.choices(media_type=LOG_CHOICES)
    @discord.app_commands.autocomplete(name=log_name_autocomplete)
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

        points_received = round(amount * MEDIA_TYPES[media_type]['points_multiplier'], 2)

        # TODO: CHECK IF GOALS FULFILLED

        points_before = await self.get_points_for_current_month(interaction.user.id)

        await self.bot.RUN(
            CREATE_LOG_QUERY,
            (interaction.user.id, media_type, name, comment, amount, points_received, log_date)
        )

        points_after = await self.get_points_for_current_month(interaction.user.id)

        # TODO: CREATE NICE EMBED FOR LOGS
        print(points_before, points_after)

        random_guild_emoji = random.choice(interaction.guild.emojis)
        consecutive_days = await self.get_consecutive_days_logged(interaction.user.id)

        await interaction.followup.send("Your log has been recorded successfully!", ephemeral=True)

    async def get_consecutive_days_logged(self, user_id: int) -> int:
        result = await self.bot.GET(GET_CONSECUTIVE_DAYS_QUERY, (user_id,))
        if not result:
            return 0

        consecutive_days = 0
        today = discord.utils.utcnow().date()

        for row in result:
            log_date = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S').date()
            if log_date == today - timedelta(days=consecutive_days):
                consecutive_days += 1
            else:
                break

        return consecutive_days

    async def get_points_for_current_month(self, user_id: int) -> float:
        result = await self.bot.GET(GET_POINTS_FOR_CURRENT_MONTH_QUERY, (user_id,))
        if result and result[0] is not None:
            return result[0][0]
        return 0.0


async def setup(bot):
    await bot.add_cog(ImmersionLog(bot))
