import asyncio
import random
from typing import List
import re

import discord
import openai
import datetime

import settings

semaphore = asyncio.Semaphore(value=1)

discordbot = discord.Client(
    intents=discord.Intents.all(),
    allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=False),
)

REGEX_USERS_AND_ROLES = re.compile(r'<@!?\d+>|<@&\d+>')

openai.api_key = settings.OPENAI_API_KEY

rate_limits = {}


@discordbot.event
async def on_ready():
    print("Bot is ready")


@discordbot.event
async def on_message(message: discord.Message):
    if message.author == discordbot.user:
        return

    if should_respond(message):
        try:
            async with message.channel.typing():
                if message.reference:
                    referenced_message = await message.channel.fetch_message(message.reference.message_id)
                    chatgpt_message_history = await get_reply_history(referenced_message)
                elif message.mentions and discordbot.user in message.mentions:
                    chatgpt_message_history = []
                else:
                    message_history = message.channel.history(limit=8)
                    chatgpt_message_history = [
                        {
                            "role": "assistant" if m.author == discordbot.user else "user",
                            "content": re.sub(REGEX_USERS_AND_ROLES, '', m.content[:400]),
                        }
                        async for m in message_history if m != message  # and m.author != discordbot.user
                    ]
                    chatgpt_message_history.reverse()

                system_prompt = f"""
                {context_fusion_history(chatgpt_message_history)}
                ---
                {settings.initial_context}
                When answering the user, take the message history into account.
                """

                prompt = [
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": re.sub(REGEX_USERS_AND_ROLES, '', message.content[:200]),
                    }
                ]
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, chatgpt_completion, prompt)
                await message.reply(response, mention_author=False)
                # await message.reply("debug response")
        except asyncio.TimeoutError:
            await message.add_reaction("⌚")


async def get_reply_history(message: discord.Message):
    messages = []
    while len(messages) < 5:
        messages.append(
            {
                "role": "assistant" if message.author == discordbot.user else "user",
                "content": re.sub(REGEX_USERS_AND_ROLES, '', message.content[:400]),
            }
        )
        if message.reference:
            message = await message.channel.fetch_message(message.reference.message_id)
        else:
            break

    messages.reverse()
    return messages


def should_respond(message: discord.Message):
    """
    Returns True if the bot should respond to the message.
    """
    if message.author == discordbot.user:
        return 0

    if message.author.bot:
        return 0

    if not message.channel.id in settings.CHANNEL_ID:
        return 0

    if message.content.endswith("?"):
        return 1

    if (message.mentions and discordbot.user in message.mentions):
        return 1

    if (random.random() < 0.05):
        return 2

    return 0


def is_rate_limited(member: discord.Member):
    if member.id in rate_limits:
        if datetime.datetime.now() < rate_limits[member.id] + datetime.timedelta(seconds=30):
            return True

    rate_limits[member.id] = datetime.datetime.now()
    return False


def context_fusion_history(history: List[dict]):
    result = "Message history:\n" + "\n".join(
        f"{m['role']}: {m['content'][:400]}" for m in history
    )
    return result


def chatgpt_completion(history: List[dict]):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=history,
        temperature=0.8,
        max_tokens=256,
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    discordbot.run(settings.DISCORD_BOT_TOKEN)
