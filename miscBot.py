import discord
from discord.ext import commands
import sqlite3
import random
import time
import asyncio
from commonFunctions import log, merge_strings

version = 3

numbers = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "bomb"]

class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.connection = sqlite3.connect("reminders.db")
        self.cursor = self.connection.cursor()
        self.active_votes = []

    @commands.command()
    async def add(self, ctx, left: int, right: int):
        """Adds two numbers together."""
        await ctx.send(left + right)

    @commands.command()
    async def roll(self, ctx, dice: str):
        """Rolls a dice in NdN format."""
        try:
            rolls, limit = map(int, dice.split('d'))
        except Exception:
            await ctx.send('**Error:** Format has to be in NdN!')
            return
        if str(limit) == "1":
            return await ctx.send("But that's just ones")
        if rolls * limit > 1000:
            await ctx.send('**Error:** Too many dice!')
        else:
            result = ', '.join(str(random.randint(1, limit)) for r in range(rolls))
            await ctx.send(":game_die: {0} :game_die:".format(result))

    @commands.command()
    async def whoami(self, ctx):
        """Tells you your identity"""
        user_data = self.get_info(ctx.author.id)
        whoami_embed = discord.Embed(title="{}'s Information".format(ctx.message.author.name),
                                     description='**Join Date:** {0.joined_at} \n**User ID:** {0.id} \n**Location:** {1} \n**Bio:** {2}'.format(
                                         ctx.message.author, user_data[0].replace("Ё", "'"),
                                         user_data[1].replace("Ё", "'")),
                                     color=discord.Color.gold())
        # whoami_embed.set_footer(text=version)
        whoami_embed.set_thumbnail(url=ctx.message.author.avatar_url)
        await ctx.send(embed=whoami_embed)

    @commands.command()
    async def whois(self, ctx, *args_member):
        """Tells you someone else's identity"""
        member = discord.utils.get(ctx.message.guild.members, name=merge_strings(args_member))
        if member is None:
            member = discord.utils.get(ctx.message.guild.members, nick=merge_strings(args_member))
        if member is None and len(ctx.message.mentions) is not 0:
            member = ctx.message.mentions[0]
        if member is None:
            return await ctx.send("**Error:** User not found")
        user_data = self.get_info(member.id)
        whois_embed = discord.Embed(title="{}'s Information".format(member.name),
                                    description='**Join Date:** {0.joined_at} \n**User ID:** {0.id} \n**Location:** {1} \n**Bio:** {2}'.format(
                                        member, user_data[0].replace("Ё", "'"), user_data[1].replace("Ё", "'")),
                                    color=discord.Color.gold())
        # whois_embed.set_footer(text=version)
        whois_embed.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed=whois_embed)

    @commands.command()
    async def setmy(self, ctx, attribute, *args):
        """Usage: .setMy <location/bio> information"""
        if (ctx.message.channel.name != "bot-commands"):
            return await ctx.send("**Error:** This command is only available in #bot-commands")
        info = merge_strings(args)
        temp = self.get_info(ctx.message.author.id)
        if attribute.lower() == "bio":
            if len(info) > 500:
                return await ctx.send("**Error:** Your bio can only be 500 characters long!")
            sql_command = """UPDATE userInfo
            SET bio = "{0}"
            WHERE authorID = {1};""".format(info.replace("'", "Ё"), ctx.message.author.id)
            self.cursor.execute(sql_command)
            self.connection.commit()
            await ctx.send("Bio set")
        elif attribute.lower() == "location":
            if len(info) > 50:
                return await ctx.send("**Error:** Your location can only be 50 characters long!")
            sql_command = """UPDATE userInfo
            SET location = "{0}"
            WHERE authorID = {1};""".format(info.replace("'", "Ё"), ctx.message.author.id)
            self.cursor.execute(sql_command)
            self.connection.commit()
            await ctx.send("Location set")
        else:
            await ctx.send("**Error:** Unknown attribute to set")

    def get_info(self, author_id):
        self.cursor.execute("SELECT * FROM userInfo")
        result = self.cursor.fetchall()
        for r in result:
            if r[0] == author_id:
                return [r[1], r[2]]
        sql_command = """INSERT INTO userInfo (authorID, location, bio)
        VALUES ({0}, "{1}", "{2}");""".format(author_id, "The Internet", "I haven't made a bio for myself")
        self.cursor.execute(sql_command)
        self.connection.commit()
        return ["The Internet", "I haven't made a bio for myself"]

    @commands.command()
    async def ping(self, ctx):
        """Pong!"""
        msg_time_sent = ctx.message.created_at
        msg_now = time.time()
        await ctx.send("The message was sent at: " + str(msg_time_sent))

    @commands.command()
    async def about(self, ctx):
        """Tells you about this bot."""
        about_embed = discord.Embed(title='About Technicus', description="Custom Discord Bot\nhttps://github.com/CorruptedMuse/Technicus",
                                    url="https://www.youtube.com/watch?v=XJskpfaJH2w",
                                    color=discord.Color.gold())
        about_embed.set_footer(text="Version={}".format(version))
        about_embed.set_thumbnail(url=self.bot.user.avatar_url)
        await ctx.send(embed=about_embed)

    @commands.command()
    async def remindme(self, ctx, remind_mes: str, *time_data: str):
        """Make a reminder for yourself"""
        is_mod = False
        for role in ctx.message.author.roles:
            if role.name == "Bot Mod":
                is_mod = True
        if ("@everyone" in remind_mes or "@here" in remind_mes) and not is_mod:
            return await ctx.send("**Error:** Message contains use of mentions you are not allowed to use!")
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
                    await ctx.send("""**Error:** Correct usage is `.remindme "<message>" <>d <>h <>m <>s`""")
                    return
            except Exception:
                await ctx.send("""**Error:** Correct usage is `.remindme "<message>" <>d <>h <>m <>s`""")
                return
        if not 2 <= wait_time <= 1209600:
            await ctx.send("**Error:** remind_mes have to be between 2 seconds and a fortnight")
            return
        wait_time = wait_time + time.time()
        channel_id = str(ctx.message.channel.id)
        author_id = str(ctx.message.author.id)
        sql_command = """INSERT INTO reminders (reminderID, channelID, authorID, message, time)
        VALUES ({0}, {1}, {2}, "{3}", {4});""".format(time.time(), channel_id, author_id, remind_mes.replace("'", "Ё"),
                                                      wait_time)
        self.cursor.execute(sql_command)
        await ctx.send(""":thumbsup: I'll remind you "{0}" """.format(remind_mes))
        self.connection.commit()

    @commands.command()
    async def x(self, ctx, cnumber: str):
        """Returns the XKCD comic specified"""
        if cnumber.isnumeric():
            if int(cnumber) == 631:
                await ctx.send("**Error:** Not allowed on server")
            else:
                await ctx.send("https://xkcd.com/{0}/".format(cnumber))
        else:
            await ctx.send("**Error:** Not a comic number")

    @commands.command()
    async def wizard(self, ctx):
        """For when you just wanna dance"""
        await ctx.send(file=discord.File('JeffereyWizardDance.gif'))

    @commands.command()
    async def neelyfiles(self, ctx):
        """Dangerous Content Follows"""
        await ctx.send(file=discord.File('neely/neely{0}.png'.format(str(random.randint(1, 5)))))

    @commands.command()
    async def thanks(self, ctx, *args):
        """Give thanks to someone or the bot"""
        if len(args) == 0:
            return await ctx.send(":sun_with_face: You're welcome!")
        member = discord.utils.get(ctx.message.guild.members, name=merge_strings(args))
        if member is None:
            member = discord.utils.get(ctx.message.guild.members, nick=merge_strings(args))
        if member is None and len(ctx.message.mentions) is not 0:
            member = ctx.message.mentions[0]
        if member is None:
            return await ctx.send("**Error:** User not found")
        message = ":gift: Giving thanks to <@{0}>".format(member.id)
        await ctx.send(message)

    @commands.command()
    async def vote(self, ctx, *options):
        """Vote for something"""
        if ctx.channel.id in self.active_votes:
            return await ctx.send("**Error:** There is already a vote going on in this channel!")
        timer = "2"
        if options[0].isnumeric():
            timer = options[0]
            options = options[1:]
        if len(options) > 9 or len(options) < 2:
            return await ctx.send("**Error:** There should be 2 to 9 options to select")
        float_time = float(timer)
        if float_time < 1 or float_time > 15:
            return await ctx.send("**Error:** Votes should be between 1 and 15 minutes")

        msg = ":ballot_box: Vote beginning! React to this message with your selection\n```\n"
        num = 1
        for option in options:
            msg = "{0}{1}: {2}\n".format(msg, num, option.replace("`", "'"))
            num = num + 1
        if len(msg) > 1990:
            return await ctx.send("**Error:** That ballot exceeds Discord's native message character limit")
        vote_mes = await ctx.send("{0}```".format(msg))
        self.active_votes.append(ctx.channel.id)
        for i in range(1, len(options) + 1):
            await vote_mes.add_reaction("{0}\U000020e3".format(i))
        await vote_mes.add_reaction("❌")
        await asyncio.sleep(float_time * 60)
        try:
            vote_over = await ctx.history().get(id=vote_mes.id)
        except:
            self.active_votes.remove(ctx.channel.id)
            return await ctx.send("**Error:** Voting ballot not found. Was deleted?")
        self.active_votes.remove(ctx.channel.id)
        results = [0] * len(options)
        no_conf = 0
        for reaction in vote_over.reactions:
            for i in range(0, len(options)):
                if str(reaction) == "{0}\U000020e3".format(i + 1):
                    results[i] = reaction.count - 1
                if str(reaction) == "❌".format(i + 1):
                    no_conf = reaction.count - 1
        winners = [[-1, ""]]
        i = 0
        for result in results:
            if result > winners[0][0]:
                winners = [[result, options[i]]]
            elif result == winners[0][0]:
                winners.append([result, options[i]])
            i = i + 1
        message = ""
        if winners[0][0] < no_conf:
            message = "Vote nullified by no confidence"
        elif winners[0][0] == 0:
            message = "Nobody voted, result inconclusive."
        elif 1 == len(winners):
            message = "`{0}` has won with {1}% of the vote.".format(winners[0][1].replace("`", "'"),
                                                                    int(winners[0][0] * 100 / sum(results)))
        elif 2 == len(winners):
            message = "`{0}` and `{1}` have tied with {2}% of the vote each.".format(winners[0][1].replace("`", "'"),
                                                                                     winners[1][1].replace("`", "'"),
                                                                                     int(
                                                                                         winners[0][0] * 100 / sum(
                                                                                             results)))
        else:
            message = "and `{0}` have tied with {1}% of the vote each.".format(winners[-1][1].replace("`", "'"),
                                                                               int(winners[0][0] * 100 / sum(results)))
            for winner in reversed(winners[:-1]):
                message = "`{0}`, {1}".format(winner[1].replace("`", "'"), message)
        message = ":ballot_box_with_check: Vote has ended! {0}".format(message)
        await ctx.send(message)
    
    @commands.command()
    async def opt(self, ctx, dir, channel_name):
        if ctx.message.channel.name != "bot-commands":
            return await ctx.send("**Error:** This command is only available in #bot-commands")
        
        valid_channels = ["introductions", "general", "questions", "games", "techtalk", "suggestions", "music", "healthy-living", "twitch", "microphoneless", "fanart", "fanprojects", "show-and-tell", "doormonstergifs", "skyvault"]
        if not channel_name in valid_channels:
            msg = "**Error:** You can only opt in and out of the following channels:```"
            for valid_channel in valid_channels:
                msg = "{0}\n{1}".format(msg, valid_channel)
            return await ctx.send("{}```".format(msg))
        
        the_channel = discord.utils.get(ctx.guild.channels, name=channel_name)
        if the_channel is None:
            return await ctx.send("**Error:** Channel not found!")
        
        if dir.lower() == "out":
            await the_channel.set_permissions(ctx.message.author, read_messages=False)
            log("Channel opt out", ctx.message.author, the_channel, None, None)
            await ctx.send("You have opted out of channel {}\nCAUTION: You may see discussions you find offensive. Server rules still apply.".format(channel_name))
        elif dir.lower() == "in":
            await the_channel.set_permissions(ctx.message.author, overwrite=None)
            log("Channel opt in", ctx.message.author, the_channel, None, None)
            await ctx.send("You have opted back in to channel {}".format(channel_name))
        else:
            await ctx.send("**Error:** Proper usage is .opt in/out channelname")
            
    @commands.command()
    async def minesweeper(self, ctx, row=10, collumn=10, mines=10):
        if mines > row*collumn*.8:
            return await ctx.send("**Error:** Too many mines")
        
        if not -1<row<101 or not -1<collumn<101:
            return await ctx.send("**Error:** Row/collumn out of range")
        
        board = [ [ 0 for i in range(collumn) ] for j in range(row) ]

        for mine in range(0,mines):
            blocked = True
            while blocked == True:
                the_row = random.randint(0, row-1)
                the_collumn = random.randint(0, collumn-1)
                if board[the_row][the_collumn]!=9:
                    blocked = False
            board[the_row][the_collumn] = 9
            for i in [-1,0,1]:
                for j in [-1,0,1]:
                    s_row = the_row + i
                    s_collumn = the_collumn + j
                    if (i !=0 or j != 0) and s_row > -1 and s_collumn > -1 and s_row < row and s_collumn < collumn and board[s_row][s_collumn] != 9:
                        board[s_row][s_collumn] = board[s_row][s_collumn] + 1

        message = ""
        for row in board:
            for collumn in row:
                message = "{0}||:{1}:||".format(message, numbers[collumn])
            message = "{0}\n".format(message)

        if len(message) > 2000:
            return await ctx.send("**Error:** Minesweeper board exceeds discord's native message cap")
        
        await ctx.send(message[:-1])
            