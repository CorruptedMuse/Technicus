import discord
import aiohttp
from aiohttp import web
import asyncio
import secrets
import hmac
import json
from hashlib import sha1
from binascii import hexlify
import re
import authDeets
from aiohttp.log import access_logger
import time
from commonFunctions import log, merge_strings
import sqlite3

sub_channels = ["https://www.youtube.com/xml/feeds/videos.xml?channel_id=UC-to_wlckb-bFDtQfUZL3Kw", "https://www.youtube.com/xml/feeds/videos.xml?channel_id=UCEKIj6NNGxofLy0dJnFthMg", "https://www.youtube.com/xml/feeds/videos.xml?channel_id=UC-JxDxyH-Q2n9HkbX2V4vSQ"]


def setup_app(app, *, port=None,
            shutdown_timeout=60.0, ssl_context=None, backlog=128,
            access_log=access_logger, handle_signals=True,
            reuse_address=None, reuse_port=None):

    loop = asyncio.get_event_loop()

    runner = web.AppRunner(app, handle_signals=handle_signals, access_log=access_log)
    loop.run_until_complete(runner.setup())

    site = web.TCPSite(runner, port=port,
                                 shutdown_timeout=shutdown_timeout,
                                 ssl_context=ssl_context, backlog=backlog,
                                 reuse_address=reuse_address,
                                 reuse_port=reuse_port)
    loop.run_until_complete(site.start())
    
def archive_feed(feed):
    example_feed = open("badfeed.xml", "w")
    example_feed.write(feed)
    example_feed.close()


