import asyncio
import random
from typing import List

import discord
import openai

import settings

semaphore = asyncio.Semaphore(value=1)

discordbot = discord.Client(
    intents=discord.Intents.all(),
    allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=False),
)

openai.api_key = settings.OPENAI_API_KEY


@discordbot.event
async def on_ready():
    print("Bot is ready")


@discordbot.event
async def on_message(message: discord.Message):
    if message.author == discordbot.user:
        return

    if not message.channel.id == settings.CHANNEL_ID:
        return

    if should_respond(message):
        try:
            # message_history = message.channel.history(limit=5)
            chatgpt_message_history = [
                {
                    "role": "system",
                    "content": settings.initial_context,
                }
            ]
            chatgpt_message_history.extend(await get_reply_history(message))
            response = await asyncio.wait_for(send_to_chatgpt(chatgpt_message_history), timeout=10)
            await message.reply(response)
        except asyncio.TimeoutError:
            print("busy")


async def get_reply_history(message: discord.Message):
    messages = []
    while len(messages) < 5:
        messages.append(
            {
                "role": "assistant" if message.author == discordbot.user else "user",
                "content": message.content,
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
        return False

    if message.author.bot:
        return False

    if not message.channel.id == settings.CHANNEL_ID:
        return False

    if message.content.endswith("?"):
        return True

    if (message.mentions and discordbot.user in message.mentions):
        return True

    if (random.random() < 0.05):
        return True

    return False


async def send_to_chatgpt(history: List[dict]):
    async with semaphore:
        task = asyncio.create_task(chatgpt_completion(history))
        return await task


async def chatgpt_completion(history: List[dict]):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=history,
        temperature=1,
        max_tokens=100,
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    discordbot.run(settings.DISCORD_BOT_TOKEN)
