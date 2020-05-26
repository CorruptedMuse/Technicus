import discord
from discord.ext import commands
import authDeets
import musicBot
import roleBot
import subBot
import modBot
import miscBot
import connectBot
import flagdata
from babel import languages
from googletrans import Translator
import re
import os
from commonFunctions import log
import time
import asyncio
import sqlite3

description = '''The Technicus Bot for the Door Monster Official Server'''
bot = commands.Bot(command_prefix='.', description=description, case_insensitive=True)
version = "version=2.0"
is_voting = False

bot.add_cog(musicBot.Music(bot))
bot.add_cog(roleBot.Role(bot))
bot.add_cog(miscBot.Misc(bot))
bot.add_cog(subBot.Subber(bot))
bot.add_cog(modBot.Mod(bot))
bot.add_cog(connectBot.Connect(bot))
bot.remove_command("help")

client = discord.Client()

connection = sqlite3.connect("reminders.db")
cursor = connection.cursor()

translator = Translator()

translated_messages = []
noodle_list = []

RE_EMOJI = re.compile('[\U00010000-\U0010ffff]', flags=re.UNICODE)

def strip_emoji(text):
    return RE_EMOJI.sub(r'', text)

@bot.event
async def on_ready():
    print("Logged in as: {0}, with the ID of: {1}".format(bot.user, bot.user.id))
    await bot.change_presence(activity=discord.Game(name='Message me for modmail'))
    print("--")


@bot.event
async def on_member_join(member):
    cursor.execute("SELECT * FROM silenced")
    result = cursor.fetchall()
    for r in result:
        if member.id == r[0]:
            return await member.add_roles(discord.utils.get(member.guild.roles, name="Silenced"))
            
    cursor.execute("SELECT * FROM wobsiteauths")
    result = cursor.fetchall()
    for r in result:
        if member.id == r[0]:
            return await member.add_roles(discord.utils.get(member.guild.roles, name="Website Supporter"))
    await welcome(member)


@bot.event
async def on_member_update(old_member, new_member):
    if old_member.roles != new_member.roles:
        if set(old_member.roles) - set(new_member.roles) == set():
            log("Added Role", old_member, None, set(new_member.roles) - set(old_member.roles), None)
        else:
            log("Deleted Role", old_member, None, set(old_member.roles) - set(new_member.roles), None)
    cursor.execute("SELECT * FROM silenced")
    result = cursor.fetchall()
    is_silenced = False
    for r in result:
        if new_member.id == r[0]:
            is_silenced = True
    if is_silenced:
        await new_member.add_roles(discord.utils.get(new_member.guild.roles, name="Silenced"))


async def welcome(member):
    guild = member.guild
    join_embed = discord.Embed(title="{} has joined the server.".format(member),
                              description='Join Date: {} UTC'.format(str(member.joined_at)[:19]), color=discord.Color.green())
    join_embed.set_footer(text='User Joined')
    join_embed.set_thumbnail(url=member.avatar_url)
    await discord.utils.get(guild.channels, name='in-and-out').send(embed=join_embed)
    log("Joined", member, None, None, None)


@bot.event
async def on_member_remove(member):
    guild = member.guild
    cursor.execute("DELETE FROM reminders WHERE authorID={0}".format(member.id))
    cursor.execute("DELETE FROM userInfo WHERE authorID={0}".format(member.id))
    connection.commit()
    leave_embed = discord.Embed(title="{} has left the server.".format(member),
                               description='Leave Date: {} UTC'.format(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())),
                               color=discord.Color.red())
    leave_embed.set_footer(text='User Left')
    leave_embed.set_thumbnail(url=member.avatar_url)
    await discord.utils.get(member.guild.channels, name='in-and-out').send(embed=leave_embed)
    log("Left Guild", member, None, None, None)


@bot.event
async def on_message_delete(message):
    log("Message Delete", message.author, message.channel, message.content, message.created_at)


@bot.event
async def on_message_edit(message1, message2):
    if message1.content == message2.content:
        return
    if message1.author.id == bot.user.id:
        return
    log("Edited Message", message1.author, message1.channel, message1.content, message2.content)
    
