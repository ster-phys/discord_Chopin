import asyncio
import random

from os import getenv
TOKEN = getenv("DISCORD_TOKEN")

import discord
from discord.ext import commands

import chopin

# prepare chopin
CHOPIN = chopin.chopin(parallel=True, semaphore=20, output=False)

ffmpeg_options = {
    'options': '-vn'
}

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, compo=None, volume=1.0):
        super().__init__(source, volume)
        self.compo = compo

    @classmethod
    def prepare_compo(cls):
        compo = CHOPIN.get()
        filename = compo.links[0].download()

        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), compo=compo)

    @classmethod
    async def async_prepare_compo(cls, loop=None):
        compo = CHOPIN.get()

        loop = loop or asyncio.get_event_loop()
        filename = await loop.run_in_executor(None, lambda: compo.links[0].download())

        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), compo=compo)

class Discord_Chopin(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.player_del = None
        self.player_now = YTDLSource.prepare_compo()
        self.player_next = YTDLSource.prepare_compo()

    @commands.command()
    async def chopin(self, ctx) -> None:
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
                await self.play(ctx)
            else:
                await asyncio.sleep(5)

    async def play(self, ctx) -> None:
        async with ctx.typing():
            self.player_del = self.player_now
            self.player_now = self.player_next
            ctx.voice_client.play(self.player_now, after=lambda e: print(f"Player error: {e}") if e else None)
            await asyncio.sleep(0.5)

        await self.now_playing(ctx, self.player_now.compo)
        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=f"?chopin\\{self.player_now.compo}"))
        self.player_del.compo.links[0].delete()
        self.player_next = await YTDLSource.async_prepare_compo(loop=self.bot.loop)

    async def now_playing(self, ctx, compo):
        embed = discord.Embed(title=f"{compo}", color=random.randint(0,255**3))
        embed.set_author(name=','.join(compo.links[0].artists), url=compo.links[0].url)
        return await ctx.send(embed=embed)

    def __del__(self) -> None:
        self.player_now.compo.links[0].delete()
        self.player_next.compo.links[0].delete()

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
