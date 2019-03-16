import discord
from discord.ext import commands

class Role(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.good_roles = self.read_role_arc()
        self.good_roles.sort()

    def write_role_arc(self):
        good_roles_arc = open("goodRoles.txt", "w")
        for a_good_role in self.good_roles:
            good_roles_arc.write("{0}\n".format(a_good_role))
        good_roles_arc.close()
        print("updated self.good_roles file")

    def read_role_arc(self):
        good_roles_arc = open("goodRoles.txt", "r")
        good_roles = []
        for line in good_roles_arc:
            good_roles.append(line[:-1])
        good_roles_arc.close()
        return good_roles

    def merge_strings(self, string_array):
        result = ""
        for segment in string_array:
            result = "{0}{1} ".format(result, segment)
        return result[:-1]

    @commands.command()
    async def addrole(self, ctx, *args_role: str):
        """Adds a role to a user"""
        if ctx.message.channel.name != "bot-commands":
            return await ctx.send("**Error:** Role commands are only available in #bot-commands")

        the_role = self.merge_strings(args_role)
        if discord.utils.get(ctx.message.guild.roles, name=the_role) is None:
            await ctx.send("**Error:** That role does not exist!".format(the_role))
        else:
            has_role = False
            for role in ctx.message.author.roles:
                if role.name == the_role:
                    has_role = True
            if has_role:
                await ctx.send("**Error:** You already have that role!")
            else:
                is_good_role = False
                for a_good_role in self.good_roles:
                    if the_role == a_good_role:
                        is_good_role = True
                if is_good_role:
                    await ctx.message.author.add_roles(discord.utils.get(ctx.message.guild.roles, name=the_role))
                    await ctx.send("Added role")
                else:
                    await ctx.send("**Error:** You aren't allowed to give yourself that role!")

    @commands.command()
    async def delrole(self, ctx, *args_role: str):
        """Removes a role from a user"""
        if ctx.message.channel.name != "bot-commands":
            return await ctx.send("**Error:** Role commands are only available in #bot-commands")

        the_role = self.merge_strings(args_role)
        if discord.utils.get(ctx.message.guild.roles, name=the_role) is None:
            await ctx.send("**Error:** That role does not exist!".format(the_role))
        else:
            has_role = False
            for role in ctx.message.author.roles:
                if role.name == the_role:
                    has_role = True
            if has_role:
                is_good_role = False
                for a_good_role in self.good_roles:
                    if the_role == a_good_role:
                        is_good_role = True
                if is_good_role:
                    await ctx.message.author.remove_roles(discord.utils.get(ctx.message.guild.roles, name=the_role))
                    await ctx.send("Removed role")
                else:
                    await ctx.send("**Error:** You aren't allowed to to remove that role from yourself!")
            else:
                await ctx.send("**Error:** You don't have that role!")

    @commands.command()
    async def editrole(self, ctx, edit, *args_role: str):
        """Creates/deletes a pingable role for the server [MOD ONLY]"""
        if ctx.message.channel.name != "bot-commands":
            return await ctx.send("**Error:** Role commands are only available in #bot-commands")

        the_role = self.merge_strings(args_role)
        is_mod = False
        for role in ctx.message.author.roles:
            if role.name == "Bot Mod":
                is_mod = True
        if is_mod:
            if discord.utils.get(ctx.message.guild.roles, name=the_role) is None:
                if edit == "0":
                    await ctx.send("**Error:** That role does not exist!".format(the_role))
                else:
                    await ctx.message.guild.create_role(name=the_role, mentionable=True,
                                                        reason="created by bot by command")
                    await ctx.send("Role has been created")
                    self.good_roles.append(the_role)
                    self.good_roles.sort()
                    self.write_role_arc()
            else:
                if edit == "0":
                    await discord.utils.get(ctx.message.guild.roles, name=the_role).delete(
                        reason="deleted by bot by command")
                    await ctx.send("Role has been deleted")
                    self.good_roles.remove(the_role)
                    self.write_role_arc()
                else:
                    await ctx.send("**Error:** Role already exists!")
        else:
            await ctx.send("**Error:** You are not allowed to create a role!")

    @commands.command()
    async def rolelist(self, ctx):
        """Displays the list of roles that you can add to yourself"""
        if ctx.message.channel.name != "bot-commands":
            return await ctx.send("**Error:** Role commands are only available in #bot-commands")

        message = "```"
        for a_good_role in self.good_roles:
            message = message + a_good_role + "\n"
        message = message + "```"
        await ctx.send(message)
