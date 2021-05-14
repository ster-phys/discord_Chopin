import asyncio
import random

from os import getenv
TOKEN = getenv("DISCORD_TOKEN")

import discord
from discord.ext import commands

import chopin
import youtube_dl

# prepare chopin
CHOPIN = chopin.chopin(parallel=True, semaphore=20, output=False)

# prepare youtube_dl
ytdl_format_options = {
    "format": "bestaudio/best",
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0" # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, compo=None, volume=1.0):
        super().__init__(source, volume)

        self.data = data
        self.compo = compo if compo else CHOPIN.get()

    @classmethod
    async def prepare_compo(cls, loop=None):
        compo = CHOPIN.get()
        url = compo.links[0].url

        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))

        filename = data["url"]

        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data, compo=compo)

class Discord_Chopin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def chopin(self, ctx):
        if not ctx.author.voice:
            await ctx.send("You are not connected to a voice channel.")
            raise commands.CommandError("Author not connected to a voice channel.")
        else: # ctx.author.voice
            if ctx.voice_client is not None:
                bot_channel_id = ctx.voice_client.channel.id
                ctx_channel_id = ctx.author.voice.channel.id
                if bot_channel_id == ctx_channel_id:
                    if ctx.voice_client.is_playing():
                        ctx.voice_client.stop()
                    await ctx.voice_client.disconnect()
                    await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=f"?chopin\\Nothing"))
                    return await ctx.send("Successfully disconnected.")
                else: # bot_channel_id != ctx_channel_id
                    return await ctx.send("I'm busy now.")

        # ctx.voice_client is None
        await ctx.author.voice.channel.connect()
        await ctx.send("Successfully connected.")

        while True:
            if ctx.voice_client is None:
                return
            elif not ctx.voice_client.is_playing():
                await self.stream(ctx)
            else:
                await asyncio.sleep(5)

    async def stream(self, ctx):
        async with ctx.typing():
            player = await YTDLSource.prepare_compo(loop=self.bot.loop)
            ctx.voice_client.play(player, after=lambda e: print(f"Player error: {e}") if e else None)

        await self.now_playing(ctx, player.compo)
        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=f"?chopin\\{player.compo}"))


    async def now_playing(self, ctx, compo):
        embed = discord.Embed(title=f"{compo}", color=random.randint(0,255**3))
        embed.set_author(name=','.join(compo.links[0].artists), url=compo.links[0].url)
        return await ctx.send(embed=embed)

bot = commands.Bot(command_prefix=("?"))

# Operation at startup
@bot.event
async def on_ready():
    print("Logged in as {} ({})".format(bot.user.name,bot.user.id))
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=f"?chopin\\Nothing"))

# Ignore commands from bots
@bot.event
async def from_bot(ctx):
    if ctx.author.bot:
        return

bot.add_cog(Discord_Chopin(bot))
bot.run(TOKEN)
