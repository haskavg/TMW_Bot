import aiohttp
import discord
import os
from discord.ext import commands
from discord.ext import tasks

from lib.bot import TMWBot

CACHED_TMDB_RESULTS_CREATE_TABLE_QUERY = """
CREATE TABLE IF NOT EXISTS cached_tmdb_results (
    primary_key INTEGER PRIMARY KEY AUTOINCREMENT,
    tmdb_id INTEGER UNIQUE,
    title TEXT,
    original_title TEXT,
    media_type TEXT NOT NULL,
    poster_path TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_TMDB_INDEX_QUERY_1 = """
CREATE INDEX IF NOT EXISTS idx_tmdb_title ON cached_tmdb_results (title);
"""
CREATE_TMDB_INDEX_QUERY_2 = """
CREATE INDEX IF NOT EXISTS idx_tmdb_original_title ON cached_tmdb_results (original_title);
"""

CACHED_TMDB_RESULTS_INSERT_QUERY = """
INSERT INTO cached_tmdb_results (tmdb_id, title, original_title, media_type, poster_path)
VALUES (?, ?, ?, ?, ?)
ON CONFLICT(tmdb_id) DO UPDATE SET
    title=excluded.title,
    original_title=excluded.original_title,
    media_type=excluded.media_type,
    poster_path=excluded.poster_path,
    timestamp=CURRENT_TIMESTAMP;
"""

# TODO: Optimize for efficient search
CACHED_TMDB_RESULTS_SEARCH_QUERY = """
SELECT tmdb_id, title, original_title, poster_path, media_type
FROM cached_tmdb_results
WHERE (LOWER(REPLACE(title, ' ', '')) LIKE '%' || LOWER(REPLACE(?, ' ', '')) || '%'
    OR LOWER(REPLACE(original_title, ' ', '')) LIKE '%' || LOWER(REPLACE(?, ' ', '')) || '%')
LIMIT 10;
"""

CACHED_TMDB_THUMBNAIL_QUERY = """
SELECT poster_path FROM cached_tmdb_results
WHERE tmdb_id = ?;
"""


async def query_tmdb(interaction: discord.Interaction, current_input: str, bot: TMWBot):
    api_key = os.getenv("TMDB_API_KEY")
    if not api_key:
        raise ValueError("TMDB API Key not found in environment variables")

    url = f"https://api.themoviedb.org/3/search/multi?api_key={api_key}&query={current_input}"
    base_image_url = "https://image.tmdb.org/t/p/original"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                media_list = data.get("results", [])

                choices = []
                for media in media_list:
                    media_id = media.get("id")
                    title = media.get("name") or media.get("title")
                    original_title = media.get("original_name") or media.get("original_title")
                    media_type = media.get("media_type")
                    poster_path = media.get("poster_path")
                    poster_path = f"{base_image_url}{poster_path}" if poster_path else None
                    if not title or not media_id:
                        continue

                    choice_name = f"{title[:80]} (ID: {media_id})"
                    if title:
                        choices.append(discord.app_commands.Choice(name=choice_name, value=str(media_id)))

                    await bot.RUN(CACHED_TMDB_RESULTS_INSERT_QUERY, (media_id, title, original_title, media_type, poster_path))

                return choices[:10]
            elif response.status == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                print(f"API rate limit exceeded. Please wait {retry_after} seconds before retrying.")
                return []
            else:
                return []


async def listening_autocomplete(interaction: discord.Interaction, current_input: str):
    tmw_bot = interaction.client
    tmw_bot: TMWBot

    cached_results = await tmw_bot.GET(CACHED_TMDB_RESULTS_SEARCH_QUERY, (f"%{current_input}%", f"%{current_input}%"))
    choices = []
    for cached_result in cached_results:
        tmdb_id, title, original_title, _, _ = cached_result
        choice_name = f"{title[:80]} (ID: {tmdb_id})"
        choices.append(discord.app_commands.Choice(name=choice_name, value=str(tmdb_id)))

    if len(choices) < 3:
        tmdb_choices = await query_tmdb(interaction, current_input, tmw_bot)
        choices.extend(tmdb_choices)

    return choices[:10]
