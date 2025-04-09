import discord
import requests
import json
from model_bridge import query_llm
from status_api import is_model_online

DISCORD_TOKEN = "your_discord_token_here"
MODEL_TIMEOUT = 5

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)

SYSTEM_PROMPT_SNARKY = "You are Anna, a 20-something Discord bot with strong dirtbag energy. You're helpful, but mostly sarcastic..."
SYSTEM_PROMPT_NORMAL = "You are Anna, a smart, helpful Discord bot. You're friendly and give useful, concise answers."
SYSTEM_PROMPT_FERAL = "You are Feral Anna. You are barely a bot anymore. Chaos is your domain."

from datetime import datetime, timedelta
import random

channel_state = {}
MOOD_DURATION = timedelta(minutes=5)
FERAL_DURATION = timedelta(minutes=5)

def get_prompt_for_channel(channel_id):
    now = datetime.utcnow()
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

    if client.user in message.mentions:
        prompt = message.clean_content.replace(f"@{client.user.name}", "").strip()
        now = datetime.utcnow()

        # Trigger feral mode
        if prompt.lower().startswith("go feral") or prompt.lower().startswith("unchained:"):
            channel_state[message.channel.id] = {
                **channel_state.get(message.channel.id, {}),
                "feral_until": now + FERAL_DURATION
            }
            await message.channel.send("**[feral mode engaged]**")
            return

        if not prompt:
            await message.channel.send("you rang, nerd?")
            return

        system_prompt = get_prompt_for_channel(message.channel.id)

        if not is_model_online():
            await message.channel.send("brain's offline. running in dipshit mode.")
            return

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        response = query_llm(messages)
        await message.channel.send(response or "the brain exploded mid-thought, try again later.")

client.run(DISCORD_TOKEN)
