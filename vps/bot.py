import discord
import requests
import json
from model_bridge import query_llm
from status_api import is_model_online
from dotenv import load_dotenv
import os
import atexit
from datetime import datetime, timedelta, timezone
import random

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
MODEL_TIMEOUT = 300
ANNA_ROLE_IDS = [1359662416165732464]

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)

channel_state = {}
MOOD_DURATION = timedelta(minutes=5)
FERAL_DURATION = timedelta(minutes=5)

CONTEXT_FILE = "thread_context.json"
thread_context = {}

def load_context():
    global thread_context
    try:
        with open(CONTEXT_FILE, "r") as f:
            thread_context = json.load(f)
            print("[bot] Loaded thread context from disk.")
    except (FileNotFoundError, json.JSONDecodeError):
        print("[bot] No saved context found. Starting fresh.")
        thread_context = {}

def save_context():
    with open(CONTEXT_FILE, "w") as f:
        json.dump(thread_context, f)
        print("[bot] Saved thread context to disk.")

def clear_context():
    global thread_context
    thread_context = {}
    try:
        os.remove(CONTEXT_FILE)
        print("[bot] Context file deleted successfully.")
    except FileNotFoundError:
        print("[bot] No context file to delete.")

atexit.register(save_context)
load_context()

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.lower().strip() in ["anna, delete yourself", "anna, reset context", "anna, forget everything"]:
        clear_context()
        await message.reply("i've deleted myself. i got no chance to win.")
        return
    thread_id = str(message.channel.id)

    if message.reference and message.reference.resolved and message.reference.resolved.author == client.user:
        prompt = message.content.replace(f"<@{client.user.id}>", "").replace(f"<@!{client.user.id}>", "")
        for role_id in ANNA_ROLE_IDS:
            prompt = prompt.replace(f"<@&{role_id}>", "")
        prompt = prompt.strip()
    elif (
        f"<@{client.user.id}>" in message.content
        or f"<@!{client.user.id}>" in message.content
        or any(f"<@&{role_id}>" in message.content for role_id in ANNA_ROLE_IDS)
    ):
        prompt = message.content.replace(f"<@{client.user.id}>", "").replace(f"<@!{client.user.id}>", "")
        for role_id in ANNA_ROLE_IDS:
            prompt = prompt.replace(f"<@&{role_id}>", "")
        prompt = prompt.strip()

        if not prompt:
            await message.reply("you rang, nerd?")
            return
    else:
        if any(trigger in message.content.lower() for trigger in [" anna ", " anna,", " anna.", " anna!", " anna;", " anna?"]):
            try:
                await message.add_reaction("👀")
            except Exception as e:
                print(f"[bot] Failed to react: {e}")
        return

#    if not is_model_online():
#        await message.reply("brain's offline. running in dipshit mode.")
#        return
    if thread_id not in thread_context:
        thread_context[thread_id] = []

    thread_context[thread_id].append({"role": "user", "content": prompt})
    messages = thread_context[thread_id]

    response = query_llm(messages)

    thread_context[thread_id].append({"role": "assistant", "content": response})
    save_context()

    MAX_CONTEXT_MESSAGES = 12
    if len(thread_context[thread_id]) > MAX_CONTEXT_MESSAGES:
        thread_context[thread_id] = thread_context[thread_id][-MAX_CONTEXT_MESSAGES:]

    if response:
        try:
            await message.reply(response)
        except Exception as e:
            print(f"[bot] Failed to send reply: {e}")
    else:
        await message.reply("brain exploded mid-thought, try again later.")

client.run(DISCORD_TOKEN)
