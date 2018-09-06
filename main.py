import discord
from discord.ext import commands
import authDeets
import musicBot
import roleBot
import subBot
import miscBot
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
bot.remove_command("help")

client = discord.Client()

connection = sqlite3.connect("reminders.db")
cursor = connection.cursor()

noodle_list = []


@bot.event
async def on_ready():
    print("Logged in as: {0}, with the ID of: {1}".format(bot.user, bot.user.id))
    await bot.change_presence(activity=discord.Game(name='with your code'))
    print("--")


@bot.event
async def on_member_join(member):
    await asyncio.sleep(2)
    for role in member.roles:
        if role.name == "linked":
            await member.add_roles(discord.utils.get(member.guild.roles, name="Patron"))


@bot.event
async def on_member_update(old_member, new_member):
    if old_member.roles != new_member.roles:
        if set(old_member.roles) - set(new_member.roles) == set():
            log("Added Role", old_member, None, set(new_member.roles) - set(old_member.roles), None)
        else:
            log("Deleted Role", old_member, None, set(old_member.roles) - set(new_member.roles), None)
    old_not_patreon = True
    old_not_kick = True
    new_is_patreon = False
    new_is_kick = False
    is_roled = False
    was_not_roled = True
    for role in old_member.roles:
        if role.name == "linked":
            old_not_patreon = False
        if role.name == "Patron":
            was_not_roled = False
        if role.name == "KickstarterBacker":
            old_not_kick = False
    for role in new_member.roles:
        if role.name == "KickstarterBacker":
            new_is_kick = True
        if role.name == "Patron":
            is_roled = True
        if role.name == "linked":
            new_is_patreon = True
    if old_not_patreon and new_is_patreon and not is_roled:
        await new_member.add_roles(discord.utils.get(new_member.guild.roles, name="Patron"))
    if was_not_roled and old_not_kick and (is_roled or new_is_kick):
        await welcome(old_member)


async def welcome(member):
    guild = member.guild
    join_embed = discord.Embed(title="{} has joined the server.".format(member),
                              description='Join Date: {} UTC'.format(str(member.joined_at)[:19]), color=discord.Color.green())
    join_embed.set_footer(text='User Joined')
    join_embed.set_thumbnail(url=member.avatar_url)
    await discord.utils.get(guild.channels, name='introductions').send(embed=join_embed)
    log("Joined", member, None, None, None)


@bot.event
async def on_member_remove(member):
    is_roled = False
    for role in member.roles:
        if role.name == "Patron" or role.name == "KickstarterBacker":
            is_roled = True
    if is_roled:
        guild = member.guild
        cursor.execute("DELETE FROM reminders WHERE authorID={0}".format(member.id))
        cursor.execute("DELETE FROM userInfo WHERE authorID={0}".format(member.id))
        connection.commit()
        leave_embed = discord.Embed(title="{} has left the server.".format(member),
                                   description='Leave Date: {} UTC'.format(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())),
                                   color=discord.Color.red())
        leave_embed.set_footer(text='User Left')
        leave_embed.set_thumbnail(url=member.avatar_url)
        await discord.utils.get(member.guild.channels, name='introductions').send(embed=leave_embed)
        log("Left Guild", member, None, None, None)


@bot.event
async def on_message_delete(message):
    log("Message Delete", message.author, message.channel, message.content, message.created_at)


@bot.event
async def on_message_edit(message1, message2):
    if message1.content == message2.content:
        return
    log("Edited Message", message1.author, message1.channel, message1.content, message2.content)

@bot.command()
async def help(ctx, *args_command_name):
    if len(args_command_name) == 0:
        msg = "```This is the Technicus Bot for the Door Monster server! Type .help <command> to get information on the following commands:\n\n"
        for command in bot.all_commands:
            if command not in ["musicbot", "editrole", "bridge", "massdel", "botban"]:
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
        is_mod = False
        for role in message.author.roles:
            if role.name == "Bot Mod":
                is_mod = True

        if message.channel.name != "bot-commands" and message.content.startswith('.') and not is_mod:
            silenced = add_spam_time(message.author.id)
            if silenced:
                await message.author.send(
                    "Do not spam the bot outside #bot-commands, please wait a bit before using the bot again")
            else:
                await bot.process_commands(message)
        else:
            await bot.process_commands(message)


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

bot.loop.create_task(remind_user())
bot.loop.create_task(spamreduce())
bot.run(authDeets.token)
