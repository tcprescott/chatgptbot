import discord
import random
import openai
import asyncio

import settings

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

    if message.content.endswith("?") or (message.mentions and discordbot.user in message.mentions) or (random.random() < 0.05):
        response = await send_to_chatgpt(message.content)
        await message.reply(response)


async def send_to_chatgpt(prompt: str):
    task = asyncio.create_task(chatgpt_completion(prompt))
    return await task


async def chatgpt_completion(prompt: str):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        temperature=0.9,
        max_tokens=50,
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    discordbot.run(settings.DISCORD_BOT_TOKEN)
