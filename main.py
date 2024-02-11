import os
import discord
import asyncio
from dotenv import load_dotenv
from discord.ext import commands
from services.gemini.gemini_service import generate_gemini_response
import json
import logging

# Constants
PREFIX = 'monke'
DELETE_EMOJI = '❌'

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

if TOKEN is None:
    print("DISCORD_TOKEN not found in environment variables.")
    exit()

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.reactions = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

logging.basicConfig(level=logging.INFO)

all_guild_emojis = {}
spy_count = 0

# Event Handlers
@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user.name}')
    load_guild_emojis()

@bot.event
async def on_message(ctx):
    if ctx.author == bot.user:
        if ctx.content.startswith(PREFIX):
            await bot.process_commands(ctx)
        return

    if bot.user.mentioned_in(ctx):
        async with ctx.channel.typing():
            query = await get_query_from_message(ctx)
            h = await get_last_messages(ctx.channel, spy_count)
            response = generate_gemini_response(query, emojis=all_guild_emojis[ctx.guild.id], h=h)
            await send_message_chunks(ctx.reply, response)

@bot.event
async def on_raw_reaction_add(payload):
    if not payload.member.bot and payload.emoji.name == DELETE_EMOJI:
        channel = await bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        if message.author.id == bot.user.id:
            await message.delete()

@bot.event
async def on_command_error(ctx, error):
    logging.error(error)
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Invalid command. Use 'monke help' for a list of commands.")

# Commands
@bot.command(name='spy')
async def spy(ctx, *, message):
    global spy_count
    try:
        message_array = message.split()
        if message_array:
            message_number = int(message_array[0])
            if 0 < message_number:
                await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"{message_number} messages"))
                await ctx.message.add_reaction('🙄')
                spy_count = message_number
            elif message_number == 0:
                await bot.change_presence(activity=None)
                await ctx.message.add_reaction('🫣')
                spy_count = 0
        else:
            await ctx.send("please use proper format: `monke spy [number of messages]`")
        
        await asyncio.sleep(0.1)
        await ctx.message.delete()

    except Exception as e:
        logging.error(e)

@bot.command(name='say')
async def say(ctx, *, message):
    print(message)
    async with ctx.channel.typing():
        await send_message_chunks(ctx.send, message)

@bot.command(name='show_emojis')
async def show_emojis(ctx):
    guild_id = ctx.guild.id

    if guild_id in all_guild_emojis:
        emojis_data = all_guild_emojis[guild_id]
        emojis_message = ' '.join(emojis_data)
        await send_message_chunks(ctx.send, emojis_message)
    else:
        await ctx.send('No emojis found for this server.')

@bot.event
async def on_guild_join(guild):
    logging.info(f'Joined new guild: {guild.name}')
    load_guild_emojis()

# Utility Functions
async def get_last_messages(channel, count):
    h = []
    previous_role = None
    last_added_role = None
    async for message in channel.history(limit=count):
        current_role = get_user_role(message.author)
        if previous_role != current_role:
            h.append({
                "role": current_role,
                "parts": [f"{(message.author.global_name + ' : ') if message.author.global_name is not None else '' }" + message.content]
            })
            last_added_role = current_role
        else:
            alternating_role = "user" if last_added_role != "user" else "model"
            h.append({
                "role": alternating_role,
                "parts": ['']
            })
            h.append({
                "role": current_role,
                "parts": [f"{(message.author.global_name + ' : ') if message.author.global_name is not None else '' }" + message.content]
            })
        
        previous_role = current_role
    h.reverse()
    return h

def get_user_role(author):
    if isinstance(author, discord.Member):
        roles = author.roles
        highest_role = max(roles, key=lambda role: role.position)
        if highest_role.name == "Monke":
            return "model"
        else:
            return highest_role.name
    else:
        return "user"

async def get_query_from_message(ctx):
    if ctx.reference:
        if ctx.content.find(f"<@{bot.user.id}>") == -1:
            return ""
        referenced_message = await ctx.channel.fetch_message(ctx.reference.message_id)
        query = referenced_message.content.replace(f'<@{bot.user.id}>', '').strip() + '\n' + ctx.content.replace(
            f'<@{bot.user.id}>', '').strip()
    else:
        query = ctx.content.replace(f'<@{bot.user.id}>', '').strip()
    return query

def load_guild_emojis():
    for guild in bot.guilds:
        emojis_data = [str(emoji) for emoji in guild.emojis]
        all_guild_emojis[guild.id] = emojis_data

    save_emojis_to_json()
    logging.info(f'All guild emojis loaded to memory')

def save_emojis_to_json():
    file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'emojis.json')
    with open(file_path, 'w') as json_file:
        json.dump(all_guild_emojis, json_file, indent=4)

async def send_message_chunks(send_func, response):
    chunks = get_chunks(response, 2000)
    for chunk in chunks:
        await send_func(chunk)

def get_chunks(text, chunk_size):
    chunks = []
    while len(text) > chunk_size:
        last_space = text.rfind(' ', 0, chunk_size)
        if last_space == -1:
            chunk = text[:chunk_size]
            text = text[chunk_size:]
        else:
            chunk = text[:last_space]
            text = text[last_space + 1:]
        chunks.append(chunk)

    chunks.append(text)
    return chunks

bot.run(TOKEN, log_handler=None)