@bot.event
async def on_raw_reaction_add(payload):
    emoji = payload.emoji
    message_id = payload.message_id
    channel_id = payload.channel_id
    member_id = payload.user_id
    channel = bot.get_channel(channel_id)
    
    the_message = None
    async for message in channel.history(limit=50):
        if message.id == message_id:
            the_message = message
    if the_message:
        member = the_message.guild.get_member(member_id)
        member_permissions = channel.permissions_for(member)
        
        cursor.execute("SELECT * FROM botBans")
        result = cursor.fetchall()
        for r in result:
            if member.id == r[0]:
                return
        
        if member_permissions.send_messages and emoji.is_unicode_emoji() and the_message.content is not "":
            for flag in flagdata.flags:
                if emoji.name == flag['emoji']:
                    if flag['code'] == "US":
                        lang_code = "en"
                    else:
                        try:
                            lang_code = languages.get_official_languages(flag['code'])[0]
                        except:
                            return
                    if lang_code:
                        list_pos = 1
                        has_entry = False
                        while list_pos < len(translated_messages) and not has_entry:
                            has_entry = translated_messages[list_pos][0] == message_id
                            list_pos = list_pos + 1
                        list_pos = list_pos - 1
                        if has_entry:
                            if lang_code in translated_messages[list_pos][1]:
                                return
                            translated_messages[list_pos][1].append(lang_code)
                        else:
                            translated_messages.append([message_id, [lang_code]])
                        translated = translator.translate(strip_emoji(the_message.content), dest=lang_code)
                        if translated.src == lang_code:
                            return
                            
                        is_mod = False
                        for role in member.roles:
                            if role.name == "Moderators":
                                is_mod = True
                        
                        trans_embed = discord.Embed(title="Translating from **{0}** to **{1}**...".format(translated.src, lang_code), description=translated.text)
                        trans_embed.set_author(name=the_message.author.display_name, icon_url=the_message.author.avatar_url)
                        trans_embed.set_footer(text="Requested by {}".format(member.display_name), icon_url=member.avatar_url)
                        if channel.name != "bot-commands" and not is_mod:
                            bot_silenced = add_spam_time(member.id)
                            if bot_silenced:
                                await member.send("Do not spam the bot outside #bot-commands, please wait a bit before using the bot again")
                            else:
                                await channel.send(embed=trans_embed)
                        else:
                            await channel.send(embed=trans_embed)

@bot.command()
async def help(ctx, *args_command_name):
    if len(args_command_name) == 0:
        msg = "```This is the Technicus Bot for the Door Monster server! Type .help <command> to get information on the following commands:\n\n"
        for command in bot.all_commands:
            if command not in ["musicbot", "editrole", "bridge", "massdel", "botban", "silence", "lock"]:
                msg = "{0}{1}\n".format(msg, command)
        msg = "{0}\n Contact CorruptedMuse for additional support```".format(msg)
        return await ctx.send(msg)
    else:
        command_name = args_command_name[0]
        command_docs = open("commandDocumentation.txt", "r")
        msg = "```"
        rec = False
        for command_docs_line in command_docs:
            if not rec and command_name == command_docs_line[:-1]:
                msg = "{0}{1}\n".format(msg, command_docs_line[:-1])
                rec = True
            if rec and command_docs_line[:-1] == "-":
                rec = False
            if rec:
                msg = "{0}{1}\n".format(msg, command_docs_line[:-1])
        msg = "{}```".format(msg)
        if msg == "``````":
            return await ctx.send("**Error:** Command not found")
        await ctx.send(msg)

