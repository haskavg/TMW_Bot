import discord
import os
import yaml

SERVER_SETTINGS_PATH = os.getenv("ALT_SETTINGS_PATH") or "config/settings.yml"
with open(SERVER_SETTINGS_PATH, "r") as f:
    server_settings = yaml.safe_load(f)


async def is_valid_channel(interaction: discord.Interaction) -> bool:
    if interaction.channel.id in server_settings['immersion_bot']['allowed_log_channels']:
        return True
    if not interaction.user.dm_channel:
        await interaction.client.create_dm(interaction.user)
    if interaction.channel == interaction.user.dm_channel:
        return True
    return False
