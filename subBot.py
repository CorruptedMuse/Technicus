import discord
import aiohttp
from aiohttp import web
import asyncio
import re
import authDeets
from aiohttp.log import access_logger
import time

sub_channels = ['https://www.youtube.com/xml/feeds/videos.xml?channel_id=UC-to_wlckb-bFDtQfUZL3Kw', 'https://www.youtube.com/xml/feeds/videos.xml?channel_id=UCEKIj6NNGxofLy0dJnFthMg']


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


class Subber():
    def __init__(self, bot):
        self.bot = bot
        self.app = web.Application()

        self.auto_subber = self.bot.loop.create_task(self.renew_sub())

        self.app.router.add_routes([web.get('/', self.handle_get),
                                    web.post('/', self.handle_post)])

        setup_app(self.app, port=authDeets.youtube_port)

    async def handle_get(self, request):
        if request.query['hub.topic'] not in sub_channels or request.query['hub.mode'] is 'unsubscribe':
            print('Invalid subscription request')
            return web.Response(status=404)
        print('Valid sub request to {}'.format(request.query['hub.topic']))
        return web.Response(body=request.query['hub.challenge'])

    async def handle_post(self, request):
        full_feed = ""
        async for line in request.content:
            full_feed = "{0}{1}".format(full_feed, str(line)[1:].replace("'",""))
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
                the_channel = discord.utils.get(self.bot.get_all_channels(), guild__name="Door Monster",
                                                name="announcements")
                await the_channel.send(":clapper: **New Video Posted!**\n{0}".format(video_link))
                video_list = open("postedVideos.txt", "a")
                video_list.write("{0}\n".format(video_link))
                video_list.close()
        return web.Response(status=200)

    async def renew_sub(self):
        while True:
            for channel in sub_channels:
                async with aiohttp.ClientSession() as session:
                    data = {
                        'hub.mode': 'subscribe',
                        'hub.callback': 'http://{0}:{1}/'.format(authDeets.host_name,
                                                                                 authDeets.youtube_port),
                        'hub.lease_seconds': 432000,
                        'hub.topic': channel
                        }
                    await self.post_data(session, data)
                await asyncio.sleep(5)
            await asyncio.sleep(60 * 60 * 24)
            
    async def post_data(self, session, data):
        async with session.post('http://pubsubhubbub.appspot.com/subscribe', data=data) as r:
            return r.status
