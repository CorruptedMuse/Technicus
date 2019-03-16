import discord
from discord.ext import commands
import sqlite3
import random
import time
import asyncio
from commonFunctions import log, merge_strings

version = 3


class Mod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.connection = sqlite3.connect("reminders.db")
        self.cursor = self.connection.cursor()
        self.check_silence = self.bot.loop.create_task(self.reset_silence())

    @commands.command()
    async def massdel(self, ctx, numbers):
        """Delete a lot of channel history [MOD ONLY]"""
        is_mod = False
        for role in ctx.message.author.roles:
            if role.name == "Bot Mod":
                is_mod = True
        if not is_mod:
            return await ctx.send("**Error:** You do not have permission to use this command!")
        log("Mass delete init", ctx.author, ctx.channel, numbers, None)
        async for elem in ctx.channel.history(limit=int(numbers) + 1):
            log("Mass Delete", elem.author, elem.channel, elem.content, elem.created_at)
            await elem.delete()

    @commands.command()
    async def botban(self, ctx, *args_member):
        """Prevent someone from using the bot or reverse the ban [MOD ONLY]"""
        is_mod = False
        for role in ctx.message.author.roles:
            if role.name == "Bot Mod":
                is_mod = True
        if not is_mod:
            return await ctx.send("**Error:** You do not have permission to use this command!")
        member = discord.utils.get(ctx.message.guild.members, name=merge_strings(args_member))
        if member is None:
            return await ctx.send("**Error:** User not found")
        if member.id == 227187657715875841:
            return await ctx.send("**Error:** This user is very important and cannot be banned!")
        self.cursor.execute("SELECT * FROM botBans")
        result = self.cursor.fetchall()
        is_bot_banned = False
        for r in result:
            if member.id == r[0]:
                is_bot_banned = True
        if is_bot_banned:
            self.cursor.execute("DELETE FROM botBans WHERE author_id={0}".format(member.id))
            self.connection.commit()
            await ctx.send(":sunflower: User now has permission to use the bot")
        else:
            sql_command = """INSERT INTO botBans (author_id, time)
                VALUES ({0}, {1});""".format(member.id, 0)
            self.cursor.execute(sql_command)
            self.connection.commit()
            await ctx.send(":crossed_swords: User no longer has permission to use the bot")
            
    @commands.command()
    async def bridge(self, ctx, guild_name, channel_name, *args_message):
        """For special-case manual control of Technicus [MOD ONLY]"""
        if ctx.message.author.id == 227187657715875841:
            the_channel = discord.utils.get(self.bot.get_all_channels(), guild__name=guild_name, name=channel_name)
            if the_channel is None:
                await ctx.send("**Error:** Channel not found!")
            else:
                if args_message[0] == ".addRole":
                    await discord.utils.get(the_channel.guild.members, name=args_message[1], discriminator=args_message[2]).add_roles(
                        discord.utils.get(the_channel.guild.roles, name=args_message[3]))
                else:
                    the_message = merge_strings(args_message)
                    await the_channel.send(the_message.replace("|", "\n"))
        else:
            await ctx.send("**Error:** You are not allowed to use this command!")
            
    @commands.command()
    async def lock(self, ctx, channel_name, *time_data: str):
        is_mod = False
        for role in ctx.message.author.roles:
            if role.name == "Bot Mod":
                is_mod = True
        if not is_mod:
            return await ctx.send("**Error:** You are not allowed to use this command!")
        the_channel = discord.utils.get(ctx.guild.channels, name=channel_name)
        if the_channel is None:
            return await ctx.send("**Error:** Channel not found!")
        
        is_locked = False
        
        for over in the_channel.overwrites_for(discord.utils.get(ctx.message.guild.roles, name="Patron")):
            if over[0] == "send_messages":
                if over[1] == False:
                    is_locked = True
        
        wait_time = 0
        for time_datum in time_data:
            try:
                if time_datum[-1:] == "d":
                    wait_time = wait_time + int(time_datum[:-1], 10) * 24 * 60 * 60
                elif time_datum[-1:] == "h":
                    wait_time = wait_time + int(time_datum[:-1], 10) * 60 * 60
                elif time_datum[-1:] == "m":
                    wait_time = wait_time + int(time_datum[:-1], 10) * 60
                elif time_datum[-1:] == "s":
                    wait_time = wait_time + int(time_datum[:-1], 10)
                else:
                    await ctx.send("""**Error:** Correct usage is `.lock <channel> <>d <>h <>m <>s`""")
                    return
            except Exception:
                await ctx.send("""**Error:** Correct usage is `.lock <channel> <>d <>h <>m <>s`""")
                return
        
        kick_role = discord.utils.get(ctx.message.guild.roles, name="KickstarterBacker")
        patron_role = discord.utils.get(ctx.message.guild.roles, name="Patron")
        kick_overwrite = the_channel.overwrites_for(kick_role)
        patron_overwrite = the_channel.overwrites_for(patron_role)
        if is_locked:
            kick_overwrite.send_messages = None
            patron_overwrite.send_messages = None
        else:
            kick_overwrite.send_messages = False
            patron_overwrite.send_messages = False
        await the_channel.set_permissions(kick_role, overwrite=kick_overwrite)
        await the_channel.set_permissions(patron_role, overwrite=patron_overwrite)
        if is_locked:
            return await ctx.send("Unlocked channel {}".format(the_channel.name))
        else:
            if wait_time == 0:
                return await ctx.send("Locked channel {}".format(the_channel.name))
            else:
                await ctx.send("Locked channel {0} until {1}".format(the_channel.name, time.asctime(time.gmtime(wait_time + time.time()))))
                await asyncio.sleep(wait_time)
                kick_overwrite.send_messages = None
                patron_overwrite.send_messages = None
                await the_channel.set_permissions(kick_role, overwrite=kick_overwrite)
                await the_channel.set_permissions(patron_role, overwrite=patron_overwrite)
                await ctx.send("Unlocked channel {}".format(the_channel.name))
           
    @commands.command()
    async def silence(self, ctx, member_name: str, reason: str, *time_data: str):
        is_mod = False
        for role in ctx.message.author.roles:
            if role.name == "Bot Mod":
                is_mod = True
        if not is_mod:
            return await ctx.send("**Error:** You are not allowed to use this command!")
        member = discord.utils.get(ctx.message.guild.members, name=member_name)
        if member is None:
            member = discord.utils.get(ctx.message.guild.members, nick=member_name)
        if member is None and len(ctx.message.mentions) is not 0:
            member = ctx.message.mentions[0]
        if member is None:
            return await ctx.send("**Error:** User not found")
        wait_time = 0
        for time_datum in time_data:
            try:
                if time_datum[-1:] == "m":
                    wait_time = wait_time + int(time_datum[:-1], 10) * 24 * 60 * 60 * 30
                elif time_datum[-1:] == "w":
                    wait_time = wait_time + int(time_datum[:-1], 10) * 24 * 60 * 60 * 7
                elif time_datum[-1:] == "d":
                    wait_time = wait_time + int(time_datum[:-1], 10) * 24 * 60 * 60
                elif time_datum[-1:] == "h":
                    wait_time = wait_time + int(time_datum[:-1], 10) * 60 * 60
                elif time_datum[-1:] == "n":
                    wait_time = wait_time + int(time_datum[:-1], 10) * 60
                elif time_datum[-1:] == "s":
                    wait_time = wait_time + int(time_datum[:-1], 10)
                else:
                    await ctx.send("""**Error:** Correct usage is `.silence "user" "reason" <>m <>w <>d <>h <>n <>s`""")
                    return
            except Exception:
                await ctx.send("""**Error:** Correct usage is `.silence "user" "reason" <>m <>w <>d <>h <>n <>s`""")
                return
        exp_time = wait_time + time.time()
        author_id = member.id
        self.cursor.execute("SELECT * FROM silenced")
        result = self.cursor.fetchall()
        for r in result:
            if r[0] == author_id:
                sql_command = """UPDATE silenced 
                                 SET reason = "{1}", time = {2} 
                                 WHERE authorID = {0};""".format(author_id, reason, exp_time)
                self.cursor.execute(sql_command)
                self.connection.commit()
                log("Silenced user update", member, None, reason, time.asctime(time.gmtime(exp_time)))
                if wait_time == 0:
                    await member.send("Your silenced period has ended early")
                else:
                    await member.send("Your silenced period has been updated to last until {} UTC".format(time.asctime(time.gmtime(exp_time))))
                return await ctx.send("""{0}'s silenced period has been changed to {1} """.format(member_name, time.asctime(time.gmtime(exp_time))))


        sql_command = """INSERT INTO silenced (authorID, reason, time)
                         VALUES ({0}, "{1}", {2});""".format(author_id, reason, exp_time)
        log("User silenced", member, None, reason, time.asctime(time.gmtime(exp_time)))
        await member.add_roles(discord.utils.get(ctx.message.guild.roles, name="Silenced"))
        self.cursor.execute(sql_command)
        self.connection.commit()
        await member.send("You have been silenced until {0} with the reason {1}\nContact a moderator for any questions".format(time.asctime(time.gmtime(exp_time)), reason))
        await ctx.send("""{0} has been silenced until {1}""".format(member_name, time.asctime(time.gmtime(exp_time))))

    async def reset_silence(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            to_be_deleted = []
            self.cursor.execute("SELECT * FROM silenced")
            result = self.cursor.fetchall()
            for r in result:
                if r[2] < time.time():
                    guild = None
                    for test_guild in self.bot.guilds:
                        if test_guild.name == "Door Monster":
                            guild = test_guild
                    if guild is not None:
                        member = guild.get_member(r[0])
                        if member is not None:
                            await member.remove_roles(discord.utils.get(guild.roles, name="Silenced"))
                            for role in member.roles:
                                if role.name == "linked":
                                    await member.add_roles(discord.utils.get(member.guild.roles, name="Patron"))
                                    
                            log("User unsilenced", member, None, r[1], None)
                            mod_channel = self.bot.get_channel(496618677228273665)
                            await mod_channel.send("<@&496616256045056001> User {} has been un-silenced".format(member.name))
                    to_be_deleted.append(r[0])
            for authorID in to_be_deleted:
                self.cursor.execute("DELETE FROM silenced WHERE authorID={0}".format(authorID))
                self.connection.commit()
            await asyncio.sleep(.5)
