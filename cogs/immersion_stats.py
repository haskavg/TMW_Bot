import io
import numpy as np
import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import colormaps
import matplotlib.colors as mcolors
import discord
from discord.ext import commands

from typing import Optional

from datetime import datetime
import asyncio

from lib.media_types import MEDIA_TYPES, LOG_CHOICES
from lib.bot import TMWBot
from lib.immersion_helpers import is_valid_channel

from .username_fetcher import get_username_db
import matplotlib
matplotlib.use('Agg')

GET_USER_LOGS_FOR_PERIOD_QUERY_BASE = """
    SELECT media_type, amount_logged, points_received, log_date
    FROM logs
    WHERE user_id = ? AND log_date BETWEEN ? AND ?
"""

GET_USER_LOGS_FOR_PERIOD_QUERY_WITH_MEDIA_TYPE = GET_USER_LOGS_FOR_PERIOD_QUERY_BASE + " AND media_type = ? ORDER BY log_date;"
GET_USER_LOGS_FOR_PERIOD_QUERY_BASE += " ORDER BY log_date;"


def modify_cmap(cmap_name, zero_color="black", nan_color="black", truncate_high=0.7):
    """
    Modify a colormap to have specific colors for 0 and NaN values, and truncate the upper range.

    Parameters:
    - cmap_name: str, the name of the base colormap.
    - zero_color: str or tuple, color to be used for 0 values.
    - nan_color: str or tuple, color to be used for NaN values.
    - truncate_high: float, fraction of the colormap to keep (0 to 1).

    Returns:
    - new_cmap: A colormap with modified 0 and NaN colors, and truncated upper range.
    """
    base_cmap = colormaps[cmap_name]
    truncated_cmap = base_cmap(np.linspace(0, truncate_high, base_cmap.N))
    modified_cmap = mcolors.ListedColormap(truncated_cmap)
    modified_cmap.colors[0] = mcolors.to_rgba(zero_color)

    # Set NaN color
    modified_cmap.set_bad(color=nan_color)

    return modified_cmap


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

    return breakdown_str, points_total, df


def bar_chart(df: pd.DataFrame, immersion_type: str = None) -> io.BytesIO:
    if immersion_type:
        df_grouped = df.groupby([df['log_date'].dt.date, 'media_type'])['amount_logged'].sum().unstack(fill_value=0)
    else:
        df_grouped = df.groupby([df['log_date'].dt.date, 'media_type'])['points_received'].sum().unstack(fill_value=0)

    # Reindexing the index to include the full date range
    full_date_range = pd.date_range(start=df_grouped.index.min(), end=df_grouped.index.max())
    df_plot = df_grouped.reindex(full_date_range, fill_value=0)

    if len(df_plot) > 365 * 2:
        df_plot = df_plot.resample('QE').sum()

        def format_quarters(date):
            quarter = (date.month - 1) // 3 + 1
            return f"{date.year}-Q{quarter}"

        x_lab = " (year-quarter)"
        date_labels = df_plot.index.map(format_quarters)
    elif len(df_plot) > 30 * 7:
        df_plot = df_plot.resample('ME').sum()
        x_lab = " (year-mounth)"
        date_labels = df_plot.index.strftime("%Y-%m")
    elif len(df_plot) > 31:
        df_plot = df_plot.resample('W').sum()
        x_lab = " (year-week)"
        date_labels = df_plot.index.strftime("%Y-%W")
    else:
        date_labels = df_plot.index.strftime("%Y-%m-%d")
        x_lab = ""

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
    df_plot.plot(kind='bar', stacked=True, ax=ax, color=[color_dict.get(col, 'gray') for col in df_plot.columns])

    if immersion_type:
        plt.title(f"{MEDIA_TYPES[immersion_type]['log_name']}  Over Time", fontweight='bold', fontsize=20)
        plt.ylabel(MEDIA_TYPES[immersion_type]['unit_name'] + 's', fontweight='bold', fontsize=14)
    else:
        plt.title('Points Over Time', fontweight='bold', fontsize=20)
        plt.ylabel('Points', fontweight='bold', fontsize=14)
    plt.xlabel('Date' + x_lab, fontweight='bold', fontsize=14)
    ax.set_xticklabels(date_labels)
    plt.xticks(rotation=45, ha='right')
    plt.legend(loc='best')
    plt.grid()

    # Save the plot to a buffer
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png')
    buffer.seek(0)

    return buffer


