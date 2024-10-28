import discord
import yaml

from lib.vndb_autocomplete import vn_name_autocomplete, CACHED_VNDB_THUMBNAIL_QUERY, CACHED_VNDB_TITLE_QUERY
from lib.anilist_autocomplete import anime_manga_name_autocomplete, CACHED_ANILIST_THUMBNAIL_QUERY, CACHED_ANILIST_TITLE_QUERY
from lib.tmdb_autocomplete import listening_autocomplete, CACHED_TMDB_THUMBNAIL_QUERY, CACHED_TMDB_TITLE_QUERY

IMMERSION_LOG_SETTINGS = "config/immersion_log_settings.yml"
with open(IMMERSION_LOG_SETTINGS, "r") as f:
    immersion_log_settings = yaml.safe_load(f)

MEDIA_TYPES = {
    "Visual Novel": {
        "log_name": "Visual Novel (in characters read)",
        "short_id": "VN",
        "max_logged": 2000000,
        "autocomplete": vn_name_autocomplete,
        "points_multiplier": immersion_log_settings['points_multipliers']["Visual_Novel"],
        "thumbnail_query": CACHED_VNDB_THUMBNAIL_QUERY,
        "title_query": CACHED_VNDB_TITLE_QUERY,
        "unit_name": "character",
        "source_url": "https://vndb.org/",
        "Achievement_Group": "Visual Novel",
    },
    "Manga": {
        "log_name": "Manga (in pages read)",
        "short_id": "MANGA",
        "max_logged": 1000,
        "autocomplete": anime_manga_name_autocomplete,
        "points_multiplier": immersion_log_settings['points_multipliers']["Manga"],
        "thumbnail_query": CACHED_ANILIST_THUMBNAIL_QUERY,
        "title_query": CACHED_ANILIST_TITLE_QUERY,
        "unit_name": "page",
        "source_url": "https://anilist.co/manga/",
        "Achievement_Group": "Manga",
    },
    "Anime": {
        "log_name": "Anime (in episodes watched)",
        "short_id": "ANIME",
        "max_logged": 100,
        "autocomplete": anime_manga_name_autocomplete,
        "points_multiplier": immersion_log_settings['points_multipliers']["Anime"],
        "thumbnail_query": CACHED_ANILIST_THUMBNAIL_QUERY,
        "title_query": CACHED_ANILIST_TITLE_QUERY,
        "unit_name": "episode",
        "source_url": "https://anilist.co/anime/",
        "Achievement_Group": "Anime",
    },
    "Book": {
        "log_name": "Book (in pages read)",
        "short_id": "BOOK",
        "max_logged": 500,
        "autocomplete": None,
        "points_multiplier": immersion_log_settings['points_multipliers']["Book"],
        "thumbnail_query": None,
        "title_query": None,
        "unit_name": "page",
        "source_url": None,
        "Achievement_Group": "Reading",
    },
    "Reading Time": {
        "log_name": "Reading Time (in minutes)",
        "short_id": "RT",
        "max_logged": 1440,
        "autocomplete": None,
        "points_multiplier": immersion_log_settings['points_multipliers']["Reading_Time"],
        "thumbnail_query": None,
        "title_query": None,
        "unit_name": "minute",
        "source_url": None,
        "Achievement_Group": "Reading",
    },
    "Listening Time": {
        "log_name": "Listening Time (in minutes)",
        "short_id": "LT",
        "max_logged": 1440,
        "autocomplete": listening_autocomplete,
        "points_multiplier": immersion_log_settings['points_multipliers']["Listening_Time"],
        "thumbnail_query": CACHED_TMDB_THUMBNAIL_QUERY,
        "title_query": CACHED_TMDB_TITLE_QUERY,
        "unit_name": "minute",
        "source_url": "https://www.themoviedb.org/{tmdb_media_type}/",
        "Achievement_Group": "Listening",
    },
    "Reading": {
        "log_name": "Reading (in characters read)",
        "short_id": "READING",
        "max_logged": 2000000,
        "autocomplete": None,
        "points_multiplier": immersion_log_settings['points_multipliers']["Reading"],
        "thumbnail_query": None,
        "title_query": None,
        "unit_name": "character",
        "source_url": None,
        "Achievement_Group": "Reading",
    },
}


LOG_CHOICES = [discord.app_commands.Choice(
    name=MEDIA_TYPES[media_type]['log_name'], value=media_type) for media_type in MEDIA_TYPES.keys()]
