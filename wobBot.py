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


class Subber(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.secret = None
        self.request_open = 0
        self.app = web.Application()

        self.auto_subber = self.bot.loop.create_task(self.renew_sub())

        self.app.router.add_routes([web.get('/', self.handle_get),
                                    web.post('/', self.handle_post)])

        setup_app(self.app, port=authDeets.wobsite_port)

    async def handle_get(self, request):
        if self.request_open == 0:
            print('Invalid subscription request')
            return web.Response(status=404)
        print('Valid sub request to wobsite')
        self.request_open = self.request_open - 1
        return web.Response(body=request.query['challengeKey'])

    async def handle_post(self, request):
        print("Get post")
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
        
        the_channel = discord.utils.get(self.bot.get_all_channels(), guild__name="Door Monster",
                                                name="announcements")
                                                
        video_embed = discord.Embed(title=json_feed['videoTitle'], description=json_feed['videoSummary'], url='https://www.doormonster.tv/video/{}'.format(json_feed['vimeoId']), color=discord.Color.orange())
        video_embed.set_thumbnail(url='https://www.doormonster.tv/{}'.format(json_feed['videoThumbnail']))
        
        await the_channel.send(":clapper: **New Video Posted!**", embed=video_embed)
        
        return web.Response(status=200)

    async def renew_sub(self):
        while True:
            self.secret = secrets.token_urlsafe(64)
            self.request_open = 1
            async with aiohttp.ClientSession() as session:
                data = {
                    'endpoint': 'http://{0}:{1}/'.format(authDeets.host_name, authDeets.wobsite_port),
                    'key': self.secret
                    }
                await self.post_data(session, data)
                await asyncio.sleep(1)
            await asyncio.sleep(60 * 60 * 24)
            
    async def post_data(self, session, data):
        async with session.post('https://www.doormonster.tv:8080/PubSub/subscribe', json=data) as r:
            return r.status