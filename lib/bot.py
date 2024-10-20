import os
import discord
import aiosqlite
from discord.ext import commands


class TMWBot(commands.Bot):
    def __init__(self, command_prefix, cog_folder="cogs", path_to_db="data/db.sqlite3"):

        super().__init__(command_prefix=command_prefix, intents=discord.Intents.all())
        self.cog_folder = cog_folder
        self.path_to_db = path_to_db

        db_directory = os.path.dirname(self.path_to_db)
        if not os.path.exists(db_directory):
            os.makedirs(db_directory)

    async def on_ready(self):
        print(f"Logged in as {self.user}")

    async def load_cogs(self, cogs_to_load):

        cogs = [cog for cog in os.listdir(self.cog_folder) if cog.endswith(".py") and
                (cogs_to_load == "*" or cog[:-3] in cogs_to_load)]

        for cog in cogs:
            cog = f"{self.cog_folder}.{cog[:-3]}"
            await self.load_extension(cog)
            print(f"Loaded {cog}")

    async def RUN(self, query: str, params: tuple = ()):
        async with aiosqlite.connect(self.path_to_db) as db:
            await db.execute(query, params)
            await db.commit()

    async def GET(self, query: str, params: tuple = ()):
        async with aiosqlite.connect(self.path_to_db) as db:
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return rows

    async def GET_ONE(self, query: str, params: tuple = ()):
        async with aiosqlite.connect(self.path_to_db) as db:
            async with db.execute(query, params) as cursor:
                row = await cursor.fetchone()
                return row
