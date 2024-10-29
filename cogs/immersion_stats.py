import discord
from discord.ext import commands

from typing import Optional

from datetime import datetime, timedelta
from collections import defaultdict
import asyncio

from lib.media_types import MEDIA_TYPES
from lib.bot import TMWBot

from .username_fetcher import get_username_db

import matplotlib.pyplot as plt
import pandas as pd
import io

GET_USER_LOGS_FOR_PERIOD_QUERY = """
    SELECT media_type, amount_logged, points_received, log_date
    FROM logs
    WHERE user_id = ? AND log_date BETWEEN ? AND ?
    ORDER BY log_date;
"""


def process_logs(logs):
    df = pd.DataFrame(logs, columns=['media_type', 'amount_logged', 'points_received', 'log_date'])
    df['log_date'] = pd.to_datetime(df['log_date'])

    points_total = df['points_received'].sum()

    breakdown = df.groupby('media_type').agg({'amount_logged': 'sum', 'points_received': 'sum'}).reset_index()
    breakdown['unit_name'] = breakdown['media_type'].apply(lambda x: MEDIA_TYPES[x]['unit_name'])

    breakdown_str = "\n".join([
        f"{row['media_type']}: {row['amount_logged']} {row['unit_name']}{'s' if row['amount_logged'] > 1 else ''} → {round(row['points_received'], 2)} pts"
        for _, row in breakdown.iterrows()
    ])

    log_dict = defaultdict(lambda: defaultdict(lambda: 0))
    for log in logs:
        log_date = pd.to_datetime(log[3])
        log_dict[log[0]][log_date.date()] += log[2]

    df_plot = pd.DataFrame(log_dict).fillna(0)

    color_dict = {
        "Book": "tab:orange",
        "Manga": "tab:red",
        "Reading": "tab:pink",
        "Reading Time": "tab:green",
        "Visual Novel": "tab:cyan",
        "Anime": "tab:purple",
        "Listening Time": "tab:blue",
    }

    fig, ax = plt.subplots(figsize=(16, 12))
    plt.title('Points Over Time', fontweight='bold', fontsize=20)
    plt.ylabel('Points', fontweight='bold', fontsize=14)
    plt.xlabel('Date', fontweight='bold', fontsize=14)

    accumulator = 0
    for media_type in df_plot.columns:
        col = df_plot[media_type]
        ax.bar(df_plot.index, col, bottom=accumulator, color=color_dict.get(media_type, 'gray'), label=media_type)
        accumulator += col

    ax.legend(df_plot.columns)
    plt.xticks(df_plot.index, fontsize=10, rotation=45, horizontalalignment='right')
    plt.grid()

    # Save the plot to a buffer
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png')
    buffer.seek(0)

    return breakdown_str, points_total, buffer


class ImmersionLogMe(commands.Cog):
    def __init__(self, bot: TMWBot):
        self.bot = bot

    @discord.app_commands.command(name='log_stats', description='Display an immersion overview for a specified period.')
    @discord.app_commands.describe(user='Optional user to display the immersion overview for.', from_date='Optional start date (YYYY-MM-DD).', to_date='Optional end date (YYYY-MM-DD).')
    async def log_stats(self, interaction: discord.Interaction, user: Optional[discord.User] = None, from_date: Optional[str] = None, to_date: Optional[str] = None):
        await interaction.response.defer()

        user_id = user.id if user else interaction.user.id
        user_name = await get_username_db(self.bot, user_id)
        try:
            if from_date:
                from_date = datetime.strptime(from_date, '%Y-%m-%d')
            else:
                now = datetime.now()
                from_date = now.replace(day=1, hour=0, minute=0, second=0)
        except ValueError:
            return await interaction.followup.send("Invalid from_date format. Please use YYYY-MM-DD.", ephemeral=True)

        try:
            to_date = datetime.strptime(to_date, '%Y-%m-%d') if to_date else datetime.now()
            to_date = to_date.replace(hour=23, minute=59, second=59)
        except ValueError:
            return await interaction.followup.send("Invalid to_date format. Please use YYYY-MM-DD.", ephemeral=True)

        user_logs = await self.bot.GET(GET_USER_LOGS_FOR_PERIOD_QUERY, (user_id, from_date.strftime('%Y-%m-%d %H:%M:%S'), to_date.strftime('%Y-%m-%d %H:%M:%S')))

        if not user_logs:
            return await interaction.followup.send("No logs available for the specified period.", ephemeral=True)

        breakdown_str, points_total, buffer = await asyncio.to_thread(process_logs, user_logs)

        timeframe_str = f"{from_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}"
        embed = discord.Embed(title="Immersion Overview", color=discord.Color.blurple())
        embed.add_field(name="User", value=user_name, inline=True)
        embed.add_field(name="Timeframe", value=timeframe_str, inline=True)
        embed.add_field(name="Points", value=f"{points_total:.2f}", inline=True)
        embed.add_field(name="Breakdown", value=breakdown_str, inline=False)

        file = discord.File(buffer, filename="immersion_overview.png")
        embed.set_image(url="attachment://immersion_overview.png")

        await interaction.followup.send(embed=embed, file=file)


async def setup(bot):
    await bot.add_cog(ImmersionLogMe(bot))