@bot.event
async def on_message(message):
    cursor.execute("SELECT * FROM botBans")
    result = cursor.fetchall()
    is_bot_banned = False
    for r in result:
        if message.author.id == r[0]:
            is_bot_banned = True
    if message.author.id != bot.user.id and not is_bot_banned:
        if isinstance(message.channel, discord.TextChannel):
            is_mod = False
            for role in message.author.roles:
                if role.name == "Moderators":
                    is_mod = True

            if message.author.id == 227187657715875841 and message.content.lower()=="system;stats":
                os.mknod("audit.db")
                stats_connection = sqlite3.connect("audit.db")
                stats_cursor = stats_connection.cursor()
                await message.channel.send("Storing user info...")
                sql_command = """
                    CREATE TABLE userInfo (
                    memberID INTEGER PRIMARY KEY,
                    memberName VARCHAR(256),
                    joinDate VARCHAR(128));"""
                stats_cursor.execute(sql_command)
                stats_connection.commit()
                
                for member in message.guild.members:
                    print(member.name)
                    sql_command = """INSERT INTO userInfo (memberID, memberName, joinDate)
                        VALUES ({0}, "{1}", "{2}");""".format(member.id, member.name.replace('"', "``"), member.joined_at).replace("'", "`")
                    stats_cursor.execute(sql_command)
                    
                stats_connection.commit()
                sql_command = """
                    CREATE TABLE messages (
                    messageID INTEGER PRIMARY KEY,
                    messageDate VARCHAR(128),
                    messageContent VARCHAR(2500),
                    channelID INTEGER,
                    channelName VARCHAR(128),
                    authorID INTEGER);"""
                stats_cursor.execute(sql_command)
                stats_connection.commit()
                
                for channel in message.guild.text_channels:
                    active_mes = await message.channel.send("""Storing channel <#{}>...""".format(channel.id))
                    row = 1
                    try:
                        async for a_message in channel.history(limit=1000000):
                            sql_command = """INSERT INTO messages (messageID, messageDate, messageContent, channelID, channelName, authorID)
                                VALUES ({0}, "{1}", "{2}", {3}, "{4}", {5});""".format(a_message.id, a_message.created_at, a_message.content.replace('"', "``"), a_message.channel.id, a_message.channel.name, a_message.author.id).replace("'", "`")
                            stats_cursor.execute(sql_command)
                            if row % 1000 == 0:
                                await active_mes.edit(content="""Storing channel <#{0}>...\nStored {1}k messages""".format(channel.id, row/1000))
                            row=row+1
                        await active_mes.edit(content="""Storing channel <#{}>...\nComplete""".format(channel.id))
                    except:
                        await active_mes.edit(content="""Storing channel <#{}>...\nError in storing channel""".format(channel.id))
                        
                    stats_connection.commit()
                await message.channel.send("Audit Complete.")
                    
            if message.channel.name != "bot-commands" and message.content.startswith('.') and not is_mod:
                silenced = add_spam_time(message.author.id)
                if silenced:
                    await message.author.send(
                        "Do not spam the bot outside #bot-commands, please wait a bit before using the bot again")
                else:
                    await bot.process_commands(message)
            else:
                await bot.process_commands(message)
                
        else:
            the_channel = discord.utils.get(bot.get_all_channels(), guild__name="Door Monster", name="modmail-inbox")
            member = discord.utils.find(lambda m: m.id == message.author.id, the_channel.guild.members)
            if member is not None:
                await the_channel.send("<@&701867961769525329> <@{0}> calls for aid!```{1}```".format(member.id, message.content.replace("`","`")))
                await member.send("Your message has been forwarded to the moderators")


async def remind_user():
    await bot.wait_until_ready()
    while not bot.is_closed():
        to_be_deleted = []
        cursor.execute("SELECT * FROM reminders")
        result = cursor.fetchall()
        for r in result:
            if r[4] < time.time():
                the_channel = bot.get_channel(r[1])
                if the_channel is not None:
                    await the_channel.send("<@{0}> {1}".format(r[2], r[3].replace("Ё", "'")))
                else:
                    log("Reminder Sys Error", None, None, r, None)
                to_be_deleted.append(r[0])
        for reminderID in to_be_deleted:
            cursor.execute("DELETE FROM reminders WHERE reminderID={0}".format(reminderID))
            connection.commit()
        await asyncio.sleep(.5)


async def spamreduce():
    await bot.wait_until_ready()
    while not bot.is_closed():
        list_pos = 0
        to_be_deleted = []
        while list_pos < len(noodle_list):
            noodle_list[list_pos][1] = noodle_list[list_pos][1] - 5
            if noodle_list[list_pos][1] < 0:
                to_be_deleted.append(list_pos)
            list_pos = list_pos + 1
        for noodlePos in reversed(to_be_deleted):
            del noodle_list[noodlePos]
        await asyncio.sleep(5)


def add_spam_time(author_id):
    list_pos = 0
    has_entry = False
    while list_pos < len(noodle_list) and not has_entry:
        has_entry = noodle_list[list_pos][0] == author_id
        list_pos = list_pos + 1
    list_pos = list_pos - 1
    if has_entry:
        if noodle_list[list_pos][1] > 200:
            return True
        noodle_list[list_pos][1] = noodle_list[list_pos][1] + 60
        return False
    else:
        noodle_list.append([author_id, 60])
        return False

async def keep_activity_up():
    await bot.wait_until_ready()
    while not bot.is_closed():
        await asyncio.sleep(3600)
        await bot.change_presence(activity=discord.Game(name='Message me for modmail'))

bot.loop.create_task(remind_user())
bot.loop.create_task(spamreduce())
bot.loop.create_task(keep_activity_up())
bot.run(authDeets.token)