def heatmap(df: pd.DataFrame, cmap='Greens') -> io.BytesIO:
    df = df.dropna(subset=["points_received"])
    df = df.set_index("log_date")
    df = df.resample("D").sum()
    full_date_range = pd.date_range(start=datetime(df.index.year.min(), 1, 1), end=datetime(df.index.year.max(), 12, 31))
    df = df.reindex(full_date_range, fill_value=0)
    df["day"] = df.index.weekday
    df["year"] = df.index.year

    heatmap_data = {}
    for year, group in df.groupby("year"):
        heat = np.full((7, 53), fill_value=np.nan)
        year_begins_on = group.index.date.min().weekday()
        for date, row in group.iterrows():
            heat[row["day"], (date.dayofyear + year_begins_on - 1) // 7] = row["points_received"]
        year_df = pd.DataFrame(heat, columns=range(1, 54), index=range(7))
        year_df = year_df.sort_index(axis=1).sort_index(axis=0)
        heatmap_data[year] = year_df

    num_years = len(heatmap_data)
    # Reverse the colormap by appending '_r'
    cmap = modify_cmap(cmap + "_r", zero_color="#222222", nan_color="#2c2c2d")

    fig, axes = plt.subplots(nrows=num_years, ncols=1, figsize=(12, 2 * num_years))

    # If there's only one year, `axes` is not a list, so we make it a list for consistency
    if num_years == 1:
        axes = [axes]

    for ax, (year, df) in zip(axes, heatmap_data.items()):
        sns.heatmap(
            df,
            cmap=cmap,
            linewidths=1.5,
            linecolor="#2c2c2d",
            cbar=False,
            square=True,
            ax=ax,
        )
        ax.set_facecolor("#2c2c2d")
        ax.set_title(f"Immersion Heatmap - {year}", color="white")
        ax.axis("off")

    plt.gcf().set_facecolor("#2c2c2d")
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png')
    buffer.seek(0)

    return buffer


class ImmersionLogMe(commands.Cog):
    def __init__(self, bot: TMWBot):
        self.bot = bot

    async def get_user_logs(self, user_id, from_date, to_date, immersion_type=None):
        if immersion_type:
            query = GET_USER_LOGS_FOR_PERIOD_QUERY_WITH_MEDIA_TYPE
            params = (user_id, from_date.strftime('%Y-%m-%d %H:%M:%S'), to_date.strftime('%Y-%m-%d %H:%M:%S'), immersion_type)
        else:
            query = GET_USER_LOGS_FOR_PERIOD_QUERY_BASE
            params = (user_id, from_date.strftime('%Y-%m-%d %H:%M:%S'), to_date.strftime('%Y-%m-%d %H:%M:%S'))

        user_logs = await self.bot.GET(query, params)
        return user_logs

    @discord.app_commands.command(name='log_stats', description='Display an immersion overview with a specified visualization type.')
    @discord.app_commands.describe(
        user='Optional user to display the immersion overview for.',
        from_date='Optional start date (YYYY-MM-DD).',
        to_date='Optional end date (YYYY-MM-DD).',
        immersion_type='Optional type of immersion to filter by (e.g., reading, listening, etc.).',
        visualization_type='Choose the type of visualization (barchart or heatmap).'
    )
    @discord.app_commands.choices(immersion_type=LOG_CHOICES)
    @discord.app_commands.choices(visualization_type=[
        discord.app_commands.Choice(name='Barchart', value='barchart'),
        discord.app_commands.Choice(name='Heatmap', value='heatmap')
    ])
    async def log_stats(self, interaction: discord.Interaction, user: Optional[discord.User] = None, from_date: Optional[str] = None, to_date: Optional[str] = None, immersion_type: Optional[str] = None, visualization_type: str = 'barchart'):
        if not await is_valid_channel(interaction):
            return await interaction.response.send_message("You can only use this command in DM or in the log channels.", ephemeral=True)
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

        user_logs = await self.get_user_logs(user_id, from_date, to_date, immersion_type)

        if not user_logs:
            return await interaction.followup.send("No logs available for the specified period.", ephemeral=True)

        breakdown_str, points_total, df_logs = await asyncio.to_thread(process_logs, user_logs)

        if visualization_type == 'barchart':
            buffer = await asyncio.to_thread(bar_chart, df_logs, immersion_type)
        elif visualization_type == 'heatmap':
            buffer = await asyncio.to_thread(heatmap, df_logs)

        timeframe_str = f"{from_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}"
        embed = discord.Embed(title="Immersion Overview", color=discord.Color.blurple())
        embed.add_field(name="User", value=user_name, inline=True)
        embed.add_field(name="Timeframe", value=timeframe_str, inline=True)
        embed.add_field(name="Points", value=f"{points_total:.2f}", inline=True)

        if immersion_type:
            embed.add_field(name="Immersion Type", value=immersion_type.capitalize(), inline=True)

        embed.add_field(name="Breakdown", value=breakdown_str, inline=False)

        file = discord.File(buffer, filename="immersion_overview.png")
        embed.set_image(url="attachment://immersion_overview.png")

        await interaction.followup.send(embed=embed, file=file)


async def setup(bot):
    await bot.add_cog(ImmersionLogMe(bot))
