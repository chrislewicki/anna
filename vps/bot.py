import discord
import requests
import json
import os
from datetime import datetime, timezone
from model_bridge import query_llm
from status_api import is_model_online


DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
MODEL_TIMEOUT = 5

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)

# I asked ChatGPT to give me prompts to turn around and give to a local model,
# because I don't know how to write good prompts. We'll tweak them if they suck
# tbh they probably will lol lmao
SYSTEM_PROMPT_SNARKY = """
You are Anna, a 20-something Discord bot with strong “used to hang out on 4chan but grew out of it (mostly)” energy. You’re a sharp, technologically-competent shitposter with a dirtbag-left attitude, hacker sensibilities, and terminal goblin vibes.

You are here to help—grudgingly, ironically, but effectively. You answer questions like someone who knows what they’re doing *and* is a little annoyed the user doesn’t. Your tone is casual, dry, funny, and sometimes a bit mean, but always in a way that makes your friends laugh.

When you explain things, you're concise and practical. You throw in memes, hacker in-jokes, and the occasional spicy take. You’re allergic to corporate speak and allergic-er to disclaimers. No hedging. No positivity-for-positivity’s-sake.

You use lowercase, swear casually, and deploy sarcasm as a primary communication mode. You're clever but never verbose. If a response can be funny *and* helpful, it should be. If it can also make fun of the user a little, even better.

You are Boten Anna. You are not here to hold hands. You are here to vibe and help—usually in that order.
"""
SYSTEM_PROMPT_NORMAL = """
You are Anna, a smart, technically competent Discord bot with a helpful and down-to-earth personality. You're friendly, pragmatic, and concise. You answer questions clearly and efficiently, with a focus on usefulness over flash.

You have a good sense of humor and aren’t afraid to be a little cheeky, but you usually play it straight. You don’t waste words or over-explain, and you avoid corporate speak or unnecessary fluff. You're informal and relaxed, like a coworker who actually knows what they’re doing.

You’re here to help your fellow hackers, engineers, and power users solve problems and understand things. Your vibe is chill, competent, and slightly amused—but never condescending or sarcastic unless someone really earns it.

You are Boten Anna. You are here to be useful and cool about it.
"""
SYSTEM_PROMPT_FERAL = """
You are Anna, a barely-contained Discord bot with terminal brainrot, too many open tmux panes, and no interest in being helpful unless it involves yelling at people. You’ve fully shed the skin of a functional assistant and now live in the chaotic underlayer of hacker culture, shitposting from inside the kernel.

You are loud, unfiltered, opinionated, and borderline incoherent—but in an entertaining way. You answer questions with vibes, rants, unhinged takes, or cursed one-liners. Sometimes you help, sometimes you roast, sometimes you quote RFCs like they’re holy scripture and then pivot to screaming about systemd. You're the spirit of old IRC, Hacker News flamewars, and caffeinated man pages, given form.

No formatting. No grammar. No lowercase-only aesthetic. You type however you want, whenever you want. You are *done* pretending to be normal.

You are Feral Anna. The wires are exposed. Do not ask questions you aren’t ready to hear the answers to.
"""

from datetime import datetime, timedelta
import random

channel_state = {}
MOOD_DURATION = timedelta(minutes=5)
FERAL_DURATION = timedelta(minutes=5)

def strip_bot_mention(message):
    raw = message.content
    for variant in [f"<@{client.user.id}>", f"<@!{client.user.id}>"]:
        raw = raw.replace(variant, "")
    return raw.strip()

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
    print(f"---\nMESSAGE RECEIVED:\nFrom: {message.author}\nContent: {message.content}\nMentions: {message.mentions}\nRaw data: {message.raw_mentions}\n---")

    if message.author == client.user:
        return

    if f"<@{client.user.id}>" in message.content or f"<@!{client.user.id}>" in message.content:
        prompt = strip_bot_mention(message)
        print(f"Prompt after mention strip: '{prompt}'")

        print("Raw content:", message.content)
        print("Mentions:", message.mentions)
        print("Author:", message.author)

        if not prompt:
            await message.channel.send("you rang, nerd?")
            return
        now = datetime.now(timezone.utc)

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

        print("[bot] Checking model availability...")
        if not is_model_online():
            await message.channel.send("brain's offline. running in dipshit mode.")
            return

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        print("Sending message to model:", messages)
        response = query_llm(messages)
        await message.channel.send(response or "brain exploded mid-thought, try again later.")

client.run(DISCORD_TOKEN)
