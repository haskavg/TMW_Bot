import discord
import os
import yaml

IMMERSION_LOG_SETTINGS = os.getenv("IMMERSION_LOG_SETTINGS") or "config/immersion_log_settings.yml"
with open(IMMERSION_LOG_SETTINGS, "r") as f:
    immersion_log_settings = yaml.safe_load(f)


async def is_valid_channel(interaction: discord.Interaction) -> bool:
    if interaction.channel.id in immersion_log_settings['immersion_bot']['allowed_log_channels']:
        return True
    if not interaction.user.dm_channel:
        await interaction.client.create_dm(interaction.user)
    if interaction.channel == interaction.user.dm_channel:
        return True
    return False
