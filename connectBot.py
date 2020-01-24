import discord
from discord.ext import commands
import sqlite3
import random
import time
import asyncio
import copy

pos_dir = [[1,0],[0,1],[1,1],[1,-1]]

version = 3

def is_int(s):
    try: 
        int(s)
        return True
    except ValueError:
        return False

class Connect(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.challenged = None
        self.challenger = None
        self.game = None
        self.isbotgame = False
        self.channel = None
        self.botturn = 1
        self.timeout = self.bot.loop.create_task(self.check_timeout())
        
    async def begin_game(self):
        players = [self.challenged, self.challenger]
        random.shuffle(players)
        if self.isbotgame:
            if self.bot.user.id == players[0]:
                self.botturn = 1
            else:
                self.botturn = 2
        self.game = {
            "First": players[0],
            "Second": players[1],
            "Board": [ [ 0 for i in range(6) ] for j in range(7) ],
            "Winstate": -1,
            "Turn": 1,
            "Lastmove": time.time()
        }
        await self.channel.send("<@{}> will go first and is blue".format(players[0]))
        self.challenged = None
        self.challenger = None
        
    async def display_board(self):
        rot_board = zip(*self.game['Board'])
        msg = ""
        for i in range(7):
            msg = "{0}{1}\U000020e3".format(msg, i + 1)
        msg = "{}\n".format(msg)
        for row in rot_board:
            for item in row:
                if item == 0:
                    msg = "{}⚫".format(msg)
                if item == 1:
                    msg = "{}🔵".format(msg)
                if item == 2:
                    msg = "{}🔴".format(msg)
            msg = "{}\n".format(msg)
        await self.channel.send(msg[:-1])
    
    def winstate_check(self, choice, height):
        if height == 0:
            blocked = True
            for i in range(7):
                if self.game['Board'][i][0] == 0:
                    blocked = False
            if blocked:
                self.game['Winstate'] = 0
        
        if self.win_detect(self.game['Board'], self.game['Turn'] ,choice, height) >= 3:
            self.game['Winstate'] = self.game['Turn']
    
    def win_detect(self, board, turn, choice, height):
        max_score = 0
        for sdir in pos_dir:
            pdist = 0
            ndist = 0
            pend_reached = False
            while not pend_reached:
                pdist = pdist + 1
                mod_choice = choice + sdir[0]*pdist
                mod_height = height + sdir[1]*pdist
                try:
                    if board[mod_choice][mod_height] != turn or mod_choice<0 or mod_height<0:
                        pend_reached = True
                except:
                    pend_reached = True
            pdist = pdist - 1
            nend_reached = False
            while not nend_reached:
                ndist = ndist + 1
                mod_choice = choice - sdir[0]*ndist
                mod_height = height - sdir[1]*ndist
                try:
                    if board[mod_choice][mod_height] != turn or mod_choice<0 or mod_height<0:
                        nend_reached = True
                except:
                    nend_reached = True
            ndist = ndist - 1
            
            if pdist + ndist > max_score:
                max_score = pdist + ndist
        return max_score
        
    async def win_announce(self):
        if self.game is not None:
            if self.game['Winstate'] != -1:
                if self.game['Winstate'] == 0:
                    await self.channel.send("Game over, Tie!")
                elif self.game['Winstate'] == 1:
                    await self.channel.send("Game over, <@{}> won!".format(self.game['First']))
                else:
                    await self.channel.send("Game over, <@{}> won!".format(self.game['Second']))
                        
                self.game = None
                self.isbotgame = False

    @commands.command()
    async def c(self, ctx, *args):
        if (ctx.message.channel.name != "bot-commands"):
            return await ctx.send("**Error:** This command is only available in #bot-commands")
            
        if args[0].lower() == "challenge":
            if self.challenger is not None and self.challenger != ctx.message.author.id:
                return await ctx.send("**Error:** There is already a pending challenge!")
            try:
                self.challenged = ctx.message.mentions[0].id
                self.challenger = ctx.message.author.id
            except:
                return await ctx.send("**Error:** Please mention a user to challenge!")
                
            self.channel = ctx.channel
            
            if self.challenged == self.bot.user.id:
                self.isbotgame = True
                await ctx.send("I accept the challenge! The game will now begin!")
                await self.begin_game()
                await self.display_board()
            else:
                await ctx.send("Awaiting response from opponent! (Use the command '.c accept')")
                await asyncio.sleep(60)
                if self.game is None:
                    self.challenged = None
                    self.challenger = None
                
        if args[0].lower() == "accept":
            if ctx.message.author.id == self.challenged:
                await ctx.send("The game will now begin!")
                await self.begin_game()
                await self.display_board()
            else:
                return await ctx.send("**Error:** You are not being challenged right now")
                
        if is_int(args[0]):
            if self.game is None:
                return await ctx.send("**Error:** There is not an ongoing game")
            
            if self.game['Turn'] == 1:
                if self.game['First'] != ctx.message.author.id:
                    return await ctx.send("**Error:** It is not your turn")
            else:
                if self.game['Second'] != ctx.message.author.id:
                    return await ctx.send("**Error:** It is not your turn")
            
            choice = int(args[0]) - 1
            
            if choice < 0 or choice > 6:
                return await ctx.send("**Error:** Invalid move!")
            
            height = 6
            placed = False
            while not placed and height > 0:
                height = height - 1
                if self.game['Board'][choice][height] == 0:
                    self.game['Board'][choice][height] = self.game['Turn']
                    placed = True
            if not placed:
                return await ctx.send("**Error:** Invalid move!")
                
            self.winstate_check(choice, height)
            await self.display_board()
            
            self.game['Lastmove'] = time.time()
                
            if self.game['Turn'] == 1:
                self.game['Turn'] = 2
            else:
                self.game['Turn'] = 1
                
        if args[0].lower() == 'conceed':
            if self.game is None:
                return await ctx.send("**Error:** There is not an ongoing game")
            if self.game['First'] == ctx.message.author.id:
                self.game['Winstate'] = 2
            elif self.game['Second'] == ctx.message.author.id:
                self.game['Winstate'] = 1
            else:
                await ctx.send("**Error:** You are not a player")
                
        
        if self.isbotgame:
            if self.game['Turn'] == self.botturn and self.game['Winstate'] == -1:
                async with ctx.message.channel.typing():
                    op_turn = 1
                    if self.botturn == 1:
                        op_turn = 2
                    
                    best_options = []
                    best_score = -10000
                    for choice in range(7):
                        future_board = copy.deepcopy(self.game['Board'])
                        height = 6
                        placed = False
                        while not placed and height > 0:
                            height = height - 1
                            if future_board[choice][height] == 0:
                                future_board[choice][height] = self.botturn
                                placed = True
                        if placed:
                            score = self.win_detect(future_board, self.botturn, choice, height)
                            if score >= 3:
                                score = 10000
                            
                            for p_choice in range(7):
                                p_height = 6
                                p_placed = False
                                while not p_placed and p_height > 0:
                                    p_height = p_height - 1
                                    if future_board[p_choice][p_height] == 0:
                                        p_placed = True
                                if p_placed:
                                    if self.win_detect(future_board, op_turn, p_choice, p_height) >= 3:
                                        score = score - 100
                            if score > best_score:
                                best_score = score
                                best_options = [[choice,height]]
                            elif score == best_score:
                                best_options.append([choice,height])
                        
                    choice, height = random.choice(best_options)
                    await asyncio.sleep(1)
                
                await ctx.send("I choose {}".format(choice + 1))
                
                self.game['Board'][choice][height] = self.botturn
                
                self.winstate_check(choice, height)
                await self.display_board()
                
                if self.game['Turn'] == 1:
                    self.game['Turn'] = 2
                else:
                    self.game['Turn'] = 1
        
        await self.win_announce()

    async def check_timeout(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            if self.game is not None:
                if time.time() > self.game['Lastmove'] + 300:
                    if self.game['Turn'] == 1:
                        self.game['Winstate'] = 2
                        await self.channel.send("Game conceeded by <@{}> due to inactivity".format(self.game['First']))
                    else:
                        self.game['Winstate'] = 1
                        await self.channel.send("Game conceeded by <@{}> due to inactivity".format(self.game['Second']))
                    await self.win_announce()
                    
            await asyncio.sleep(60)