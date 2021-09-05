#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import os
import random
import subprocess
from asyncio.events import AbstractEventLoop

import discord
import youtube_dl
from chopin import Chopin, Composition
from discord.ext import commands, tasks
from discord.ext.commands import Bot, Context

chopin:Chopin = Chopin(force=False, output=False, semaphore=16)

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
    "source_address": "0.0.0.0"
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class Listener(commands.Cog):
    def __init__(self, bot:Bot) -> None:
        super().__init__()
        self.bot:Bot = bot

    @commands.Cog.listener(name="on_ready")
    async def operation_at_startup(self) -> None:
        print(f"Logged in as {self.bot.user.name} ({self.bot.user.id})")
        return

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, data:dict, compo:Composition=None):
        super().__init__(original=source, volume=1.0)
        self.compo = compo if compo is not None else chopin.random_get()
        self.data:dict = data

    @classmethod
    async def async_prepare_compo(cls, loop:AbstractEventLoop=None):
        compo:Composition = chopin.random_get()
        url:str = compo.links[0].url

        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
        path = data["url"]
        return cls(discord.FFmpegPCMAudio(source=path, **ffmpeg_options), data, compo)

class DiscordChopin(commands.Cog):
    def __init__(self, bot:Bot) -> None:
        super().__init__()
        self.bot:Bot = bot

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

        self.stream.start(ctx=ctx)
        return

    @tasks.loop(seconds=5.0)
    async def stream(self, ctx:Context) -> None:
        if ctx.voice_client is None:
            return self.stream.cancel()
        elif not ctx.voice_client.is_playing():
            await self._stream(ctx)
        return

    async def _stream(self, ctx:Context) -> None:
        async with ctx.typing():
            player = await YTDLSource.async_prepare_compo(loop=self.bot.loop)
            ctx.voice_client.play(player, after=lambda e: print(f"Player error: {e}") if e else None)
            await asyncio.sleep(2.0)

        await self.send_playing(ctx, player.compo)
        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=str(player.compo)))
        return

    async def send_playing(self, ctx:Context, compo:Composition) -> None:
        embed = discord.Embed(title=str(compo), color=random.randint(0,255**3))
        embed.set_author(name=','.join(compo.links[0].artists), url=compo.links[0].url)
        await ctx.send(embed=embed)
        return

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
