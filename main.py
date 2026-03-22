import discord
from discord.ext import commands

# Create a bot instance and specify the command prefix
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Load cogs
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    # Load the cogs
    bot.load_extension('moderation')
    bot.load_extension('trade')
    bot.load_extension('verify')

# Connect to Discord
TOKEN = 'YOUR_DISCORD_BOT_TOKEN'
bot.run(TOKEN)
