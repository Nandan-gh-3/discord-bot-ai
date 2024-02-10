import os
import discord
from dotenv import load_dotenv
from discord.ext import commands
from services.gemini.gemini_service import generate_gemini_response
import json
import logging

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')

if TOKEN is None:
    print("DISCORD_TOKEN not found in environment variables.")
    exit()

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.reactions = True  # Add this line to enable reaction events


bot = commands.Bot(command_prefix='monke ', intents=intents)
# bot = commands.Bot(command_prefix=commands.when_mentioned_or('monke '), intents=intents)

logging.basicConfig(level=logging.INFO)

all_guild_emojis = {}


@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user.name}')
    load_guild_emojis()


@bot.event
async def on_message(ctx):
    if ctx.author == bot.user:
        return

    if bot.user.mentioned_in(ctx):
        async with ctx.channel.typing():
            query = await get_query_from_message(ctx)
            response = generate_gemini_response(
                f"query: {query} \nemojis: {' '.join(all_guild_emojis[ctx.guild.id])} \naccent: funny \ngenerate a very short response for the query with above parameters"
            )
            await send_message_chunks(ctx.reply, response)

    await bot.process_commands(ctx)


@bot.event
async def on_raw_reaction_add(payload):
    if not payload.member.bot and payload.emoji.name == '❌':
        channel = await bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        if message.author.id == bot.user.id:
            await message.delete()


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Invalid command. Use 'monke help' for a list of commands.")


@bot.command(name='show_emojis')
async def show_emojis(ctx):
    guild_id = ctx.guild.id

    if guild_id in all_guild_emojis:
        emojis_data = all_guild_emojis[guild_id]
        emojis_message = ' '.join(emojis_data)
        await send_message_chunks(ctx.send, emojis_message)
    else:
        await ctx.send('No emojis found for this server.')


@bot.command(name='say')
async def say(ctx, *, message):
    async with ctx.channel.typing():
        await send_message_chunks(ctx.send, message)

@bot.command(name='help')
async def help(ctx):
    await send_message_chunks(ctx.send, 'monke help')


@bot.event
async def on_guild_join(guild):
    logging.info(f'Joined new guild: {guild.name}')
    load_guild_emojis()


def load_guild_emojis():
    for guild in bot.guilds:
        emojis_data = [str(emoji) for emoji in guild.emojis]
        all_guild_emojis[guild.id] = emojis_data

    save_emojis_to_json()
    logging.info(f'All guild emojis loaded to memoryy')


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
