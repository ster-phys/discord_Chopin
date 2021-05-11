#!/usr/bin/env python
# -*- coding: utf-8 -*-

import discord
from discord import channel
from discord.ext import commands

import config

# Get TOKEN
TOKEN = config.DISCORD_TOKEN

# Bot setting
commandPrefix = "?"
bot = commands.Bot(command_prefix=commandPrefix)
bot.remove_command("help")

# Operation at startup
@bot.event
async def on_ready():
    print("Logged in as {} ({})".format(bot.user.name,bot.user.id))

# Ignore commands from bots
@bot.event
async def from_bot(ctx):
    if ctx.author.bot:
        return

import asyncio
import random
import chopin
CHOPIN = chopin.chopin(True, 20)

class Manage():
    def __init__(self,ctx):
        # task status
        self._remove = CHOPIN.get()
        self._now = CHOPIN.get()
        self._next = CHOPIN.get()
        # audio path
        self._path = self._now.links[0].download()
        # Need for discord
        self._ctx = ctx
        self._voiceClient = self._ctx.guild.voice_client

    async def output(self):
        if self._voiceClient:
            embed = discord.Embed(title=str(self._now), color=random.randint(0,255**3))
            url = "https://www.j-cast.com/trend/assets_c/2020/02/trend_20200214145309-thumb-645xauto-172891.jpg"
            embed.set_author(name=','.join(self._now.links[0].artists), icon_url=url)
            await self._ctx.send(embed=embed)
        return

    async def _process1(self):
        """
        Remove MP3 File
        """
        await asyncio.sleep(5)
        self._remove.links[0].delete()

    async def _process2(self):
        """
        Play @ Voice Channel
        """
        try:
            audioSource = discord.FFmpegPCMAudio(self._path)
            self._voiceClient.play(audioSource)
            await self.output()
            return True
        except:
            return False

    async def _process3(self):
        """
        Next Play
        """
        await asyncio.sleep(5)
        self._path = self._next.links[0].download()

    async def proceed(self):
        await self._process1()
        if not await self._process2():
            return
        await self._process3()

        flag = False
        while not flag:
            if self._voiceClient.is_playing():
                await asyncio.sleep(2)
            elif not self._voiceClient:
                return
            else:
                flag = True

        self._remove = self._now
        self._now = self._next
        self._next = CHOPIN.get()

        if self._voiceClient:
            await self.proceed()
        else:
            return

    def __del__(self):
        if self._voiceClient.is_playing():
            self._voiceClient.stop()
        self._voiceClient = None
        self._remove.links[0].delete()
        self._now.links[0].delete()
        self._next.links[0].delete()

@bot.command()
async def join(ctx):
    # User must be on the voice channel to use the command
    if not ctx.author.voice:
        await ctx.send("You need to connect to the voice channel.")
        return
    # already connected
    if ctx.guild.voice_client:
        await ctx.send("Already connected.")
        return
    # connect
    await ctx.author.voice.channel.connect()
    # play
    global MNG
    MNG = Manage(ctx)
    await MNG.proceed()

@bot.command()
async def leave(ctx):
    # check connection
    if not ctx.guild.voice_client:
        await ctx.send("There is no connection.")
        return

    # disconnect
    await ctx.guild.voice_client.disconnect()
    await ctx.send("Successfully disconnected.")

    global MNG
    del MNG

bot.run(TOKEN)
