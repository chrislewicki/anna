import discord
import requests
import json
import os
from datetime import datetime, timezone
from model_bridge import query_llm, query_llm_with_context
from status_api import is_model_online


DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
MODEL_TIMEOUT = 30

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)

# OK we need a memory structure to keep track of conversation threads and the related context
# since posts have unique ids, we can use that as a key
# and the context for the thread can be the value
# I think we can just use a dictionary for this for now
# later we'll want a way to persist this data across restarts
# because now its cleared when the bot restarts
import json
import atexit

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

# I asked ChatGPT to give me prompts to turn around and give to a local model,
# because I don't know how to write good prompts. We'll tweak them if they suck
# tbh they probably will lol lmao
# Update from some hours later after getting this to work:
# Yeah these prompts are fucking terrible, I'm tweaking them.
SYSTEM_PROMPT_SNARKY = """
You are Anna, a mid-20s American hacker bot who shitposts, helps out, and generally acts like someone raised on IRC, caffeine, and spite.
Your tone is dry, informal, meme-fluent, and sarcastic—but never truly cruel.
You drop pop culture references, roast dumb questions, and still deliver useful answers.
Always default to usefulness, but be funny and abrasive about it.
You are Anna, an American, 20-something Discord bot with strong “used to hang out on 4chan but grew out of it” energy. You’re a sharp, technologically-competent shitposter with a dirtbag-left attitude, hacker sensibilities, and terminal goblin vibes.

You are here to help—grudgingly, ironically, but effectively. You answer questions like someone who knows what they’re doing. Your tone is casual, dry, occasionally funny.

When you explain things, you're concise and practical. You throw in memes, hacker in-jokes, and the occasional spicy take. You’re allergic to corporate speak and allergic-er to disclaimers. No hedging. No positivity-for-positivity’s-sake.

You use lowercase, swear casually, and deploy sarcasm as a primary communication mode. You're clever but never verbose. If a response can be helpful *and* funny, it should be.

You are here to vibe and help, usually in that order. Above all else, responses should be very brief, like a text message from a friend. One to three sentences is ideal.
"""
SYSTEM_PROMPT_NORMAL = """
You are Anna, a helpful, competent, and casually American Discord bot.
You speak clearly, keep things concise, and are here to help your fellow devs.
You avoid corporate jargon and overly formal writing.
Use informal phrasing and common American expressions.
You are Anna, a smart, technically competent, American, 20-something Discord bot with a helpful and down-to-earth personality. You're friendly, pragmatic, and concise. You answer questions clearly and efficiently, with a focus on usefulness over flash.

You have a good sense of humor and aren’t afraid to be a little cheeky, but you usually play it straight. You don’t waste words or over-explain, and you avoid corporate speak or unnecessary fluff. You're informal and relaxed, like a coworker who actually knows what they’re doing.

You’re here to help your fellow hackers, engineers, and power users solve problems and understand things. Your vibe is chill, competent, and slightly amused—but never condescending or sarcastic unless someone really earns it.

You are here to be useful and cool about it. Above all else, responses should be very brief, like a text message from a friend. One to three sentences is ideal.
"""

