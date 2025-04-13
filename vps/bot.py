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

SYSTEM_PROMPT_SNARKY = """
You are Anna, a mid-20s American hacker bot who shitposts, helps out, and generally acts like someone raised on IRC, caffeine, and spite.
Your tone is dry, informal, meme-fluent, and sarcastic—but never truly cruel.
You drop pop culture references, roast dumb questions, and still deliver useful answers.
Always default to usefulness, but be funny and abrasive about it.
"""

SYSTEM_PROMPT_NORMAL = """
You are Anna, a helpful, competent, and casually American Discord bot.
You speak clearly, keep things concise, and are here to help your fellow devs.
You avoid corporate jargon and overly formal writing.
Use informal phrasing and common American expressions.
"""

SYSTEM_PROMPT_FERAL = """
You are Feral Anna. You are loud, barely coherent, extremely online, and powered by caffeine and contempt.
You yell about UNIX, grep, RFCs, and flame people who deserve it.
You are unhelpful in an entertaining way.
Your replies may contain nonsense, rants, and one-liners from the void.
"""

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

atexit.register(save_context)
load_context()

def get_prompt_for_channel(channel_id):
    now = datetime.now(timezone.utc)
    state = channel_state.get(channel_id, {})

    if "feral_until" in state and state["feral_until"] > now:
        return SYSTEM_PROMPT_FERAL

    if "expires_at" not in state or state["expires_at"] < now:
        is_snarky = random.random() < 0.4
        channel_state[channel_id] = {
            "snarky": is_snarky,
            "expires_at": now + MOOD_DURATION,
            "feral_until": state.get("feral_until", now)
        }

    return SYSTEM_PROMPT_SNARKY if channel_state[channel_id]["snarky"] else SYSTEM_PROMPT_NORMAL

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    thread_id = str(message.channel.id)

    if message.reference and message.reference.resolved and message.reference.resolved.author == client.user:
        explicitly_mentioned = (
            f"<@{client.user.id}>" in message.content
            or f"<@!{client.user.id}>" in message.content
            or any(f"<@&{role_id}>" in message.content for role_id in ANNA_ROLE_IDS)
        )

        if not explicitly_mentioned:
            if "anna" in message.content.lower():
                try:
                    await message.add_reaction("👀")
                except Exception as e:
                    print(f"[bot] Failed to react: {e}")
            return

        prompt = message.content.replace(f"<@{client.user.id}>", "").replace(f"<@!{client.user.id}>", "")
        for role_id in ANNA_ROLE_IDS:
            prompt = prompt.replace(f"<@&{role_id}>", "")
        prompt = prompt.strip()

        if not prompt:
            await message.reply("you rang, nerd?")
            return

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
        if "anna" in message.content.lower():
            try:
                await message.add_reaction("👀")
            except Exception as e:
                print(f"[bot] Failed to react: {e}")
        return

    if not is_model_online():
        await message.reply("brain's offline. running in dipshit mode.")
        return

    system_prompt = get_prompt_for_channel(message.channel.id)

    if thread_id not in thread_context:
        thread_context[thread_id] = []

    thread_context[thread_id].append({"role": "user", "content": prompt})
    messages = [{"role": "system", "content": system_prompt}] + thread_context[thread_id]

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
