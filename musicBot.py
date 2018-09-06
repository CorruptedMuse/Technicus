import asyncio
import discord
from discord.ext import commands
import authDeets
import youtube_dl
import time
import os

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio[ext=mp3]/best[ext=mp3]/bestaudio/best',
    'outtmpl': 'media-%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'max_filesize': 20000000,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'before_options': '-nostdin',
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')
        self.id = data.get('id')

    @classmethod
    async def from_url(cls, url, *, loop=None):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, ytdl.extract_info, url)

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = ytdl.prepare_filename(data)
        for file in os.listdir():
            if file == filename:
                return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)
        else:
            return None


class Music:
    def __init__(self, bot):
        self.bot = bot
        self.songs = ["None"]
        self.queue_player = self.bot.loop.create_task(self.queue_loop())
        self.voice = None
        self.voice_channel = None
        self.played_time = 0
        self.connection_player = self.bot.loop.create_task(self.connection_loop())
        self.music_off = False
        self.processing_songs = 0
        self.tbd_id = None
        self.id_list = []
        self.skip_votes = []

    def del_all_files(self):
        for file in os.listdir():
            if file.startswith("media"):
                os.remove(file)

    def title_shorten(self, title):
        if len(title) > 60:
            return "{0}...".format(title.replace("`", "'")[:57])
        else:
            return title.replace("`", "'")

    def del_song(self, song_pos):
        file_to_del = None
        if self.songs[song_pos] != "None":
            copy_exists = False
            pos = len(self.songs) - 1
            while pos > -1:
                if self.songs[pos][0].id == self.songs[song_pos][0].id and pos != song_pos:
                    copy_exists = True
                pos = pos - 1
            if not copy_exists:
                for file in os.listdir():
                    if self.songs[song_pos][0].id in file and file.startswith("media"):
                        file_to_del = file
        if len(self.songs) == 1:
            self.songs = ["None"]
        else:
            del self.songs[song_pos]
        if file_to_del is not None:
            print("removing file {0}".format(file_to_del))
            os.remove(file_to_del)

    @commands.command()
    async def summon(self, ctx):
        """Summons the bot to join your voice channel."""
        if ctx.message.channel.name != "bot-commands":
            return await ctx.send("**Error:** Music Bot commands are only available in #bot-commands")
        if self.music_off:
            return await ctx.send("**Error:** Music Bot features are currently off")

        self.played_time = time.time()
        summoned_channel = ctx.message.author.voice
        if summoned_channel is None:
            return await ctx.send("**Error:** You are not in a voice channel.")

        if ctx.voice_client is not None:
            if self.songs != ["None"]:
                return await ctx.send("**Error:** There are songs playing in the other voice channel")
            self.voice = ctx.voice_client
            self.voice_channel = ctx.message.channel
            return await ctx.voice_client.move_to(summoned_channel.channel)

        await summoned_channel.channel.connect()
        self.voice = ctx.voice_client
        self.voice_channel = ctx.message.channel
        self.processing_songs = 0
        await ctx.send("Summoned")
        # await ctx.send("**Notice:** youtube_dl is currently experiencing slowdowns when handling YouTube requests (it will still work though). Until this is fixed, consider using other audio sources, such as Bandcamp or Soundcloud")

    # @commands.command()
    # async def play(self, ctx, *, query):
    #	"""Plays a file from the local filesystem"""
    #	
    #	if ctx.voice_client is None:
    #		if ctx.author.voice.channel:
    #			await ctx.author.voice.channel.connect()
    #		else:
    #			return await ctx.send("**Error:** Not connected to a voice channel.")
    #	
    #	source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(query))
    #	
    #	self.voice = ctx.voice_client
    #	self.voice_channel = ctx.message.channel
    #	await self.songs.put([source, query, ctx.voice_client, ctx.message.channel])
    #	
    #	await ctx.send('Queued: {}'.format(query))

    @commands.command()
    async def yt(self, ctx, *, url):
        """Streams from a url (almost anything youtube_dl supports)"""
        if ctx.message.channel.name != "bot-commands":
            return await ctx.send("**Error:** Music Bot commands are only available in #bot-commands")
        if self.music_off:
            return await ctx.send("**Error:** Music Bot features are currently off")
        if ctx.voice_client is None or ctx.voice_client.channel is not ctx.message.author.voice.channel:
            return await ctx.send("**Error:** You must be connected to the voice channel.")
        if len(self.songs) + self.processing_songs >= 30:
            return await ctx.send("**Error:** There can only be a maximum of 30 items in the queue")
        if self.processing_songs >= 3:
            return await ctx.send("**Error:** Please wait until some of the other songs are finished processing")

        self.played_time = time.time()
        self.voice = ctx.voice_client
        self.voice_channel = ctx.message.channel
        async with ctx.message.channel.typing():
            self.processing_songs = self.processing_songs + 1
            try:
                player = await YTDLSource.from_url(url, loop=self.bot.loop)
            except:
                self.processing_songs = self.processing_songs - 1
                return await ctx.send("Error processing song. Invalid URL or no matching videos using that search term")
            if player is None:
                self.processing_songs = self.processing_songs - 1
                return await ctx.send("**Error:** Song file too large!")
            self.processing_songs = self.processing_songs - 1
            self.songs.append([player, player.title, ctx.voice_client, ctx.message.channel, []])

            shortened_title = self.title_shorten(player.title)
            await ctx.send('Queued: `{}`'.format(shortened_title))

    #	@commands.command()
    #	async def volume(self, ctx, volume: int):
    #		"""Changes the player's volume"""
    #		if(ctx.message.channel.name != "bot-commands"):
    #			return await ctx.send("**Error:** Music Bot commands are only available in #bot-commands")
    #		if(self.music_off):
    #			return await ctx.send("**Error:** Music Bot features are currently off")
    #
    #		if ctx.voice_client is None:
    #			return await ctx.send("**Error:** Not connected to a voice channel.")
    #		if(volume>200):
    #			return await ctx.send("**Error:** Maximum is 200%")
    #
    #		ctx.voice_client.source.volume = volume/100
    #		await ctx.send("Changed volume to {}%".format(volume))

    @commands.command()
    async def disconnect(self, ctx):
        """Stops and disconnects the bot from voice"""
        if ctx.message.channel.name != "bot-commands":
            return await ctx.send("**Error:** Music Bot commands are only available in #bot-commands")
        if self.music_off:
            return await ctx.send("**Error:** Music Bot features are currently off")
        if ctx.voice_client is None or ctx.voice_client is not self.voice:
            return await ctx.send("**Error:** You must be connected to the voice channel.")
        try:
            await ctx.voice_client.stop()
        except:
            pass
        await ctx.voice_client.disconnect()
        self.songs = ["None"]
        self.processing_songs = 0
        self.del_all_files()
        self.voice = None
        await ctx.send("Disconnected")

    @commands.command()
    async def skip(self, ctx):
        """Stops or skips current song"""
        if ctx.message.channel.name != "bot-commands":
            return await ctx.send("**Error:** Music Bot commands are only available in #bot-commands")
        if self.music_off:
            return await ctx.send("**Error:** Music Bot features are currently off")
        if ctx.voice_client is None or ctx.voice_client is not self.voice:
            return await ctx.send("**Error:** You must be connected to the voice channel.")

        is_mod = False
        for role in ctx.message.author.roles:
            if role.name == "Bot Mod":
                is_mod = True
        if is_mod:
            await ctx.send("Skipping song...")
            return await self.voice.stop()

        if ctx.author.id not in self.songs[0][4]:
            self.skip_votes.append(ctx.author.id)
        if len(ctx.message.author.voice.channel.members) - 1 > len(self.songs[0][4]) * 2:
            await ctx.send("{0} skip votes registered, need {1} to skip song.".format(len(self.songs[0][4]), int(
                (len(ctx.message.author.voice.channel.members) - 1) / 2)))
        else:
            await ctx.send("Skipping song")
            await self.voice.stop()

    @commands.command()
    async def pause(self, ctx):
        """Pauses/unpauses current song"""
        if ctx.message.channel.name != "bot-commands":
            return await ctx.send("**Error:** Music Bot commands are only available in #bot-commands")
        if self.music_off:
            return await ctx.send("**Error:** Music Bot features are currently off")
        if ctx.voice_client is None or ctx.voice_client is not self.voice:
            return await ctx.send("**Error:** You must be connected to the voice channel.")

        if ctx.voice_client.is_paused():
            await ctx.voice_client.resume()
            await ctx.send("Resumed music")
        else:
            await ctx.voice_client.pause()
            await ctx.send("Paused music")

    @commands.command()
    async def queue(self, ctx, *args):
        """Shows you the currently queued songs"""
        if ctx.message.channel.name != "bot-commands":
            return await ctx.send("**Error:** Music Bot commands are only available in #bot-commands")
        if self.music_off:
            return await ctx.send("**Error:** Music Bot features are currently off")
        if ctx.voice_client is None or ctx.voice_client is not self.voice:
            return await ctx.send("**Error:** You must be connected to the voice channel.")

        is_mod = False
        for role in ctx.message.author.roles:
            if role.name == "Bot Mod":
                is_mod = True

        queue_string = "```"
        try:
            # if(args[0]=="clear"):
            #	self.songs=[]
            if args[0] == "remove":
                pos = len(self.songs) - 1
                while pos > 0:
                    if args[1].lower() in self.songs[pos][1].lower():
                        if ctx.author.id not in self.songs[pos][4]:
                            self.songs[pos][4].append(ctx.author.id)
                        shortened_title = self.title_shorten(self.songs[pos][1])
                        if (len(ctx.message.author.voice.channel.members) - 1 > len(
                                self.songs[pos][4]) * 2 and not is_mod):
                            await ctx.send("{0} remove votes registered for `{1}`, need {2} to remove song.".format(
                                len(self.songs[pos][4]), shortened_title,
                                (len(ctx.message.author.voice.channel.members) - 1) / 2))
                        else:
                            await ctx.send("Removing `{0}`".format(shortened_title))
                            self.del_song(pos)
                    pos = pos - 1
        except:
            pass
        pos = 0
        for song in self.songs:
            if pos == 0:
                pos_indicator = "> "
            else:
                pos_indicator = "{0}.".format(str(pos))
            shortened_title = self.title_shorten(song[1])
            queue_string = "{0}{1}{2}\n".format(queue_string, pos_indicator, shortened_title)
            pos = pos + 1
        if queue_string == "```":
            return await ctx.send("Queue is empty")
        await ctx.send("{0}```".format(queue_string))

    @commands.command()
    async def musicbot(self, ctx, the_state):
        """Activates/deactivates Music Bot features [MOD ONLY]"""
        is_mod = False
        for role in ctx.message.author.roles:
            if role.name == "Bot Mod":
                is_mod = True
        if is_mod:
            if the_state == "1":
                self.music_off = False
                await ctx.send("Music Bot features now on")
            else:
                self.music_off = True
                await ctx.send("Music Bot features now off")
        else:
            await ctx.send("**Error:** You are not allowed to use this command!")

    async def connection_loop(self):
        while True:
            if self.voice is not None:
                if self.voice.is_playing() or self.processing_songs > 0:
                    self.played_time = time.time()
                if time.time() - self.played_time > 300:
                    try:
                        await self.voice.stop()
                    except:
                        pass
                    try:
                        await self.voice.disconnect()
                    except:
                        pass
                    self.songs = ["None"]
                    await self.voice_channel.send("Disconnecting from Voice Channel due to inactivity")
                    self.voice = None
                    self.processing_songs = 0
                    self.del_all_files()
            await asyncio.sleep(5)

    async def queue_loop(self):
        while True:
            if self.voice is not None:
                timeout_time = time.time() + 3600
                while self.songs == ['None'] or (
                        timeout_time > time.time() and (self.voice.is_playing() or self.voice.is_paused())):
                    if self.songs == ['None']:
                        timeout_time = time.time() + 3600
                    await asyncio.sleep(1)
                if self.songs != ["None"]:
                    self.del_song(0)
                if self.songs != ["None"]:
                    self.skip_votes = self.songs[0][4]
                    self.songs[0][2].play(self.songs[0][0],
                                          after=lambda e: print('Player error: %s' % e) if e else None)
                    shortened_title = self.title_shorten(self.songs[0][1])
                    await self.songs[0][3].send('Now playing: `{}`'.format(shortened_title))
            else:
                await asyncio.sleep(1)
