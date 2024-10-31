[![Deploy Discord Bot](https://github.com/friedrich-de/TMW_Bot/actions/workflows/main.yml/badge.svg)](https://github.com/friedrich-de/TMW_Bot/actions/workflows/main.yml)

### How to contribute
1. Report bugs and suggest features in the issues tab.

2. Create a PR with your changes. The bot is made to run server indepedently, so you can run it anywhere you want to test your changes.

### How to run

1. Clone the repository
2. Create a virtual environment and install the requirements with `pip install -r requirements.txt`
3. Create a `.env` file in the root directory and add the following variables:

    `TOKEN=YOUR_DISCORD_BOT_TOKEN`

    `AUTHORIZED_USERS=960526101833191435,501009840437592074` Comma separated list of user IDs who can use bot management commands.

    `DEBUG_USER=960526101833191435` User ID of the user who gets sent debug messages.

    `COMMAND_PREFIX=%`

    `PATH_TO_DB=data/db.sqlite3`

    `TMDB_API_KEY=YOUR_TMDB_API_KEY`

4. Run the bot with `python main.py`

### Overwrite Settings

You can link to alternative setting files by setting the path in the corresponding environment variable. 

Each part of the bot can be configured separately. Please look into the cog files for the variable names.


### General ToDo
- Clubs
- Bookmarker

### Acknowledgements
This bot is based on the following project (mostly used as a feature reference without or minimal direct code reuse):

- **DJT-Discord Bot** - Unlicensed (Corresponding code in this project is licensed under the GPL-3.0 license).
  - Original source: [https://github.com/friedrich-de/DJT-Discord-Bot](https://github.com/friedrich-de/DJT-Discord-Bot)
- **gatekeeper** - Licensed under the GPL-3.0 license.
  - Original source: [https://github.com/themoeway/gatekeeper](https://github.com/themoeway/gatekeeper)
- **selfmutebot** - Licensed under the MIT license.
  - Original source: [https://github.com/themoeway/selfmutebot](https://github.com/themoeway/selfmutebot)
- **tmw-utility-bot** - Licensed under the GPL-3.0 license.
  - Original source: [https://github.com/themoeway/tmw-utility-bot](https://github.com/themoeway/tmw-utility-bot)
- **Immersionbot** - Licensed under the MIT license.
  - Original source: [https://github.com/themoeway/Immersionbot](https://github.com/themoeway/Immersionbot)  
