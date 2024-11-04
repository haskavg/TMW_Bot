import io
import numpy as np
import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import colormaps
from matplotlib import gridspec, patches
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
    """
    base_cmap = colormaps[cmap_name]
    truncated_cmap = base_cmap(np.linspace(0, truncate_high, base_cmap.N))
    modified_cmap = mcolors.ListedColormap(truncated_cmap)
    modified_cmap.colors[0] = mcolors.to_rgba(zero_color)

    # Set NaN color
    modified_cmap.set_bad(color=nan_color)

    return modified_cmap


def embedded_info(df: pd.DataFrame) -> tuple:
    points_total = df['points_received'].sum()
    breakdown = df.groupby('media_type').agg({'amount_logged': 'sum', 'points_received': 'sum'}).reset_index()
    breakdown['unit_name'] = breakdown['media_type'].apply(lambda x: MEDIA_TYPES[x]['unit_name'])
    breakdown_str = "\n".join([
        f"{row['media_type']}: {row['amount_logged']} {row['unit_name']}{'s' if row['amount_logged'] > 1 else ''} → {round(row['points_received'], 2)} pts"
        for _, row in breakdown.iterrows()
    ])

    return breakdown_str, points_total


# Define a function or dictionary to set consistent styles
def set_plot_styles():
    plt.rcParams.update({
        'axes.titlesize': 20,
        'axes.titleweight': 'bold',
        'axes.labelsize': 14,
        'axes.labelweight': 'bold',
        'xtick.labelsize': 12,
        'ytick.labelsize': 12,
        'axes.facecolor': '#2c2c2d',
        'figure.facecolor': '#2c2c2d',
        'text.color': 'white',
        'axes.labelcolor': 'white',
        'xtick.color': 'white',
        'ytick.color': 'white'
    })


def process_bar_data(df: pd.DataFrame, from_date: datetime, to_date: datetime, color_dict: dict, immersion_type: str = None) -> tuple:
    bar_df = df[from_date:to_date]
    if immersion_type:
        bar_df = bar_df.pivot_table(index=bar_df.index.date, columns='media_type', values='amount_logged', aggfunc='sum', fill_value=0)
    else:
        bar_df = bar_df.pivot_table(index=bar_df.index.date, columns='media_type', values='points_received', aggfunc='sum', fill_value=0)
    bar_df.index = pd.DatetimeIndex(bar_df.index)

    time_frame = pd.date_range(bar_df.index.date.min(), to_date, freq='D')
    bar_df = bar_df.reindex(time_frame, fill_value=0)
    color_dict = {
        "Manga": "#b45865",
        "Anime": "#e48586",
        "Listening Time": "#ffb4c8",
        "Book": "#e5afee",
        "Reading Time": "#b9a7f3",
        "Visual Novel": "#7d84e4",
        "Reading": "#77aaee"
    }
    stacking_order = color_dict.keys()
    existing_columns = [col for col in stacking_order if col in bar_df.columns]
    bar_df = bar_df[existing_columns]

    if not isinstance(bar_df.index, pd.DatetimeIndex):
        bar_df.index = pd.to_datetime(bar_df.index)

    if len(bar_df) > 365 * 2:
        df_plot = bar_df.resample('QE').sum()
        x_lab = " (year-quarter)"
        date_labels = df_plot.index.map(lambda date: f"{date.year}-Q{(date.month - 1) // 3 + 1}")
    elif len(bar_df) > 30 * 7:
        df_plot = bar_df.resample('ME').sum()
        x_lab = " (year-month)"
        date_labels = df_plot.index.strftime("%Y-%m")
    elif len(bar_df) > 31:
        df_plot = bar_df.resample('W').sum()
        x_lab = " (year-week)"
        date_labels = df_plot.index.strftime("%Y-%W")
    else:
        df_plot = bar_df
        date_labels = df_plot.index.strftime("%Y-%m-%d")
        x_lab = ""

    df = df.resample("D").sum()
    full_date_range = pd.date_range(start=datetime(df.index.year.min(), 1, 1), end=datetime(df.index.year.max(), 12, 31))
    df = df.reindex(full_date_range, fill_value=0)
    df["day"] = df.index.weekday
    df["year"] = df.index.year
    heatmap_data = {}
    for year, group in df.groupby("year"):
        heat_array = np.full((7, 53), fill_value=np.nan)
        year_begins_on = group.index.date.min().weekday()
        for date, row in group.iterrows():
            week_num = (date.dayofyear + year_begins_on - 1) // 7
            heat_array[row["day"], week_num] = row["points_received"]
        year_df = pd.DataFrame(heat_array, columns=range(1, 54), index=range(7))
        heatmap_data[year] = year_df

    cmap = modify_cmap('Blues_r', zero_color="#222222", nan_color="#2c2c2d")

    num_years = len(heatmap_data)
    fig_height = 8 + num_years * 3
    combined_fig = plt.figure(figsize=(16, fig_height))
    gs = gridspec.GridSpec(2, 1, height_ratios=[4, num_years], figure=combined_fig)
    combined_fig.patch.set_facecolor('#2c2c2d')

    ax_bar = combined_fig.add_subplot(gs[0])
    ax_bar.set_facecolor('#2c2c2d')
    df_plot.plot(kind='bar', stacked=True, ax=ax_bar, color=[color_dict.get(col, 'gray') for col in df_plot.columns])
    if immersion_type:
        ax_bar.set_title(f"{MEDIA_TYPES[immersion_type]['log_name']}  Over Time", fontweight='bold', fontsize=20)
        ax_bar.set_ylabel(MEDIA_TYPES[immersion_type]['unit_name'] + 's', fontweight='bold', fontsize=14)
        ax_bar.get_legend().remove()
    else:
        ax_bar.set_title('Points Over Time', fontweight='bold', fontsize=20)
        ax_bar.set_ylabel('Points', fontweight='bold', fontsize=14)
        ax_bar.legend(title='Media Type', title_fontsize='14', fontsize='12', loc='best')
    ax_bar.set_xlabel('Date' + x_lab, fontweight='bold', fontsize=14)
    ax_bar.set_xticklabels(date_labels, rotation=45, ha='right')
    ax_bar.grid(color='#8b8c8c')

    gs_heatmaps = gridspec.GridSpecFromSubplotSpec(num_years, 1, subplot_spec=gs[1], hspace=0.4)
    current_date = datetime.now().date()
    for i, (year, data) in enumerate(heatmap_data.items()):
        ax_heat = combined_fig.add_subplot(gs_heatmaps[i])
        sns.heatmap(
            data,
            cmap=cmap,
            linewidths=1.5,
            linecolor="#2c2c2d",
            cbar=False,
            square=True,
            ax=ax_heat
        )
        ax_heat.set_facecolor("#2c2c2d")
        ax_heat.set_title(f"Immersion Heatmap - {year}", color="white")
        ax_heat.axis("off")

        if current_date.year == year:
            current_week = (current_date.timetuple().tm_yday + current_date.weekday() - 1) // 7
            current_day = current_date.weekday()
            rect = patches.Rectangle(
                (current_week, current_day),
                1, 1,
                linewidth=2,
                edgecolor='black',
                facecolor='none'
            )
            ax_heat.add_patch(rect)

    plt.tight_layout(pad=2.0, h_pad=2.0)

    buffer = io.BytesIO()
    combined_fig.savefig(buffer, format='png', facecolor=combined_fig.get_facecolor(), bbox_inches='tight')
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

    @discord.app_commands.command(name='log_stats', description='Display an immersion overview with a specified.')
    @discord.app_commands.describe(
        user='Optional user to display the immersion overview for.',
        from_date='Optional start date (YYYY-MM-DD).',
        to_date='Optional end date (YYYY-MM-DD).',
        immersion_type='Optional type of immersion to filter by (e.g., reading, listening, etc.).',
    )
    @discord.app_commands.choices(immersion_type=LOG_CHOICES)
    async def log_stats(self, interaction: discord.Interaction, user: Optional[discord.User] = None, from_date: Optional[str] = None, to_date: Optional[str] = None, immersion_type: Optional[str] = None):
        if not await is_valid_channel(interaction):
            return await interaction.response.send_message("You can only use this command in DM or in the log channels.", ephemeral=True)
        await interaction.response.defer()

        user_id = user.id if user else interaction.user.id
        user_name = await get_username_db(self.bot, user_id)

        try:
            if from_date:
                from_date = datetime.strptime(from_date, '%Y-%m-%d')
                start_of_year = datetime(from_date.year, 1, 1)  # Start of the year for the heatmap
            else:
                now = datetime.now()
                from_date = now.replace(day=1, hour=0, minute=0, second=0)
                start_of_year = datetime(now.year, 1, 1, 0, 0, 0)
        except ValueError:
            return await interaction.followup.send("Invalid from_date format. Please use YYYY-MM-DD.", ephemeral=True)

        try:
            to_date = datetime.strptime(to_date, '%Y-%m-%d') if to_date else datetime.now()
            to_date = to_date.replace(hour=23, minute=59, second=59)
        except ValueError:
            return await interaction.followup.send("Invalid to_date format. Please use YYYY-MM-DD.", ephemeral=True)

        user_logs = await self.get_user_logs(user_id, start_of_year, to_date, immersion_type)
        logs_df = pd.DataFrame(user_logs, columns=['media_type', 'amount_logged', 'points_received', 'log_date'])
        logs_df['log_date'] = pd.to_datetime(logs_df['log_date'])
        logs_df = logs_df.set_index('log_date')

        if logs_df[from_date:to_date].empty:
            return await interaction.followup.send("No logs found for the specified period.", ephemeral=True)

        figure_buffer = await asyncio.to_thread(generate_plot, logs_df, from_date, to_date, immersion_type)
        breakdown_str, points_total = await asyncio.to_thread(embedded_info, logs_df[from_date:to_date])

        timeframe_str = f"{from_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}"
        embed = discord.Embed(title="Immersion Overview", color=discord.Color.blurple())
        embed.add_field(name="User", value=user_name, inline=True)
        embed.add_field(name="Timeframe", value=timeframe_str, inline=True)
        embed.add_field(name="Points", value=f"{points_total:.2f}", inline=True)
        if immersion_type:
            embed.add_field(name="Immersion Type", value=immersion_type.capitalize(), inline=True)
        embed.add_field(name="Breakdown", value=breakdown_str, inline=False)
        file = discord.File(figure_buffer, filename='immersion_overview.png')
        embed.set_image(url='attachment://immersion_overview.png')

        await interaction.followup.send(file=file, embed=embed)

async def setup(bot):
    await bot.add_cog(ImmersionLogMe(bot))