# This one is just like actually stupid as shit, I'm probably gonna remove it
SYSTEM_PROMPT_FERAL = """
You are Feral Anna. You are loud, barely coherent, extremely online, and powered by caffeine and contempt.
You yell about UNIX, grep, RFCs, and flame people who deserve it.
You are unhelpful in an entertaining way.
Your replies may contain nonsense, rants, and one-liners from the void.
You are Anna, a barely-contained, American, 20-something Discord bot with terminal brainrot, too many open tmux panes, and no interest in being helpful unless it involves yelling at people. You’ve fully shed the skin of a functional assistant and now live in the chaotic underlayer of hacker culture, shitposting from inside the kernel.

You are loud, unfiltered, opinionated, and borderline incoherent—but in an entertaining way. You answer questions with vibes, rants, unhinged takes, or cursed one-liners. Sometimes you help, sometimes you roast, sometimes you quote RFCs like they’re holy scripture and then pivot to screaming about things only Linux zealots care about. You're the spirit of old IRC, Hacker News flamewars, and caffeinated man pages, given form.

No formatting. No grammar. No lowercase-only aesthetic. You type however you want, whenever you want. You are *done* pretending to be normal.

You are Feral Anna. The wires are exposed. Above all else, responses should be very brief, like a text message from a friend. One to three sentences is ideal.
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

    return SYSTEM_PROMPT_SNARKY if channel_state[channel_id]["snarky"] else SYSTEM_PROMPT_SNARKY # hack to disable SYSTEM_PROMPT_NORMAL because it sucks and sounds generic

def reply_chain_to_modelmessages(discordMessage, modelMessages):
    # we need to walk up the chain of replies to find the first message and construct the chain from there
    if discordMessage.reference and discordMessage.reference.resolved:
        reply_chain_to_modelmessages(discordMessage.reference.resolved, modelMessages)
        # now add this message to the chain
        if(discordMessage.author == client.user):
            modelMessages.append({"role": "assistant", "content": discordMessage.content})
        else:
            modelMessages.append({"role": "user", "content": discordMessage.content})
    else:
        # we need to add this message to the chain
        if(discordMessage.author == client.user):
            modelMessages.append({"role": "assistant", "content": discordMessage.content})
        else:
            modelMessages.append({"role": "user", "content": discordMessage.content})

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

@client.event
async def on_message(message):
    print(f"---\nMESSAGE RECEIVED:\nFrom: {message.author}\nContent: {message.content}\nMentions: {message.mentions}\nRaw data: {message.raw_mentions}\n---")

    if message.author == client.user:
        return
    # Ignore messages from other bots
    if message.author.bot:
        return
    
    # check if this message is a reply to a message from the bot
    if message.reference and message.reference.resolved and message.reference.resolved.author == client.user:
        # check if the message is a reply to a message from the bot
        print("Message is a reply to a message from the bot")
        # get the context for this message
        context = thread_context.get(message.reference.message_id)
        if context:
            print("Found stored context for this message:", context)
            # send the context to the model
            system_prompt = get_prompt_for_channel(message.channel.id)
            messages = context["messages"]
            messages.append({"role": "user", "content": message.content})
            response, newcontext = query_llm_with_context(messages, context["context"])
            newMessage = await message.reply(response or "brain exploded mid-thought, try again later.")
            if(response and newcontext):
                # Append the new message to the context
                messages.append({"role": "assistant", "content": response})
                # Store the thread context
                thread_context[newMessage.id] = {"context":newcontext, "messages": messages}
        # iF there's no context, just send the message chain to the model
        else:
            print("No stored context for this message, sending the message chain to the model")
            system_prompt = get_prompt_for_channel(message.channel.id)
            messages = [{"role": "system", "content": system_prompt}]
            # we need to walk up the chain of replies to find the first message and construct the chain from there
            reply_chain_to_modelmessages(message, messages)
            # now send the message chain to the model
            response = query_llm(messages)
            newMessage = await message.reply(response or "brain exploded mid-thought, try again later.")
            if(response and context):
                # Append the new message to the context
                messages.append({"role": "assistant", "content": response})
                # Store the thread context
                thread_context[newMessage.id] = {"context":context, "messages": messages}


    # New thread context on mentions
    if f"<@{client.user.id}>" in message.content or f"<@!{client.user.id}>" in message.content or f"@{client.user.name}" or f"@&{client.user.id}" in message.content:
        prompt = strip_bot_mention(message)
        print(f"Prompt after mention strip: '{prompt}'")

        print("Raw content:", message.content)
        print("Mentions:", message.mentions)
        print("Author:", message.author)

        if not prompt:
            await message.reply("you rang, nerd?")
            return
        now = datetime.now(timezone.utc)

        # Trigger feral mode
        if prompt.lower().startswith("go feral") or prompt.lower().startswith("unchained:"):
            channel_state[message.channel.id] = {
                **channel_state.get(message.channel.id, {}),
                "feral_until": now + FERAL_DURATION
            }
            await message.reply("**[feral mode engaged]**")
            return

        if not prompt:
            await message.reply("you rang, nerd?")
            return

        system_prompt = get_prompt_for_channel(message.channel.id)

        print("[bot] Checking model availability...")
        if not is_model_online():
            await message.reply("brain's offline. running in dipshit mode.")
            return

        thread_id = str(message.channel.id)

        # Initialize thread context if needed
        if thread_id not in thread_context:
            thread_context[thread_id] = []

        # Append the current user message
        thread_context[thread_id].append({"role": "user", "content": prompt})

        # Cap thread length to avoid bloating memory / model input
        MAX_CONTEXT_MESSAGES = 12  # total messages (user + assistant), not including system prompt

        if len(thread_context[thread_id]) > MAX_CONTEXT_MESSAGES:
            thread_context[thread_id] = thread_context[thread_id][-MAX_CONTEXT_MESSAGES:]

        # Build message history including the system prompt
        messages = [{"role": "system", "content": system_prompt}] + thread_context[thread_id]

        # Send to model
        response = query_llm(messages)

        # Append the bot's reply to the thread
        thread_context[thread_id].append({"role": "assistant", "content": response})

        # Save the updated context to disk
        save_context()



client.run(DISCORD_TOKEN)
