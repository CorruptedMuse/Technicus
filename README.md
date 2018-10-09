# Technicus

Technicus is a Discord bot I threw together over the course of two months, and have kept updated for about 10 (as I write this). I wanted to give access to people so they could use some snippets of code if they want, as long as I get some credit and stuff.

Mostly self-taught so it's a bit of a mess. Not necessarily recommended for someone looking to start a bot but doesn't know anything about discord or python.

Technicus uses https://github.com/Rapptz/discord.py as its backbone, specifically the rewrite version. It will work on python 3.6, maybe 3.5 or 3.7 and definitely not on 2. It is also not built to work on multiple servers (some things will break).

There should be an additional file called authDeets.py included in any implementation which declares the bot token as "token" (a string) as well as the url ("host_name") and port ("youtube_port") that the YouTube subscription system uses to set up the webhook (you will also need that url to point to wherever you are running this bot).

It needs ffmpeg for the music bot features to work. As for other modules, just try to run the program and install whatever module you are missing.

There are also some custom configured settings, like the guild/channel that video updates are posted to, the channel where join/leave messages are posted, the fact that the bridge command is keyed to my own user id, and the entirety of the autorole/autojoin system which you'll probably going to want to completely scrap if you're not doing the very specific setup Technicus is made to do with Patreon.