class Subber(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.secret = None
        self.request_open = 0
        
        self.connection = sqlite3.connect("reminders.db")
        self.cursor = self.connection.cursor()
        
        self.the_channel = None
        self.create_channel = self.bot.loop.create_task(self.gen_channel())
        
        self.auto_subber = self.bot.loop.create_task(self.renew_sub())
        
        self.app = web.Application()

        self.app.router.add_routes([web.get('/webhook/youtube', self.handle_youtube_get),
                                    web.post('/webhook/youtube', self.handle_youtube_post),
                                    web.get('/webhook/wobsite', self.handle_wobsite_get),
                                    web.post('/webhook/wobsite', self.handle_wobsite_post),
                                    web.get('/webhook/discordauth', self.handle_discordauth_get),
                                    web.post('/webhook/discordauth', self.handle_discordauth_post)])

        setup_app(self.app, port=80)
        
    async def gen_channel(self):
        await self.bot.wait_until_ready()
        self.the_channel = discord.utils.get(self.bot.get_all_channels(), guild__name="Door Monster", name="social-media-feed")

    async def handle_youtube_get(self, request):
        if request.query['hub.topic'] not in sub_channels or request.query['hub.mode'] is 'unsubscribe' or self.request_open == 0:
            print('Invalid subscription request')
            return web.Response(status=404)
        log('Valid sub request to {}'.format(request.query['hub.topic']), None, None, None, None)
        self.request_open = self.request_open - 1
        return web.Response(body=request.query['hub.challenge'])

    async def handle_youtube_post(self, request):
        try:
            sha1_a = request.headers['X-Hub-Signature']
        except:
            sha1_a = 0
        
        body = await request.content.read()
        hmac_checker = hmac.new(self.secret.encode(), body, sha1)
        
        if hexlify(hmac_checker.digest()).decode("utf-8") != sha1_a[5:]:
            print("False packet alert!")
            return web.Response(status=200)
        
        full_feed = body.decode("utf-8")
        
        split_delim = ['<', '>']
        regex_patterns = '|'.join(map(re.escape, split_delim))
        parsed_feed = re.split(regex_patterns, full_feed)
        pos = 1
        video_id = None
        published_date = None
        for elem in parsed_feed:
            if elem == 'yt:videoId':
                video_id = parsed_feed[pos]
            if elem == 'published':
                published_date = parsed_feed[pos]
            pos = pos + 1
        
        if video_id and published_date:
            is_new = True
            video_link = 'https://www.youtube.com/watch?v={}'.format(video_id)
            video_list = open("postedVideos.txt", "r")
            for video_elem in video_list:
                if video_link in str(video_elem):
                    is_new = False
            video_list.close()
            if published_date[:10] != time.strftime("%Y-%m-%d", time.gmtime()):
                is_new = False
            if is_new:
                await self.the_channel.send(":clapper: **New Video Posted!**\n{0}".format(video_link))
                video_list = open("postedVideos.txt", "a")
                video_list.write("{0}\n".format(video_link))
                video_list.close()
        else:
            archive_feed(full_feed)
            if video_id:
                log("Error, could not retreive published_date", None, None, None, None)
            elif published_date:
                log("Error, could not retreive videoId", None, None, None, None)
            else:
                log("Error, could not retreive videoId or published_date", None, None, None, None)
        
        return web.Response(status=200)
        
    async def handle_wobsite_get(self, request):
        if self.request_open == 0:
            print('Invalid subscription request')
            return web.Response(status=404)
        log('Valid sub request to video updates on wobsite', None, None, None, None)
        self.request_open = self.request_open - 1
        return web.Response(body=request.query['challengeKey'])

    async def handle_wobsite_post(self, request):
        body = await request.content.read()
        try:
            sha1_a = request.headers['X-Hub-Signature']
        except:
            sha1_a = 0
        hmac_checker = hmac.new(self.secret.encode(), body, sha1)
        
        if hexlify(hmac_checker.digest()).decode("utf-8") != sha1_a[5:]:
            print("False packet alert!")
            return web.Response(status=200)
        
        json_feed = json.loads(body.decode("utf-8"))
                                                
        video_embed = discord.Embed(title=json_feed['videoTitle'], description=json_feed['videoSummary'], url='https://www.doormonster.tv/video/{}'.format(json_feed['vimeoId']), color=discord.Color.orange())
        video_embed.set_image(url='https://s3.amazonaws.com/doormonster/assets/images/videos/{}'.format(json_feed['videoThumbnail']))
        
        await self.the_channel.send(":clapper: **New Video Posted!**", embed=video_embed)
        
        return web.Response(status=200)
        
    async def handle_discordauth_get(self, request):
        if self.request_open == 0:
            print('Invalid subscription request')
            return web.Response(status=404)
        log('Valid sub request to discord subscribers on wobsite', None, None, None, None)
        self.request_open = self.request_open - 1
        return web.Response(body=request.query['challengeKey'])

    async def handle_discordauth_post(self, request):
        body = await request.content.read()
        try:
            sha1_a = request.headers['X-Hub-Signature']
        except:
            sha1_a = 0
        hmac_checker = hmac.new(self.secret.encode(), body, sha1)
        
        if hexlify(hmac_checker.digest()).decode("utf-8") != sha1_a[5:]:
            print("False packet alert!")
            return web.Response(status=200)
        
        json_feed = json.loads(body.decode("utf-8"))
        
        sql_command = """INSERT INTO wobsiteauths (authorID)
        VALUES ({0});""".format(json_feed)
        self.cursor.execute(sql_command)
        self.connection.commit()
        
        member = discord.utils.get(self.the_channel.guild.members, id=int(json_feed))
        
        if member:
            await member.add_roles(discord.utils.get(member.guild.roles, name="Website Supporter"))
        
        return web.Response(status=200)

    async def renew_sub(self):
        while True:
            self.secret = secrets.token_urlsafe(64)
            self.request_open = 5
            async with aiohttp.ClientSession() as session:
                
                for channel in sub_channels:
                    data = {
                        "hub.mode": "subscribe",
                        "hub.callback": "http://{}/webhook/youtube".format(authDeets.host_name),
                        "hub.lease_seconds": 432000,
                        "hub.topic": channel,
                        "hub.secret": self.secret
                        }
                    destination = "http://pubsubhubbub.appspot.com/subscribe"
                    is_json = False
                    await self.post_data(session, destination, data, is_json)
                    await asyncio.sleep(1)
                
                data = {
                    "endpoint": "http://{}/webhook/wobsite".format(authDeets.host_name),
                    "key": self.secret
                    }
                destination = 'https://www.doormonster.tv:8080/PubSub/subscribe'
                is_json = True
                await self.post_data(session, destination, data, is_json)
                
                data = {
                    "endpoint": "http://{}/webhook/discordauth".format(authDeets.host_name),
                    "key": self.secret
                    }
                destination = 'https://www.doormonster.tv:8080/PubSub/subscribe/discord'
                is_json = True
                await self.post_data(session, destination, data, is_json)
                
            await asyncio.sleep(60 * 60 * 24)
            
    async def post_data(self, session, destination, data, is_json):
        if is_json:
            async with session.post(destination, json=data) as r:
                return r.status
        else:
            async with session.post(destination, data=data) as r:
                return r.status
