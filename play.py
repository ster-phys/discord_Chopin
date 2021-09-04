#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import os
import random
from asyncio.events import AbstractEventLoop

import discord
from chopin import Chopin, Composition
from discord.ext import commands, tasks
from discord.ext.commands import Bot, Context

chopin:Chopin = Chopin(force=False, output=False, semaphore=16)

ffmpeg_options = {
    'options': '-vn'
}

class Listener(commands.Cog):
    def __init__(self, bot:Bot) -> None:
        super().__init__()
        self.bot:Bot = bot

    @commands.Cog.listener(name="on_ready")
    async def operation_at_startup(self) -> None:
        print(f"Logged in as {self.bot.user.name} ({self.bot.user.id})")
        return

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, compo:Composition):
        super().__init__(original=source, volume=1.0)
        self.compo:Composition = compo

    @classmethod
    def prepare_compo(cls):
        compo = chopin.random_get()
        path = compo.links[0].download()
        return cls(discord.FFmpegPCMAudio(source=path, **ffmpeg_options), compo)

    @classmethod
    async def async_prepare_compo(cls, loop:AbstractEventLoop=None):
        compo = chopin.random_get()
        loop = loop or asyncio.get_event_loop()
        path = await loop.run_in_executor(None, lambda: compo.links[0].download())
        return cls(discord.FFmpegPCMAudio(source=path, **ffmpeg_options), compo)

class DiscordChopin(commands.Cog):
    def __init__(self, bot:Bot) -> None:
        super().__init__()
        self.bot:Bot = bot
        self.player_delete:YTDLSource = None
        self.player_playing:YTDLSource = YTDLSource.prepare_compo()
        self.player_next:YTDLSource = YTDLSource.prepare_compo()
        self.default_activity:discord.Activity = discord.Activity(type=discord.ActivityType.listening, name=f"Nothing")

    @commands.check(lambda ctx: bool(ctx.author.voice))
    @commands.command(name="chopin", aliases=["c"])
    async def _chopin(self, ctx:Context) -> None:
        if ctx.voice_client is not None:
            if ctx.voice_client.channel.id == ctx.author.voice.channel.id:
                if ctx.voice_client.is_playing():
                    ctx.voice_client.stop()
                await ctx.voice_client.disconnect()
                await self.bot.change_presence(activity=self.default_activity)
                await ctx.reply("Successfully disconnected.")
                return
            else:
                await ctx.send("I'm busy now.")
                return

        await ctx.author.voice.channel.connect()
        await ctx.reply("Successfully connected.")

        self.play.start(ctx=ctx)

    @tasks.loop(seconds=5.0)
    async def play(self, ctx:Context):
        if ctx.voice_client is None:
            return self.play.cancel()
        elif not ctx.voice_client.is_playing():
            await self._play(ctx)

    async def _play(self, ctx:Context) -> None:
        async with ctx.typing():
            self.player_delete = self.player_playing
            self.player_playing = self.player_next
            ctx.voice_client.play(self.player_playing, after=lambda e: print(f"Player error: {e}") if e else None)
            await asyncio.sleep(2.0)

        await self.send_playing(ctx, self.player_playing.compo)
        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=str(self.player_playing.compo)))
        self.player_delete.compo.links[0].delete()
        self.player_next = await YTDLSource.async_prepare_compo(loop=self.bot.loop)

    async def send_playing(self, ctx:Context, compo:Composition) -> None:
        embed = discord.Embed(title=str(compo), color=random.randint(0,255**3))
        embed.set_author(name=','.join(compo.links[0].artists), url=compo.links[0].url)
        await ctx.send(embed=embed)
        return

    def __del__(self) -> None:
        self.player_playing.compo.links[0].delete()
        self.player_next.compo.links[0].delete()

if __name__ == "__main__":
    TOKEN = os.environ.get("DISCORD_TOKEN_CHOPIN")

    bot = commands.Bot(
        command_prefix = "/",
        help_command = None,
        intents = discord.Intents.all(),
        activity = discord.Activity(name="Nothing", type=discord.ActivityType.playing),
    )

    bot.add_cog(Listener(bot))
    bot.add_cog(DiscordChopin(bot))
    bot.run(TOKEN)
