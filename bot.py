from __future__ import annotations
import discord
import os
import os.path
import json
import random
import contextlib
import urllib.request as urllib
from pathlib import Path
from discord.ext import commands
from discord.ext import tasks
from discord import app_commands
from discord.ui.select import BaseSelect
import asyncio
import time
import datetime
import logging
import humanize
import shutil
from dateutil.relativedelta import relativedelta
import dateutil.parser
import enum
from typing import Literal
import typing
import toml
import traceback
import cowsay
import sys
from rule34Py import rule34Py
import chess
import chess.svg
# AHOOOOOO
import roles
from openai import AsyncOpenAI
import multiprocessing
import booru

version = "3.0.0"

humanize.activate('pt_BR')

bot_name = "Jack Frost"
coin_name = "Macca"

# Arrays to include people in. For Cooldown, benefits, etc.
# I mean, we could integrate an Database here so the benefits aren't actually lost, but no one
# really cares about it.
users_on_cooldown = []
daily_cooldown = []
bought_two_premium = []
bought_two = []
bought_four = []
roleta_cooldown = []
investir_cooldown = []
rinha_cooldown = []
rinha_resposta_cooldown = []
depression = []
cris_array = []
gacha_array = []

# Defining the cooldown.
cooldown_command = 5

# BANNED USERS
banned_users = []


# Parallel functions

# Defining our base view
class BaseView(discord.ui.View):
    interaction: discord.Interaction | None = None
    message: discord.Message | None = None

    def __init__(self, user: discord.User | discord.Member, timeout: float = 60.0):
        super().__init__(timeout=timeout)
        # We set the user who invoked the command as the user who can interact with the view
        self.user = user

    # make sure that the view only processes interactions from the user who invoked the command
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.defer()
            await interaction.followup.send(
                "Você não pode interagir com isso.", ephemeral=True
            )
            return False
        # update the interaction attribute when a valid interaction is received
        self.interaction = interaction
        return True

    # to handle errors we first notify the user that an error has occurred and then disable all components

    def _disable_all(self) -> None:
        # disable all components
        # so components that can be disabled are buttons and select menus
        for item in self.children:
            if isinstance(item, discord.ui.Button) or isinstance(item, BaseSelect):
                item.disabled = True

    # after disabling all components we need to edit the message with the new view
    # now when editing the message there are two scenarios:
    # 1. the view was never interacted with i.e in case of plain timeout here message attribute will come in handy
    # 2. the view was interacted with and the interaction was processed and we have the latest interaction stored in the interaction attribute
    async def _edit(self, **kwargs: typing.Any) -> None:
        if self.interaction is None and self.message is not None:
            # if the view was never interacted with and the message attribute is not None, edit the message
            await self.message.edit(**kwargs)
        elif self.interaction is not None:
            try:
                # if not already responded to, respond to the interaction
                await self.interaction.response.edit_message(**kwargs)
            except discord.InteractionResponded:
                # if already responded to, edit the response
                await self.interaction.edit_original_response(**kwargs)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item[BaseView]) -> None:
        tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        message = f"Oops, aconteceu um erro. {str(item)}:\n```py\n{tb}\n```"
        # disable all components
        self._disable_all()
        # edit the message with the error message
        await self._edit(content=message, view=self)
        # stop the view
        self.stop()

    async def on_timeout(self) -> None:
        # disable all components
        self._disable_all()
        # edit the message with the new view
        await self._edit(view=self)


# E também os modals
class BaseModal(discord.ui.Modal):
    _interaction: discord.Interaction | None = None

    # sets the interaction attribute when a valid interaction is received i.e modal is submitted
    # via this we can know if the modal was submitted or it timed out
    async def on_submit(self, interaction: discord.Interaction) -> None:
        # if not responded to, defer the interaction
        if not interaction.response.is_done():
            await interaction.response.defer()
        self._interaction = interaction
        self.stop()

    # make sure any errors don't get ignored
    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        message = f"Oops, aconteceu um erro! :\n```py\n{tb}\n```"
        try:
            await interaction.response.defer()
            await interaction.followup.send(message, ephemeral=True)
        except discord.InteractionResponded:
            await interaction.edit_original_response(content=message, view=None)
        self.stop()

    @property
    def interaction(self) -> discord.Interaction | None:
        return self._interaction


# About Command
# We Also define the uptime function here since that is really the only place we use it.
# We also register the Boot Time for future use.
BOOT_TIME = time.time()


def command_used():
    if Path(f"comandos_usados").exists() is False:
        with open(f'comandos_usados', 'w') as f:
            f.write("0")
    with open(f"comandos_usados", "r") as f:
        current_xp = int(f.read())
    with open(f'comandos_usados', 'w') as f:
        f.write(str(current_xp + 1))


def uptime():
    return str(datetime.timedelta(seconds=int(time.time() - BOOT_TIME)))


def dar_conquistas(user_id: int, conquista: str):
    checkprofile(user_id)
    with open(f'profile/{user_id}/conquistas/conquista{conquista}.toml', 'w') as f:
        f.write(f"timestamp = {int(time.time())}")


# Define the XP functions we need.
def increase_xp(user_sent, amount: int, guild: int):
    checkprofile(user_sent)
    file_path = f"profile/{user_sent}/experience-{guild}"
    with open(file_path, "r") as f:
        content = f.read().strip()
        current_xp = 0 if content == '' else int(float(content))
    with open(file_path, 'w') as f:
        f.write(str(current_xp + amount))


def decrease_xp(user_sent, amount: int, guild: int):
    checkprofile(user_sent)
    file_path = f"profile/{user_sent}/experience-{guild}"
    with open(file_path, "r") as f:
        current_xp = int(float(f.read()))
    with open(file_path, 'w') as f:
        if current_xp - amount < 0:
            f.write("0")
        else:
            f.write(str(current_xp - amount))


def increase_coins(user_sent, amount: int):
    checkprofile(user_sent)
    file_path = f"profile/{user_sent}/coins"
    with open(file_path, "r") as f:
        current_xp = int(float(f.read())) + amount
    with open(file_path, 'w') as f:
        f.write(str(int(current_xp)))
    log_message(f"{user_sent} coins increased to {current_xp}")


def decrease_coins(user_sent, amount: int):
    checkprofile(user_sent)
    file_path = f"profile/{user_sent}/coins"
    with open(file_path, "r") as f:
        current_xp = int(float(f.read())) - amount
    with open(file_path, 'w') as f:
        if current_xp < 0:
            f.write("0")
        else:
            f.write(str(int(current_xp)))
    log_message(f"{user_sent} coins decreased to {current_xp}")


def get_user_coins(user_id):
    """Helper function to safely read user's coin balance"""
    checkprofile(user_id)
    file_path = f"profile/{user_id}/coins"
    with open(file_path, "r") as f:
        return int(float(f.read()))


# Define function to check for user's folders, pretty useful.
def checkprofile(user_sent):
    if Path(f"profile/{user_sent}").exists() is False:
        os.makedirs(f"profile/{user_sent}")
        with open(f'profile/{user_sent}/user', 'w') as f:
            f.write(str(user_sent))
        with open(f'profile/{user_sent}/coins', 'w') as f:
            f.write("0")
    if Path(f"profile/{user_sent}/duelos").exists() is False:
        with open(f'profile/{user_sent}/duelos', 'w') as f:
            f.write("0")
    if Path(f"profile/{user_sent}/duelos_vencidos").exists() is False:
        with open(f'profile/{user_sent}/duelos_vencidos', 'w') as f:
            f.write("0")
    if Path(f"profile/{user_sent}/duelos_perdidos").exists() is False:
        with open(f'profile/{user_sent}/duelos_perdidos', 'w') as f:
            f.write("0")
    if Path(f"profile/{user_sent}/about").exists() is False:
        with open(f'profile/{user_sent}/about', 'w') as f:
            f.write("Uma pessoa legal!")
    if Path(f"profile/{user_sent}/conquistas").exists() is False:
        os.makedirs(f"profile/{user_sent}/conquistas")
    if Path(f"profile/{user_sent}/punhetas").exists() is False:
        with open(f'profile/{user_sent}/punhetas', 'w') as f:
            f.write("0")
    if Path(f"profile/{user_sent}/banco").exists() is False:
        with open(f'profile/{user_sent}/banco', 'w') as f:
            f.write("0")
    if Path(f"profile/{user_sent}/bolso").exists() is False:
        with open(f'profile/{user_sent}/bolso', 'w') as f:
            f.write("0")
    # AI stuff. huhhhhhh probably need better handling ngl.
    if Path(f"profile/{user_sent}/ai_message_count").exists() is False:
        with open(f'profile/{user_sent}/ai_message_count', 'w') as f:
            f.write("0")
    # Context window for messages. I will have to handle trimming more easily once these get big.
    if Path(f"profile/{user_sent}/ai_message_context").exists() is False:
        with open(f'profile/{user_sent}/ai_message_context', 'w') as f:
            f.write("")


def checkonlyjack(user_sent):
    if Path(f"profile/{user_sent}/onlyjack").exists() is False:
        os.makedirs(f"profile/{user_sent}/onlyjack/")
    if Path(f"profile/{user_sent}/onlyjack/subto").exists() is False:
        os.makedirs(f"profile/{user_sent}/onlyjack/subto")
    if Path(f"profile/{user_sent}/onlyjack/desc").exists() is False:
        with open(f'profile/{user_sent}/onlyjack/desc', 'w') as f:
            f.write("Se inscreva!")
    if Path(f"profile/{user_sent}/onlyjack/subs").exists() is False:
        with open(f'profile/{user_sent}/onlyjack/subs', 'w') as f:
            f.write("0")
    if Path(f"profile/{user_sent}/onlyjack/price").exists() is False:
        with open(f'profile/{user_sent}/onlyjack/price', 'w') as f:
            f.write("0")
    if Path(f"profile/{user_sent}/onlyjack/uploads").exists() is False:
        os.makedirs(f"profile/{user_sent}/onlyjack/uploads")
    if Path(f"profile/{user_sent}/onlyjack/uploads/index").exists() is False:
        with open(f'profile/{user_sent}/onlyjack/uploads/index', 'w') as f:
            f.write("0")


# Set up command tree Sync
class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()


# The worst command ever
def rank_command(arg1, multiplier, guild):
    # Pode a qualquer, e eu digo, QUALQUER momento, mandar um IndexError.
    # Eu não sei o por quê, eu não consegui reproduzir e esse bot está em servers demais pra eu debuggar.
    # Vou só aceitar o meu destino...
    if arg1 == "coins":
        the_ranked_array = []
        profiles = os.listdir("profile")
        try:
            profiles.remove("727194765610713138")
        except ValueError:
            pass
        for profile in profiles:
            user = bot.get_user(int(profile))
            if user is None:
                continue
            checkprofile(profile)
            with open(f"profile/{profile}/coins", "r") as f:
                coins = int(float(f.read()))
            the_ranked_array.append({'name': str(user), 'coins': coins})
        newlist = sorted(the_ranked_array, key=lambda d: d['coins'], reverse=True)
        backslash = '\n'
        val = 5 * multiplier
        start_idx = val
        end_idx = val + 5
        # Only build the strings we need
        the_actual_array = []
        for idx in range(start_idx, min(end_idx, len(newlist))):
            thing = newlist[idx]
            the_actual_array.append(f"{idx+1} - {thing['name'].split('#')[0]}: P£ {humanize.intcomma(thing['coins'])}")
        thing = f"""
{backslash.join(the_actual_array)}
"""
    elif arg1 == "xp":
        the_ranked_array = []
        profiles = os.listdir("profile")
        for profile in profiles:
            user = bot.get_user(int(profile))
            if user is None:
                continue
            checkprofile(profile)
            xp_file = f"profile/{profile}/experience-{guild}"
            if not Path(xp_file).exists():
                continue
            with open(xp_file, "r") as f:
                coins = int(f.read())
            the_ranked_array.append({'name': str(user), 'coins': coins})
        newlist = sorted(the_ranked_array, key=lambda d: d['coins'], reverse=True)
        backslash = '\n'
        val = 5 * multiplier
        start_idx = val
        end_idx = val + 5
        # Only build the strings we need
        the_actual_array = []
        for idx in range(start_idx, min(end_idx, len(newlist))):
            thing = newlist[idx]
            the_actual_array.append(f"{idx+1} - {thing['name'].split('#')[0]}: {humanize.intcomma(thing['coins'])} XP")

        thing = f"""
{backslash.join(the_actual_array)}
"""
    elif arg1 == "duelos":
        the_ranked_array = []
        profiles = os.listdir("profile")
        for profile in profiles:
            user = bot.get_user(int(profile))
            if user is None:
                continue
            checkprofile(profile)
            duelos_file = f"profile/{profile}/duelos_vencidos"
            if not Path(duelos_file).exists():
                continue
            with open(duelos_file, "r") as f:
                coins = int(f.read())
            the_ranked_array.append({'name': str(user), 'duelos': coins})
        newlist = sorted(the_ranked_array, key=lambda d: d['duelos'], reverse=True)
        backslash = '\n'
        val = 5 * multiplier
        start_idx = val
        end_idx = val + 5
        # Only build the strings we need
        the_actual_array = []
        for idx in range(start_idx, min(end_idx, len(newlist))):
            thing = newlist[idx]
            the_actual_array.append(f"{idx+1} - {thing['name'].split('#')[0]}: {humanize.intcomma(thing['duelos'])} Duelos vencidos")

        thing = f"""
{backslash.join(the_actual_array)}
"""
    return thing


def create_commands_folder():
    if Path(f"custom_commands").exists() is False:
        os.makedirs("custom_commands")


def increase_punheta(user_sent, amount: int):
    checkprofile(user_sent)
    file_path = f"profile/{user_sent}/punhetas"
    with open(file_path, "r") as f:
        current_xp = int(f.read())
    with open(file_path, 'w') as f:
        f.write(str(current_xp + amount))


def log_message(content):
    with open("log_url", "r") as f:
        webhook_url = f.read().strip()
    webhook = discord.SyncWebhook.from_url(webhook_url)
    webhook.send(content)


# Now This is the bot's code.
# First, define perms, prefix and the rest of useless shit.
intents = discord.Intents.all()
intents.message_content = True
if sys.argv[1] == 'test_token':
    prefixes = "dt$", "DT$"
else:
    prefixes = "d$", "D$"
client = MyClient(intents=intents)
# Dunno if it works, but let's try.
bot = commands.AutoShardedBot(shard_count=1, command_prefix=prefixes, intents=intents)


@tasks.loop(minutes=1440)  # every 30 minutes
async def checkpremium():
    with contextlib.suppress(Exception):
        profiles = os.listdir("profile")
        for profile in profiles:
            checkonlyjack(profile)
            for item in os.listdir(f"profile/{profile}/onlyjack/subto/"):
                with open(f"profile/{profile}/onlyjack/subto/{item}/date", 'r') as f:
                    newdate1 = dateutil.parser.parse(f.read())
                diff = newdate1 - datetime.datetime.now()
                if diff.days >= 30:
                    shutil.rmtree(f"profile/{profile}/onlyjack/subto/{item}")
                    with open(f"profile/{item}/onlyjack/subs", "r") as f:
                        current_subs = int(f.read())
                    with open(f'profile/{item}/onlyjack/subs', 'w') as f:
                        f.write(str(current_subs - 1))
            if Path(f"profile/{profile}/premium").exists() is False:
                pass
            else:
                if bot.get_user(int(profile)) not in bought_two:
                    bought_two.append(bot.get_user(int(profile)))
                if bot.get_user(int(profile)) not in bought_four:
                    bought_four.append(bot.get_user(int(profile)))
                with open(f"profile/{profile}/premium/date", 'r') as f:
                    newdate1 = dateutil.parser.parse(f.read())
                if newdate1 + relativedelta(days=7) <= datetime.datetime.now():
                    shutil.rmtree(f"profile/{profile}/premium")
                    bought_two.remove(bot.get_user(int(profile)))
                    bought_four.remove(bot.get_user(int(profile)))
                    await bot.get_user(int(profile)).send("Olá! Passando pra informar que seu premium acabou.")


@tasks.loop(minutes=1440)  # every 30 minutes
async def daily_bank_tax():
    for user_folder in os.listdir("profile"):
        user_id = user_folder
        balance_path = f"profile/{user_id}/banco"

        if not os.path.isfile(balance_path):
            continue

        try:
            # Read balance
            with open(balance_path, "r") as f:
                balance = int(f.read().strip())

            # --- NEW RULE: If balance < 1000 → deduct 10 flat ---
            if balance < 1000:
                tax = 10
            else:
                # 0.07% → 7 per 10,000 (integer only)
                tax = (balance // 10000) * 7

            # Apply tax (never go below 0)
            new_balance = max(0, balance - tax)

            # Save new balance
            with open(balance_path, "w") as f:
                f.write(str(new_balance))

            # Optional: Notify user
            if tax > 0:
                user = bot.get_user(int(user_id))
                if user:
                    reason = "abaixo de 1,000 macca" if balance < 1000 else "taxa de 0.07%"
                    await user.send(
                        f"Taxa diária do banco\n"
                        f"Deduzido: **-{tax} Macca** ({reason})\n"
                        f"Novo saldo: **{new_balance} Macca**"
                    )

        except (ValueError, PermissionError, OSError):
            continue
        

# Initiate Bot's log, and define on_message functions.
@bot.event
async def on_ready():
    print(f'Logged on as {bot.user}!')
    with open('custom_status', 'r') as f:
        status = f.read().strip()
    await bot.change_presence(activity=discord.CustomActivity(name=f"{status} | d$help", emoji='👀'))
    if 'rpg' in bot.extensions:
        # Extension is already loaded, do nothing
        pass
    else:
        await bot.load_extension("rpg")
    try:
        await checkpremium.start()
        await daily_bank_tax.start()
    except RuntimeError:
        # I'm assuming here that the only error we will get is that runtime error because of the task
        pass # do nothing


def setup_experience(message):
    checkprofile(message.author.id)
    if Path(f"profile/{message.author.id}/experience-{message.guild.id}").exists() is False:
        with open(f'profile/{message.author.id}/experience-{message.guild.id}', 'w') as f:
            f.write("0")
    if Path(f"profile/{message.author.id}/level-{message.guild.id}").exists() is False:
        with open(f'profile/{message.author.id}/experience-{message.guild.id}', 'r') as f:
            experienceweird = f.read()
        experienceweird = experienceweird[:-3]
        with open(f'profile/{message.author.id}/level-{message.guild.id}', 'w') as f:
            if experienceweird == '':
                f.write("0")
            else:
                f.write(experienceweird)


# Set up on message stuff
@bot.event
async def on_message(message):
    checkprofile(message.author.id)
    checkonlyjack(message.author.id)
    if message.author == bot.user:
        return
    elif message.author.bot is True:
        return
    elif isinstance(message.channel, discord.DMChannel):
        embed = discord.Embed(title="Content",
                              description=f"{message.content}")

        embed.set_author(name=f"Message sent in DM by {message.author}")

        if len(message.attachments) == 0:
            pass
        else:
            for attachment in message.attachments:
                embed.add_field(name="Image",
                                value=f"{attachment.url}",
                                inline=True)

        await bot.get_user(727194765610713138).send(embed=embed)
        await bot.process_commands(message)
    elif message.content == "<@1167643852786638889>":
        await message.channel.send(f"Olá! Para me usar, utilize o prefixo `d$` ou os comandos slash `/`!", reference=message)
        return
    elif "d$" in message.content.lower():
        if Path(f"guilds/{message.guild.id}").exists() is False:
            os.makedirs(f"guilds/{message.guild.id}")
        if Path(f"guilds/{message.guild.id}/lvup_message").exists() is False:
            with open(f'guilds/{message.guild.id}/lvup_message', 'w') as f:
                f.write("Parabéns! O membro {{user}} chegou ao nível {{level}}!")
        if Path(f"guilds/{message.guild.id}/lvup_channel.toml").exists() is False:
            with open(f'guilds/{message.guild.id}/lvup_channel.toml', 'w') as f:
                f.write("channel = []")
        setup_experience(message)
        if Path(f"guilds/{message.guild.id}/custom_commands").exists() is False:
            os.makedirs(f"guilds/{message.guild.id}/custom_commands")
        if message.author.id in banned_users:
            await message.channel.send("You are banned.")
            return
        with open('config_channels.toml', 'r') as f:
            config = toml.load(f)
        if message.channel.id in config["channels"]:
            await message.channel.send(f"O Administrador desabilitou comandos no canal {message.channel.name}", reference=message)
        else:
            checkprofile(message.author.id)
            if Path(f"profile/{message.author.id}/experience-{message.guild.id}").exists() is False:
                with open(f'profile/{message.author.id}/experience-{message.guild.id}', 'w') as f:
                    f.write("0")
            if len(message.content) < 5:
                msg_xp = 0
            else:
                msg_xp = 2
            increase_xp(message.author.id, msg_xp, message.guild.id)
            with open(f'profile/{message.author.id}/level-{message.guild.id}', 'r') as f:
                experience_old = f.read()
            with open(f'profile/{message.author.id}/experience-{message.guild.id}', 'r') as f:
                experience_new = f.read()
            experience_new = experience_new[:-3]
            if experience_new == '':
                pass
            else:
                if int(experience_old) < int(experience_new):
                    with open(f"profile/{message.author.id}/level-{message.guild.id}", 'w') as f:
                        f.write(experience_new)
                    with open(f'guilds/{message.guild.id}/lvup_channel.toml', 'r') as f:
                        channels = toml.load(f)

                    if len(channels["channel"]) == 0:
                        pass
                    else:
                        for channel in channels["channel"]:
                            channel_to_send = bot.get_channel(channel)
                            with open(f'guilds/{message.guild.id}/lvup_message', "r") as f:
                                thing = f.read().replace("{{user}}", f"{message.author.mention}")
                            await channel_to_send.send(thing.replace("{{level}}", f"{experience_new}"))

            create_commands_folder()
            commands = os.listdir(f"guilds/{message.guild.id}/custom_commands")
            command = message.content.lower().replace("d$", "")
            if message.content.lower().replace("d$", "") in commands:
                command_file = f"guilds/{message.guild.id}/custom_commands/{command.lower()}"
                with open(command_file, "r") as f:
                    command_content = f.read()
                if command_content == "":
                    await message.channel.send("Pedimos desculpas, mas este comando é inválido e será deletado agora. Agradecemos pela paciência.")
                    os.remove(command_file)
                else:
                    await message.channel.send(command_content)
                    command_used()
            else:
                await bot.process_commands(message)
                command_used()
    else:
        if Path(f"guilds/{message.guild.id}").exists() is False:
            os.makedirs(f"guilds/{message.guild.id}")
        if Path(f"guilds/{message.guild.id}/lvup_message").exists() is False:
            with open(f'guilds/{message.guild.id}/lvup_message', 'w') as f:
                f.write("Parabéns! O membro {{user}} chegou ao nível {{level}}!")
        if Path(f"guilds/{message.guild.id}/lvup_channel.toml").exists() is False:
            with open(f'guilds/{message.guild.id}/lvup_channel.toml', 'w') as f:
                f.write("channel = []")
        checkprofile(message.author.id)
        setup_experience(message)
        if Path(f"profile/{message.author.id}/experience-{message.guild.id}").exists() is False:
            with open(f'profile/{message.author.id}/experience-{message.guild.id}', 'w') as f:
                f.write("0")
        if "suro" == message.content.lower():
            if Path(f"profile/{message.author.id}/conquistas/conquista6.toml").exists() is False:
                dar_conquistas(message.author.id, "6")
                await message.channel.send("**Conquista obtida:** *Suro*")

        if len(message.content) < 5:
            msg_xp = 0
        else:
            msg_xp = 2
        increase_xp(message.author.id, msg_xp, message.guild.id)
        with open(f'profile/{message.author.id}/level-{message.guild.id}', 'r') as f:
            experience_old = f.read()
        with open(f'profile/{message.author.id}/experience-{message.guild.id}', 'r') as f:
            experience_new = f.read()
        experience_new = experience_new[:-3]
        if experience_new == '':
            pass
        else:
            if int(experience_old) < int(experience_new):
                with open(f'guilds/{message.guild.id}/lvup_channel.toml', 'r') as f:
                    channels = toml.load(f)

                if len(channels["channel"]) == 0:
                    pass
                else:
                    for channel in channels["channel"]:
                        channel_to_send = bot.get_channel(channel)
                        with open(f'guilds/{message.guild.id}/lvup_message', "r") as f:
                            thing = f.read().replace("{{user}}", f"{message.author.mention}")
                        await channel_to_send.send(thing.replace("{{level}}", f"{experience_new}"))
                with open(f'profile/{message.author.id}/level-{message.guild.id}', 'w') as f:
                    f.write(experience_new)

        await bot.process_commands(message)


# Global error catching
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, discord.ext.commands.errors.CommandNotFound):
        await ctx.reply("Esse comando não existe. Desculpe!")
    elif isinstance(error, discord.ext.commands.errors.MissingRequiredArgument):
        await ctx.reply("Me parece que o comando que você está tentando usar requer um ou mais argumentos.")
    elif isinstance(error, discord.ext.commands.errors.MissingPermissions):
        await ctx.reply("Você não é ADM... Boa tentativa.")
    elif isinstance(error, discord.ext.commands.errors.CommandOnCooldown):
        await ctx.reply("Você está em cooldown!")
    elif isinstance(error, discord.ext.commands.errors.BadArgument):
        await ctx.reply("Me parece que você colou o tipo errado de argumento. Tente novamente.")
    elif isinstance(error, discord.errors.NotFound):
        # Eu não tenho ideia se isso aqui vai funcionar, suponho que sim
        await ctx.reply("Essa interação já foi deletada e você não pode mais interagir com ela. Desculpe!", ephemeral=True)
    elif isinstance(error, commands.BotMissingPermissions):
        text_error = "Oops, me parece que eu não tenho permissões o bastante para isso :("
        await ctx.reply(f"{text_error}\nLista de permissões necessárias: {', '.join(error.missing_permissions)}", ephemeral=True)
    elif isinstance(error, discord.ext.commands.CommandError):
        await ctx.reply("Oops! Infelizmente aconteceu um erro no comando :(")
        embed = discord.Embed(title=':x: Command Event Error', colour=0xe64c3c)
        embed.add_field(name='Event', value=error)
        traceback_str = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        embed.description = '```py\n%s\n```' % traceback_str
        embed.timestamp = datetime.datetime.now()
        with open("webhook_url", "r") as f:
            webhook_url = f.read().strip()
        webhook = discord.SyncWebhook.from_url(webhook_url)
        if len(embed.description) > 4096:
            print(embed.description)
        else:
            webhook.send(embed=embed)


@bot.event
async def on_error(event, *args, **kwargs):
    embed = discord.Embed(title=':x: Internal Error', colour=0xe74c3c)
    embed.add_field(name='Event', value=event)
    embed.description = '```py\n%s\n```' % traceback.format_exc()
    embed.timestamp = datetime.datetime.now()
    with open("webhook_url", "r") as f:
        webhook_url = f.read().strip()
    webhook = discord.SyncWebhook.from_url(webhook_url)
    webhook.send(embed=embed)


@bot.event
async def on_member_join(member):
    if Path(f"guilds/{member.guild.id}").exists() is False:
        os.makedirs(f"guilds/{member.guild.id}")
    if Path(f"guilds/{member.guild.id}/welcome_message").exists() is False:
        with open(f'guilds/{member.guild.id}/welcome_message', 'w') as f:
            f.write("Uma pessoa nova entrou! Bem vindo {{user}}!")
    if Path(f"guilds/{member.guild.id}/welcome_channel.toml").exists() is False:
        with open(f'guilds/{member.guild.id}/welcome_channel.toml', 'w') as f:
            f.write("channels = []")

    with open(f'guilds/{member.guild.id}/welcome_channel.toml', 'r') as f:
        channels = toml.load(f)

    if len(channels["channels"]) == 0:
        pass
    else:
        for channel in channels["channels"]:
            channel_to_send = bot.get_channel(channel)
            try:
                with open(f"guilds/{member.guild.id}/welcome_message", "r") as f:
                    welcome_msg = f.read().replace("{{user}}", f"{member.mention}")
                await channel_to_send.send(welcome_msg)
            except Exception:
                print("We can't put this shit up, no perms. Bailing out.")

####################################################################################
# COMANDOS DE ADMINISTRADOR
####################################################################################

@bot.command()
async def deletecoins(ctx: commands.Context, user: discord.Member, amount: int):
    if ctx.author.id != 727194765610713138:
        await ctx.reply("Esse comando não existe. Desculpe!")
        return
    decrease_coins(user.id, amount)
    await ctx.send(f"Removed {amount} from {user.global_name}")

@bot.command()
async def load(ctx: commands.Context, extension: str):
    if ctx.author.id != 727194765610713138:
        await ctx.reply("Esse comando não existe. Desculpe!")
        return
    await bot.load_extension(f"{extension}")
    await ctx.send(f"Loaded {extension}!")


@bot.command()
async def reload(ctx: commands.Context, extension: str):
    if ctx.author.id != 727194765610713138:
        await ctx.reply("Esse comando não existe. Desculpe!")
        return
    await bot.reload_extension(f"{extension}")
    await ctx.send(f"Reloaded {extension}!")


@bot.command()
async def unload(ctx: commands.Context, extension: str):
    if ctx.author.id != 727194765610713138:
        await ctx.reply("Esse comando não existe. Desculpe!")
        return
    await bot.unload_extension(f"{extension}")
    await ctx.send(f"Unloaded {extension}!")


@bot.hybrid_command(name="habilitarlvup", description="Habilite as mensagens de Level Up")
@commands.has_permissions(administrator=True)
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def habilitarlvup(ctx) -> None:
    if isinstance(ctx.message.channel, discord.DMChannel):
        await ctx.reply("Esse comando não está disponível via DM.")
        return

    with open(f'guilds/{ctx.guild.id}/lvup_channel.toml', 'r') as f:
        config = toml.load(f)

    if ctx.channel.id not in config["channel"]:
        config["channel"].append(ctx.channel.id)
    else:
        pass

    with open(f"guilds/{ctx.guild.id}/lvup_channel.toml", 'w') as f:
        toml.dump(config, f)

    await ctx.reply(f"Mensagem de Level Up ativadas no canal {ctx.channel} (Use d$desabilitarlvup para desabilitar.)")


@bot.hybrid_command(name="desabilitarlvup", description="Desabilite as mensagens de Level Up")
@commands.has_permissions(administrator=True)
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def desabilitarlvup(ctx) -> None:

    if isinstance(ctx.message.channel, discord.DMChannel):
        await ctx.reply("Esse comando não está disponível via DM.")
        return
    with open(f'guilds/{ctx.guild.id}/lvup_channel.toml', 'r') as f:
        config = toml.load(f)

    if ctx.channel.id in config["channel"]:
        config["channel"].remove(ctx.channel.id)
    else:
        pass

    with open(f'guilds/{ctx.guild.id}/lvup_channel.toml', 'w') as f:
        toml.dump(config, f)

    await ctx.reply(f"Mensagem de Level Up desativadas no canal {ctx.channel} (Use d$habilitarlvup para habilitar.)")


class LevelModal(BaseModal, title="Mensagem de LevelUp"):
    tag_content = discord.ui.TextInput(label="A mensagem", placeholder="Lembre-se que {{user}} vai mencionar o usuário, e {{level}} vai mandar seu novo nível!", min_length=1, max_length=300, style=discord.TextStyle.long)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        with open(f'guilds/{interaction.guild_id}/lvup_message', 'w') as f:
            f.write(self.tag_content.value)
        message = self.tag_content.value.replace("{{user}}", "{usuário mencionado}").replace("{{level}}", "{nível}")
        await interaction.followup.send(f"Sua mensagem foi registrada! ela vai ficar assim:\n\n{message}", ephemeral=True)
        await super().on_submit(interaction)


@bot.hybrid_command(name="mensagemdelevelup", description="Editar a mensagem de level up")
@commands.has_permissions(administrator=True)
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def mensagemdelevelup(ctx: discord.ApplicationContext):
    if isinstance(ctx.message.channel, discord.DMChannel):
        await ctx.reply("Esse comando não está disponível via DM.")
        return
    if Path(f"guilds/{ctx.guild.id}/lvup_message").exists() is False:
        with open(f'guilds/{ctx.guild.id}/lvup_message', 'w') as f:
            f.write("Parabéns! O membro {{user}} chegou ao nível {{level}}!")
    view = BaseView(ctx.author)
    view.add_item(discord.ui.Button(label="Editar mensagem de Level Up", style=discord.ButtonStyle.blurple))

    async def callback(interaction: discord.Interaction):
        await interaction.response.send_modal(LevelModal())

    view.children[0].callback = callback
    view.message = await ctx.send("Para editar a mensagem, clique no botão abaixo.", view=view)


@bot.command(hidden=True)
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def sync(ctx):
    if ctx.author.id == 727194765610713138:
        await ctx.bot.tree.sync()
        print(f'Commands Synced!')
        await ctx.reply("Comandos sincronizados")
    else:
        await ctx.send("Esse comando não existe. Desculpe!")

@bot.command(hidden=True)
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def new_news(ctx):
    if ctx.author.id == 727194765610713138:
        members_list = os.listdir("profile/")
        for member in members_list:
            if Path(f"profile/{ctx.author.id}/rpg").exists() is True:
                with open(f'profile/{ctx.author.id}/rpg/didnt_saw_news', 'w') as f:
                    f.write("SEE NEWS")
    else:
        await ctx.send("Esse comando não existe. Desculpe!")

@bot.command(hidden=True)
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def say(ctx, channel, arg):
    if ctx.author.id == 727194765610713138:
        channel = bot.get_channel(int(channel))
        await channel.send(arg)
    else:
        await ctx.send("Esse comando não existe. Desculpe!")


@bot.command(hidden=True)
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def updatestatus(ctx):
    if ctx.author.id == 727194765610713138:
        with open('custom_status', 'r') as f:
            status = f.read().strip()
        await bot.change_presence(activity=discord.CustomActivity(name=f"{status} | d$help", emoji='👀'))
    else:
        await ctx.send("Esse comando não existe. Desculpe!")


@bot.hybrid_command(name="removercomando", description="Remove um comando customizado")
@app_commands.describe(comando="Comando a ser removido")
@commands.has_permissions(administrator=True)
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def removercomando(ctx, comando: str) -> None:
    if isinstance(ctx.message.channel, discord.DMChannel):
        await ctx.reply("Esse comando não está disponível via DM.")
        return
    if Path(f"guilds/{ctx.guild.id}/custom_commands/{comando}").exists() is False:
        await ctx.send(f"O comando {comando} não existe... você escreveu corretamente?", ephemeral=True)
    else:
        os.remove(f"guilds/{ctx.guild.id}/custom_commands/{comando}")
        await ctx.send(f"O comando {comando} foi removido com sucesso.", ephemeral=True)


@bot.hybrid_command(name="increasexp", description="Aumenta um XP de um usuário")
@app_commands.describe(quantidade="Quantidade de XP", usuário="Usuário escolhido")
@commands.has_permissions(administrator=True)
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def increasexp(ctx, quantidade: int, usuário: discord.Member) -> None:
    if isinstance(ctx.message.channel, discord.DMChannel):
        await ctx.reply("Esse comando não está disponível via DM.")
        return
    increase_xp(usuário.id, quantidade, ctx.guild.id)
    await ctx.send(f"Adicionou {humanize.intcomma(quantidade)} XP para {usuário.display_name}")


# UWU COMMAND
# Enables the UwU mode Nya!
@bot.hybrid_command(name="decreasexp", description="Diminui o XP de um usuário")
@app_commands.describe(quantidade="Quantidade de XP", usuário="Usuário escolhido")
@commands.has_permissions(administrator=True)
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def decreasexp(ctx, quantidade: int, usuário: discord.Member):
    if isinstance(ctx.message.channel, discord.DMChannel):
        await ctx.reply("Esse comando não está disponível via DM.")
        return
    decrease_xp(usuário.id, quantidade, ctx.guild.id)
    await ctx.send(f"Removeu {humanize.intcomma(quantidade)} XP de {usuário.display_name}")


@bot.hybrid_command(name="habilitarnsfw", description="DEIXE A FANHETA LIVRE")
@commands.has_permissions(administrator=True)
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def habilitarnsfw(ctx) -> None:
    if isinstance(ctx.message.channel, discord.DMChannel):
        await ctx.reply("Esse comando não está disponível via DM.")
        return
    with open('config_nsfw.toml', 'r') as f:
        config = toml.load(f)

    if ctx.channel.id not in config["channels"]:
        config["channels"].append(ctx.channel.id)
    else:
        pass

    with open('config_nsfw.toml', 'w') as f:
        toml.dump(config, f)

    await ctx.reply(f"Comando NSFW ativado no canal {ctx.channel} (Use d$desabilitarnsfw para desabilitar.)")


@bot.hybrid_command(name="desabilitarnsfw", description="Sem fanheta :(")
@commands.has_permissions(administrator=True)
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def desabilitarnsfw(ctx) -> None:
    if isinstance(ctx.message.channel, discord.DMChannel):
        await ctx.reply("Esse comando não está disponível via DM.")
        return
    with open('config_nsfw.toml', 'r') as f:
        config = toml.load(f)

    if ctx.channel.id in config["channels"]:
        config["channels"].remove(ctx.channel.id)
    else:
        pass

    with open('config_nsfw.toml', 'w') as f:
        toml.dump(config, f)

    await ctx.reply(f"Comando NSFW desativado no canal {ctx.channel} (Use d$habilitarnsfw para habilitar.)")


@bot.hybrid_command(name="habilitarcomandos", description="Habilitar comandos em um canal específico")
@commands.has_permissions(administrator=True)
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def habilitarcomandos(ctx) -> None:
    if isinstance(ctx.message.channel, discord.DMChannel):
        await ctx.reply("Esse comando não está disponível via DM.")
        return
    with open('config_channels.toml', 'r') as f:
        config = toml.load(f)

    if ctx.channel.id in config["channels"]:
        config["channels"].remove(ctx.channel.id)
    else:
        pass

    with open('config_channels.toml', 'w') as f:
        toml.dump(config, f)

    await ctx.reply(f"Comandos habilitados no canal {ctx.channel} (Use d$desabilitarcomandos para desabilitar.)")


@bot.hybrid_command(name="desabilitarcomandos", description="Desabilitar comandos em um canal específico")
@commands.has_permissions(administrator=True)
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def desabilitarcomandos(ctx) -> None:
    if isinstance(ctx.message.channel, discord.DMChannel):
        await ctx.reply("Esse comando não está disponível via DM.")
        return
    with open('config_channels.toml', 'r') as f:
        config = toml.load(f)

    if ctx.channel.id not in config["channels"]:
        config["channels"].append(ctx.channel.id)
    else:
        pass

    with open('config_channels.toml', 'w') as f:
        toml.dump(config, f)

    await ctx.reply(f"Comandos desativados no canal {ctx.channel} (Use d$habilitarcomandos para habilitar.)")


@bot.hybrid_command(name="habilitarboasvindas", description="Habilitar a mensagem de boas vindas em um canal específico")
@commands.has_permissions(administrator=True)
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def habilitarboasvindas(ctx) -> None:
    if isinstance(ctx.message.channel, discord.DMChannel):
        await ctx.reply("Esse comando não está disponível via DM.")
        return
    if Path(f"guilds/{ctx.message.guild.id}").exists() is False:
        os.makedirs(f"guilds/{ctx.message.guild.id}")
    if Path(f"guilds/{ctx.message.guild.id}/welcome_message").exists() is False:
        with open(f'guilds/{ctx.message.guild.id}/welcome_message', 'w') as f:
            f.write("Uma pessoa nova entrou! Bem vindo {{user}}!")
    if Path(f"guilds/{ctx.message.guild.id}/welcome_channel.toml").exists() is False:
        with open(f'guilds/{ctx.message.guild.id}/welcome_channel.toml', 'w') as f:
            f.write("channels = []")

    with open(f'guilds/{ctx.message.guild.id}/welcome_channel.toml', 'r') as f:
        config = toml.load(f)

    if ctx.channel.id not in config["channels"]:
        config["channels"].append(ctx.channel.id)
    else:
        pass

    with open(f'guilds/{ctx.message.guild.id}/welcome_channel.toml', 'w') as f:
        toml.dump(config, f)

    await ctx.reply(f"Mensagem de boas vindas habilitados no canal {ctx.channel} (Use d$desabilitarboasvindas para desabilitar.)")


@bot.hybrid_command(name="desabilitarboasvindas", description="Desabilitar a mensagem de boas vindas em um canal específico")
@commands.has_permissions(administrator=True)
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def desabilitarboasvindas(ctx) -> None:
    if isinstance(ctx.message.channel, discord.DMChannel):
        await ctx.reply("Esse comando não está disponível via DM.")
        return
    if Path(f"guilds/{ctx.message.guild.id}").exists() is False:
        os.makedirs(f"guilds/{ctx.message.guild.id}")
    if Path(f"guilds/{ctx.message.guild.id}/welcome_message").exists() is False:
        with open(f'guilds/{ctx.message.guild.id}/welcome_message', 'w') as f:
            f.write("Uma pessoa nova entrou! Bem vindo {{user}}!")
    if Path(f"guilds/{ctx.message.guild.id}/welcome_channel.toml").exists() is False:
        with open(f'guilds/{ctx.message.guild.id}/welcome_channel.toml', 'w') as f:
            f.write("channels = []")
    with open(f'guilds/{ctx.message.guild.id}/welcome_channel.toml', 'r') as f:
        config = toml.load(f)

    if ctx.channel.id in config["channels"]:
        config["channels"].remove(ctx.channel.id)
    else:
        pass

    with open(f'guilds/{ctx.message.guild.id}/welcome_channel.toml', 'w') as f:
        toml.dump(config, f)

    await ctx.reply(f"Mensagem de boas vindas desativados no canal {ctx.channel} (Use d$habilitarboasvindas para habilitar.)")


class TagModal(BaseModal, title="Mensagem de boas vindas"):
    tag_content = discord.ui.TextInput(label="A mensagem", placeholder="Lembre-se que {{user}} vai mencionar o novo usuário!", min_length=1, max_length=300, style=discord.TextStyle.long)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        with open(f'guilds/{interaction.guild_id}/welcome_message', 'w') as f:
            f.write(self.tag_content.value)
        message = self.tag_content.value.replace("{{user}}", "{usuário mencionado}")
        await interaction.followup.send(f"Sua mensagem foi registrada! ela vai ficar assim:\n\n{message}", ephemeral=True)
        await super().on_submit(interaction)


@bot.hybrid_command(name="mensagemdeboasvindas", description="Editar a mensagem de boas vindas")
@commands.has_permissions(administrator=True)
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def mensagemdeboasvindas(ctx: discord.ApplicationContext):
    if isinstance(ctx.message.channel, discord.DMChannel):
        await ctx.reply("Esse comando não está disponível via DM.")
        return
    if Path(f"guilds/{ctx.message.guild.id}/welcome_message").exists() is False:
        with open(f'guilds/{ctx.message.guild.id}/welcome_message', 'w') as f:
            f.write("Uma pessoa nova entrou! Bem vindo {{user}}!")
    view = BaseView(ctx.author)
    view.add_item(discord.ui.Button(label="Editar mensagem de boas vindas", style=discord.ButtonStyle.blurple))

    async def callback(interaction: discord.Interaction):
        await interaction.response.send_modal(TagModal())

    view.children[0].callback = callback
    view.message = await ctx.send("Para editar a mensagem, clique no botão abaixo.", view=view)


####################################################################################
# PREFIX COMMANDS
####################################################################################


@bot.hybrid_command(name="sobre", description="Dá uma descrição do bot")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def sobre(ctx):

    class ErrorReport(BaseModal, title="Reportar um erro"):
        tag_content = discord.ui.TextInput(label="Descreva seu erro aqui", placeholder="Meu erro aconteceu blah blah blah...", min_length=1, max_length=1024, style=discord.TextStyle.long)

        async def on_submit(self, interaction: discord.Interaction) -> None:
            await interaction.response.defer()
            idk = bot.get_user(int("727194765610713138"))
            await idk.send(f"**Erro reportado por {ctx.author.global_name} (ID: {ctx.author.id})**\n\nErro reportado: {self.tag_content.value}")
            await interaction.followup.send(f"Obrigado pela sua colaboração.", ephemeral=True)
            await super().on_submit(interaction)

    list = os.listdir("profile/")
    the_user = bot.get_user(int("727194765610713138"))
    embed = discord.Embed(title=f'{bot_name}', colour=0x00b0f4)
    embed.set_thumbnail(url=bot.user.display_avatar)
    embed.add_field(name="Tempo Ligado:", value=uptime(), inline=True)
    with open("comandos_usados", "r") as f:
        commands_used = f.read()
    embed.add_field(name="Comandos Usados:", value=commands_used, inline=True)
    embed.add_field(name="Perfis disponíveis:", value=f"{len(list)} perfis", inline=False)
    embed.set_footer(text=f"Feito por Jocadbz - v{version}",
                     icon_url=the_user.display_avatar)

    view = BaseView(ctx.author)
    view.add_item(discord.ui.Button(label="Reportar um erro", style=discord.ButtonStyle.gray, emoji='✍️'))

    async def callback(interaction: discord.Interaction):
        await interaction.response.send_modal(ErrorReport())

    view.children[0].callback = callback
    view.message = await ctx.reply(embed=embed, view=view)


# Battle Command
# Simmulates an idiotic battle between two concepts.
@bot.hybrid_command(name="battle", description="Simula uma batalha")
@app_commands.describe(arg1="Pessoa um", arg2="Pessoa Dois")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def battle(ctx, arg1: str, arg2: str) -> None:
    rand1 = [0, 1]

    if random.choice(rand1) == 0:
        comeco = ["Foi por pouco, mas ", "E com grande folga, ", "Foi uma luta justa, mas "]
        fim = ["esmagando seu crânio.", "abrindo um buraco em seu peito.", "decepando sua cabeça."]
        jokes = f"{random.choice(comeco)}{arg1} ganhou a luta contra {arg2} {random.choice(fim)}"
        await ctx.send(jokes)
    else:
        comeco = ["Foi por pouco, mas ", "E com grande folga, ", "Foi uma luta justa, mas "]
        fim = ["esmagando seu crânio.", "abrindo um buraco em seu peito.", "decepando sua cabeça.", "desintegrando seu corpo.", "serrando seu corpo ao meio."]
        jokes = f"{random.choice(comeco)}{arg2} ganhou a luta contra {arg1} {random.choice(fim)}"
        await ctx.send(jokes)


# Gerador de cancelamento
# Roubado de um certo site
@bot.hybrid_command(name="cancelamento", description="Simula um cancelamento")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def cancelamento(ctx):
    motivos = ["ser atraente demais", "ter charme demais", "ser uma pessoa horrível", "ser uma grande gostosa", "ser boy lixo", "ser comunista", "debochar demais ser inteligente demais", "ser padrãozinho", "pedir muito biscoito", "ser corno ser uma delícia", "ser gado demais", "não ser ninguém", "ser poser", "ser insuportável", "ser insensível", "não fazer nada", "ser trouxa", "se atrasar", "sempre ser impaciente demais", "ter virado o Coronga", "ser BV", "ter muita preguiça", "ser inútil", "ser inadimplente no Serasa", "contar muita piada ruim", "procrastinar demais", "por se considerar incancelável"]
    await ctx.send(f"{ctx.author.mention} foi cancelado por {random.choice(motivos)}")


# SÁBIO
# Obtenha respostas para as questões mais importantes da vida.
@bot.hybrid_command(name="sabio", description="Obtenha as respostas para todas as questões da vida")
@app_commands.describe(pergunta="A pergunta que você quer")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def sabio(ctx, *, pergunta: str):
    jokes = ["SIM, COM TODA CERTEZA", "Sim, com certeza.", "Sim.", "Provavelmente.", "Não sei dizer.", "Provavelmente não.", "Não.", 'Com certeza não.', "NÃO, COM TODA CERTEZA NÃO"]
    await ctx.send(random.choice(jokes))


# PPT
# Declaração de amor via Discord... que brega.
@bot.hybrid_command(name="ppt", description="Declare seu amor!")
@app_commands.describe(lover="Seu amado")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def ppt(ctx, lover: discord.Member) -> None:
    jokes = f"Caro/Cara {lover}, o {ctx.author.mention} gostaria de declarar seus sentimentos a você."
    await ctx.send(jokes)


# Jogo
# Simulação do jogo de futebol do seu time. Que você sabe que vai perder.
@bot.hybrid_command(name="jogo", description="Deixe o bot decidir o resultado do jogo do seu time de coração")
@app_commands.describe(time1="Time Um", time2="Time dois")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def jogo(ctx, time1: str, time2: str) -> None:
    rand1 = [0, 1, 2, 3, 4, 5]
    jokes = f"O resultado da partida de {time1} x {time2} vai ser {random.choice(rand1)} x {random.choice(rand1)}"
    await ctx.send(jokes)


@bot.hybrid_command(name="comprar", description=f"Informações sobre a compra de {coin_name}")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def comprar(ctx):
    thing = f"""Ficou sem dinheiro apostando com o ADM? Agora você pode realizar a compra de {coin_name}!
Comprar {coin_name} é um jeito de ajudar o bot a continuar online, ajuda o criador a pagar as contas, e principalmente, nos ajuda a continuar desenvolvendo!

Para comprar, chame o criador do {bot_name} (@jocadbz) na DM. O valor é negociável."""
    await ctx.author.send(f"{thing}\nhttps://tenor.com/view/mlem-silly-goofy-cat-silly-cat-goofy-gif-27564930")
    await ctx.send("Mensagem mandada na sua DM!")


@bot.hybrid_command(name="premium", description="Informações sobre a compra do Premium")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def premium(ctx):
    if Path(f"profile/{ctx.author.id}/premium").exists() is False:
        thing = f"""Agora ficou ainda mais fácil de ganhar beneficíos no {bot_name}. O Premium é um jeito barato, rápido, e fácil de ostentar para os pobres.
Os benefícios incluem:
- 100K De {coin_name}
- O DOBRO de dinheiro no d$daily
- Todos os benefícios da lojinha permanentemente
- Perfil diferenciado

O preço estabelecido é de R$2/Semana (50% OFF!!). Para realizar a compra, chame @jocadbz na DM."""
        await ctx.author.send(f"{thing}\nhttps://cdn.discordapp.com/attachments/1164700096668114975/1175195963636322334/image0.gif?ex=656a5987&is=6557e487&hm=1e638b6daaa7c3f5661b8356b67eadae6231b7220b6cb25ecd5c0612e98dd514&")
        await ctx.reply("Mensagem mandada na sua DM!")
    else:
        newdate1 = dateutil.parser.parse(open(f"profile/{ctx.author.id}/premium/date", 'r+'))
        newdate1 = newdate1 + relativedelta(days=7)
        embed = discord.Embed(title="Premium",
                              colour=0xf5c211)

        embed.set_author(name=f"Bem vindo {ctx.author.display_name}",
                         icon_url=ctx.author.display_avatar.url)

        embed.add_field(name="Data",
                        value=f"Seu premium acaba em <t:{int(newdate1.timestamp())}:F>",
                        inline=True)

        embed.set_footer(text=f"{bot_name}",
                         icon_url=bot.user.display_avatar.url)

        await ctx.reply(embed=embed)


# Ping
# Não estamos nos referindo ao esporte.
@bot.hybrid_command(name="ping", description="Teste a latência do bot")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def ping(ctx):
    if round(bot.latency * 1000) <= 50:
        embed = discord.Embed(title="Ping", description=f":ping_pong: Pingpingpingpingping! O ping é de **{round(bot.latency * 1000)}** millisegundos!", color=0x44ff44)
    elif round(bot.latency * 1000) <= 100:
        embed = discord.Embed(title="Ping", description=f":ping_pong: Pingpingpingpingping! O ping é de **{round(bot.latency * 1000)}** millisegundos!", color=0xffd000)
    elif round(bot.latency * 1000) <= 200:
        embed = discord.Embed(title="Ping", description=f":ping_pong: Pingpingpingpingping! O ping é de **{round(bot.latency * 1000)}** millisegundos!", color=0xff6600)
    else:
        embed = discord.Embed(title="Ping", description=f":ping_pong: Pingpingpingpingping! O ping é de **{round(bot.latency * 1000)}** millisegundos!", color=0x990000)
    await ctx.send(embed=embed)


@bot.hybrid_command(name="daily", description=f"Ganhe {coin_name} diários")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def daily(ctx):
    checkprofile(ctx.author.id)
    if Path(f"profile/{ctx.author.id}/daily_grabbed").exists() is True:
        newdate1 = dateutil.parser.parse(open(f"profile/{ctx.author.id}/daily_grabbed", 'r+'))
        if newdate1 + relativedelta(hours=24) <= datetime.datetime.now():
            os.remove(f"profile/{ctx.author.id}/daily_grabbed")
            # Nothing to do, removes and continues the operation
        else:
            timestamped_date = newdate1 + relativedelta(days=1)
            await ctx.send(f"Opaaa pera lá, você já pegou seus {coin_name} diários. Espere até <t:{int(timestamped_date.timestamp())}:f> para pegar novamente. (Dica: d$comprar)")
            return

    if Path(f"profile/{ctx.author.id}/premium").exists() is True:
        increase_coins(ctx.author.id, 1300)

        await ctx.reply(f"Você ganhou 1300 {coin_name}! (Bônus de Premium)")
    else:
        increase_coins(ctx.author.id, 1200)

        await ctx.reply(f"Você ganhou 1200 {coin_name}!")
    current_date = datetime.datetime.now()
    with open(f'profile/{ctx.author.id}/daily_grabbed', 'w') as f:
        f.write(current_date.isoformat())


@bot.hybrid_group(fallback="ajuda")
async def perfil(ctx: commands.Context) -> None:
    embed = discord.Embed(title="Perfil",
                          description="Comandos disponíveis:\n\n- `ver`\n- `sobremim`",
                          colour=0x00b0f4)

    await ctx.send(embed=embed)


# Profile
# Check User Profile
@perfil.command(name="ver", description="Verifique o seu perfil e o de outros usuários")
@app_commands.describe(rsuser="O Usuário para verificar o perfil")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
# TODO: Try to find a way of reducing code in this specific command.
async def profile(ctx, rsuser: discord.User | None = None):
    # Now the actual code
    rsuser = rsuser or None
    if rsuser is not None:
        # TODO: Fix the fact that this gets ignored if we throw any letters at it.
        user_sent = rsuser.id
        if bot.get_user(int(user_sent)) is None:
            await ctx.send(f"Tem certeza de que esse user existe?")
            return
    else:
        user_sent = ctx.author.id

    # Defining the fucking modal again fucking shit
    class ProfileButton(BaseModal, title="Editar Sobre mim"):
        tag_content = discord.ui.TextInput(label="Novo texto", placeholder="Eu sou uma pessoa muito legal...", min_length=1, max_length=1024, style=discord.TextStyle.long)

        async def on_submit(self, interaction: discord.Interaction) -> None:
            await interaction.response.defer()
            with open(f'profile/{user_sent}/about', 'w') as f:
                f.write(self.tag_content.value)
            await interaction.followup.send(f"Seu perfil foi atualizado", ephemeral=True)
            await super().on_submit(interaction)

    checkprofile(user_sent)

    if str(user_sent) == "727194765610713138":
        embed = discord.Embed(title=f"Perfil do/a {bot.get_user(int(user_sent)).display_name} (🤖 Dono do bot)",
                              description="",
                              colour=12526271)
    elif Path(f"profile/{user_sent}/premium").exists() is True:
        embed = discord.Embed(title=f"Perfil do/a {bot.get_user(int(user_sent)).display_name} (👑 Premium)",
                              description="",
                              colour=0xf5c211)
    else:
        embed = discord.Embed(title=f"Perfil do/a {bot.get_user(int(user_sent)).display_name}",
                              description="",
                              colour=0x00b0f4)
    if Path(f"profile/{user_sent}/casado").is_file() is True:
        if bot.get_user(int(open(f'profile/{user_sent}/casado', 'r+').read())) is None:
            pass
        else:
            user = bot.get_user(int(open(f'profile/{user_sent}/casado', 'r+').read())).display_name
            embed.set_author(name=f"💍 Casado/a com {user}",
                             icon_url=bot.get_user(int(open(f"profile/{user_sent}/casado", "r+").read())).display_avatar)
    embed.add_field(name="Sobre Mim",
                    value=f"""{open(f"profile/{user_sent}/about", "r+").read()}""",
                    inline=False)
    embed.add_field(name=f"{coin_name}",
                    value=f"""D£ {humanize.intcomma(open(f"profile/{user_sent}/coins", "r+").read())}""",
                    inline=False)
    if isinstance(ctx.message.channel, discord.DMChannel) is False:
        embed.add_field(name="Pontos de Experiência (Neste Servidor) - Level",
                        value=f"""{humanize.intcomma(open(f"profile/{user_sent}/experience-{ctx.guild.id}", "r+").read())} XP - LV {open(f'profile/{user_sent}/level-{ctx.guild.id}', 'r+').read()}""",
                        inline=False)

    embed.add_field(name="Apostas vencidas",
                    value=f"""{open(f"profile/{user_sent}/duelos", "r+").read()}""",
                    inline=False)
    if Path(f"profile/{user_sent}/image_url").exists() is True:
        embed.set_image(url=f"{open(f'profile/{user_sent}/image_url', 'r+').read()}")
    embed.add_field(name="Duelos Mortalmente Mortais",
                    value=f"""Ganhou {open(f"profile/{user_sent}/duelos_vencidos", "r+").read()} - Perdeu {open(f"profile/{user_sent}/duelos_perdidos", "r+").read()}""",
                    inline=False)
    embed.add_field(name="Comandos NSFW Usados",
                    value=f"""{open(f"profile/{user_sent}/punhetas", "r+").read()}""",
                    inline=False)

    embed.set_thumbnail(url=bot.get_user(int(user_sent)).display_avatar)

    embed.set_footer(text=f"{bot_name}",
                     icon_url=bot.user.display_avatar)
    if user_sent == ctx.author.id:
        view = BaseView(ctx.author)
        view.add_item(discord.ui.Button(label="Alterar sobre mim", style=discord.ButtonStyle.gray, emoji='✍️'))

        async def callback(interaction: discord.Interaction):
            await interaction.response.send_modal(ProfileButton())

        view.children[0].callback = callback
        view.message = await ctx.reply(embed=embed, view=view)
    else:
        await ctx.reply(embed=embed)


@perfil.command(name="sobremim", description="Edite seu perfil")
@app_commands.describe(sobre_mim="O texto que vai estar no seu perfil")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def sobremim(ctx, *, sobre_mim: str):
    checkprofile(ctx.author.id)
    if len(sobre_mim) > 1024:
        await ctx.reply("Sua descrição é longa demais...", ephemeral=True)
        return
    with open(f'profile/{ctx.author.id}/about', 'w') as f:
        f.write(sobre_mim)
    await ctx.reply("Seu perfil foi atualizado!", ephemeral=True)


# Escolhas da Lojinha
class Item(str, enum.Enum):
    Item_1 = "1"
    Item_2 = "2"
    Item_3 = "3"


@perfil.command(name="upload_image", description="Dê upload em uma imagem para colocar no seu perfil")
@app_commands.describe(attachment="A imagem que você deseja colocar no seu perfil")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def uploadimage(ctx, *, attachment: discord.Attachment):
    checkprofile(ctx.author.id)
    if attachment.filename.endswith(('.png', '.gif', '.jpg', '.jpeg')) is False:
        await ctx.reply("O arquivo que você mandou não é um tipo reconhecido pelo discord. (Tipos suportados: png, gif, jpg, jpeg)")
    else:
        with open(f'profile/{ctx.author.id}/image_url', 'w') as f:
            f.write(attachment.url)
        # await attachment.save(f"profi")
        await ctx.reply(f"Você fez upload do arquivo {attachment.filename}!", ephemeral=True)


@perfil.command(name="remove_image", description="Remova a imagem para colocar no seu perfil")
@app_commands.describe(attachment="A imagem que você deseja colocar no seu perfil")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def removeimage(ctx, *, attachment: discord.Attachment):
    checkprofile(ctx.author.id)
    if Path(f"profile/{ctx.author.id}/image_url").exists() is True:
        await ctx.reply("Você não tem uma imagem no seu perfil.")
        return
    else:
        os.remove(f"profile/{ctx.author.id}/image_url")
        await ctx.reply("Imagem removida.")

# Lojinha
@bot.hybrid_command(name="lojinha", description="Verifique os itens da lojinha")
@app_commands.describe(arg1="O Item para comprar")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def lojinha(ctx, arg1: Item | None = None):
    if isinstance(ctx.message.channel, discord.DMChannel):
        await ctx.reply("Esse comando não está disponível via DM.")
        return
    if ctx.guild.id == 1207100636278034472:
        price_1 = 0
        price_2 = 0
        price_3 = 0
    else:
        price_1 = 200
        price_2 = 500
        price_3 = 150

    arg1 = arg1 or None
    checkprofile(ctx.author.id)
    if arg1 == "1":
        current_coins = get_user_coins(ctx.author.id)
        if current_coins >= price_1:
            decrease_coins(ctx.author.id, price_1)

            await ctx.send("Você comprou o benefício 1.")
            bought_two.append(ctx.author)
            await asyncio.sleep(2500)  # time in seconds
            bought_two.remove(ctx.author)
        else:

            await ctx.send(f"A-Ah, m-mais que twiste!!11 você não tem {coin_name} o suficiente. *looks at you* (Dica UWU: d$comprar)")
    elif arg1 == "2":
        current_coins = get_user_coins(ctx.author.id)
        if current_coins >= price_2:

            await ctx.send("Você comprou o benefício 2. Primeiramente, responda a essa mensagem com o nome do comando. (Exemplo, se você colocar 'example', seu comando vai ser 'cd$example')")

            def sus(m):
                return m.author == ctx.author

            try:
                msg1 = await bot.wait_for('message', check=sus)
            except asyncio.TimeoutError:
                await ctx.send('Compra cancelada. Tente novamente.')
            else:
                array = bot.commands
                new_array = []
                for i in array:
                    new_array.append(i.name)
                if msg1.content.lower() in new_array:
                    await ctx.reply("Oops, esse comando já existe.")
                    return
                else:
                    if Path(f"guilds/{ctx.guild.id}/custom_commands/{msg1.content.lower()}").exists() is True:
                        await ctx.reply("Oops, esse comando já existe.")
                        return

                await ctx.send("Agora, responda a essa mensagem com o que você quer que o comando mande (GIFs, mensagens, etc)")

                def sus(m):
                    return m.author == ctx.author

                try:
                    msg2 = await bot.wait_for('message', check=sus)
                except asyncio.TimeoutError:
                    await ctx.send('Compra cancelada. Tente novamente.')
                else:
                    msgcontent = [msg2.content]
                    if len(msg2.attachments) == 0:
                        pass
                    else:
                        for attachment in msg2.attachments:
                            msgcontent.append(f"{attachment.url} ")
                    if " ".join(msgcontent) == "" or " ".join(msgcontent) is None:
                        await ctx.send("Você não pode mandar um comando sem nada...")
                        return
                    await ctx.send('Comando registrado.')
                    decrease_coins(ctx.author.id, price_2)
                    with open(f'guilds/{ctx.guild.id}/custom_commands/{msg1.content.lower()}', 'w') as f:
                        f.write(" ".join(msgcontent))
        else:

            await ctx.send(f"Ah mais que triste. Você não tem {coin_name} o suficiente. (Dica: d$comprar)")

    elif arg1 == "3":
        current_coins = get_user_coins(ctx.author.id)
        if current_coins >= price_3:
            decrease_coins(ctx.author.id, price_3)

            await ctx.send("Você comprou o benefício 3.")
            bought_four.append(ctx.author)
            await asyncio.sleep(2500)  # time in seconds
            bought_four.remove(ctx.author)
        else:

            await ctx.send(f"Ah mais que triste. Você não tem {coin_name} o suficiente. (Dica: d$comprar)")

    elif arg1 is None:

        embed = discord.Embed(title=f"Lojinha do {bot_name}",
                              description=f"Compre benefícios com seus {coin_name} aqui! - Mande o comando '$lojinha <numero>' para comprar!",
                              colour=0x00b0f4)

        embed.add_field(name=f"I - Rinha e Duelo Cooldown Remover",
                        value=f"Não seja afetado pelo cooldown das apostas e duelos por 40 minutos - {price_1} {coin_name}",
                        inline=False)
        embed.add_field(name=f"II - Comando customizado",
                        value=f"Coloque um comando customizado com seu username - {price_2} {coin_name}s",
                        inline=False)
        embed.add_field(name=f"III - Sonegar impostos",
                        value=f"Seja um fora da lei e pague zero impostos na suas transferencias por 40 minutos - {price_3} {coin_name}",
                        inline=False)

        embed.set_footer(text=f"{bot_name}",
                         icon_url=bot.user.display_avatar)

        await ctx.send(embed=embed)


# Investir
# Perder ou ganhar? É o bot quem decide.
@bot.hybrid_command(name="investir", description="O lobo de Wall Street")
@app_commands.describe(arg1="A quantidade para investir")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def investir(ctx, arg1: int) -> None:
    checkprofile(ctx.author.id)

    investir_random = ["win", "lose"]
    resultado = random.choice(investir_random)
    win_thing = [4, 10, 2, 2, 4, 5]
    win_thing = random.choice(win_thing)

    if arg1 < 0:
        await ctx.send("Você não pode investir valores menores ou iguais a zero.")
        return

    if arg1 > get_user_coins(ctx.author.id):
        await ctx.reply("Você não tem fundos o suficiente pra investir. (Dica: d$comprar)")
    else:
        if resultado == "win":

            await ctx.reply(f"Você lucrou {humanize.intcomma(str(win_thing).replace('0.', ''))}%! Seu lucro total foi {int(int(arg1)*win_thing / 100)} {coin_name}!")
            new_coins = int(round(int(arg1) * win_thing / 100))
            increase_coins(ctx.author.id, new_coins)
        else:

            await ctx.reply(f"Você perdeu {humanize.intcomma(str(win_thing).replace('0.', ''))}%! Suas perdas totais foram {int(round(int(arg1)*win_thing / 100))} {coin_name}... Boa sorte na próxima...")
            new_coins = int(round(int(arg1) * win_thing / 100))
            decrease_coins(ctx.author.id, new_coins)


# Roleta
# Roda a Roda jequiti
@bot.hybrid_command(name="roleta", description="Roda a Roda Jequiti")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def roleta(ctx):
    checkprofile(ctx.author.id)
    roleta_random = [100, 10, 50, 200, 0, 100, 110, 110, 140, 140, 120, 120, 110, 110, 110, 120, 0, 0, 140]
    resultado = random.choice(roleta_random)

    if ctx.author in roleta_cooldown:

        await ctx.send("Opaaa pera lá, você já pegou seu giro. Espere mais um tempo para pegar novamente. (Dica: d$comprar)")

    else:

        await ctx.send(f"O resultado da sua roleta foi... {resultado} {coin_name}!")
        increase_coins(ctx.author.id, resultado)
        roleta_cooldown.append(ctx.author)
        await asyncio.sleep(2000)
        roleta_cooldown.remove(ctx.author)


# Doar
# MrBeast
@bot.hybrid_command(name="doar", description="Doe dinheiro para pessoas!")
@app_commands.describe(amount=f"A quantidade de {coin_name}", user="A Pessoa para quem você quer doar")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def doar(ctx, amount: int, user: discord.Member):
    checkprofile(ctx.author.id)
    if bot.get_user(user.id) is None:
        await ctx.send("Tem certeza de que esse user existe?")
    else:
        checkprofile(user.id)
        if amount > get_user_coins(ctx.author.id):
            await ctx.send("Você não tem fundos o suficiente pra completar essa transação. (Dica: d$comprar)")
        else:
            if amount < 0:
                await ctx.send("Você não pode doar um valor negativo ou igual a zero.")
                return
            if ctx.author in bought_four:
                imposto = 0
            elif 1 == 1:
                imposto = 0
            else:
                imposto = round(amount) * 0.05
            decrease_coins(ctx.author.id, amount)
            increase_coins(user.id, amount - imposto)
            increase_coins(727194765610713138, imposto)
            if imposto != 0:

                await ctx.send(f"Você transferiu {humanize.intcomma(amount)} {coin_name} para {user.mention}! (Imposto cobrado: {str(int(imposto))} {coin_name})")
                await ctx.send(f"Compre o benefício 4 na d$lojinha para não pagar impostos!")
            else:

                await ctx.send(f"Você transferiu {humanize.intcomma(amount)} {coin_name} para {user.mention}! (Sem impostos cobrados)")


@bot.hybrid_command(name="adivinhar", description="Adivinhe um número e ganhe sonhos... ou perca eles...")
@app_commands.describe(amount="A quantia que você quer apostar", number="O número em qual você quer apostar")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def adivinhar(ctx, amount: int, number: int):
    if number > 10 or number < 0:
        await ctx.reply("Você só pode escolher entre números de 0 a 10!")
        return
    possibilities = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    checkprofile(ctx.author.id)
    user_coins = get_user_coins(ctx.author.id)
    if amount == user_coins:
        if Path(f"profile/{ctx.author.id}/conquistas/conquista1.toml").exists() is False:
            dar_conquistas(ctx.author.id, "1")
            await ctx.send("**Conquista obtida:** *Eu confio na sorte!*")
    if amount > user_coins:
        await ctx.reply("Me parece que você não pode cobrir essa aposta... (Dica: d$comprar)")
        if amount < 0:
            await ctx.send("Você não pode apostar um valor negativo ou igual a zero.")
            return
    else:
        if number == random.choice(possibilities):

            await ctx.reply(f"Parabéns! Você acertou, e ganhou {humanize.intcomma(amount*10)}!")
            increase_coins(ctx.author.id, amount*5)
        else:

            await ctx.reply(f"Poxa! Você perdeu {humanize.intcomma(amount)}...")
            decrease_coins(ctx.author.id, amount)


@bot.hybrid_command(name="aposta", description="Perca sua fortuna apostando!")
@app_commands.describe(amount=f"A quantidade de {coin_name}", user="A Pessoa com quem você quer apostar")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def aposta(ctx, amount: int, user: discord.Member):
    blah = user
    checkprofile(ctx.author.id)
    if ctx.author in rinha_cooldown:

        await ctx.send("Opaaa pera lá, você já apostou. Espere o cooldown acabar. (Dica: Você pode pular esse cooldown comprando o benefício 2 na d$lojinha)")
    else:
        user_coins = get_user_coins(ctx.author.id)
        if amount == user_coins:
            if Path(f"profile/{ctx.author.id}/conquistas/conquista1.toml").exists() is False:
                dar_conquistas(ctx.author.id, "1")
                await ctx.send("**Conquista obtida:** *Eu confio na sorte!*")
        if amount > user_coins:
            await ctx.send("Você não tem fundos o suficiente pra apostar. (Dica: d$comprar)")
            return
        if amount < 0:
            await ctx.send("Você não pode apostar um valor negativo ou igual a zero.")
            return
        else:
            if user.id == ctx.author.id:

                await ctx.send("Você não pode apostar com você mesmo.")
            else:
                checkprofile(user.id)
                if amount > get_user_coins(user.id):
                    await ctx.send("Me parece que seu oponente não pode cobrir essa aposta... (Dica: d$comprar)")
                else:

                    aposta_message = await ctx.send(f"**Atenção {user.mention}, o {ctx.author.mention} quer apostar {humanize.intcomma(amount)} {coin_name} com você. Reaja a esta mensagem com um emoji de dedão '👍' em 15 segundos para concordar com a aposta.**")
                    await aposta_message.add_reaction('👍')

                    def check(reaction, user):
                        return user == blah and str(reaction.emoji) == '👍'
                    try:
                        reaction, user = await bot.wait_for('reaction_add', timeout=15.0, check=check)
                    except asyncio.TimeoutError:

                        await ctx.send("Aposta cancelada")
                    else:
                        things = ["win", "lose"]
                        resultado = random.choice(things)
                        # You see this text down here? Pretty messy heh?
                        # The first thing you will think of doing is removing those useless variables, but here is the catch: It doesn't work without them.
                        # The code has a absolutely stroke, so I don't reccoment changing anything here.
                        if resultado == 'win':

                            await aposta_message.edit(content=f"O Ganhador foi...\n{ctx.author.mention}! Parabéns, você ganhou {humanize.intcomma(amount)} {coin_name}!")
                            increase_coins(ctx.author.id, amount)
                            decrease_coins(user.id, amount)
                            current_duels_user = open(f"profile/{ctx.author.id}/duelos", "r+").read()
                            new_duels_user = int(current_duels_user) + 1
                            with open(f'profile/{ctx.author.id}/duelos', 'w') as f:
                                f.write(str(new_duels_user))

                        else:

                            await aposta_message.edit(content=f"O Ganhador foi...\n{user.mention}! Parabéns, você ganhou {humanize.intcomma(amount)} {coin_name}!")
                            increase_coins(user.id, amount)
                            decrease_coins(ctx.author.id, amount)
                            current_duels_user = open(f"profile/{user.id}/duelos", "r+").read()
                            new_duels_user = int(current_duels_user) + 1
                            with open(f'profile/{user.id}/duelos', 'w') as f:
                                f.write(str(new_duels_user))
                        if ctx.author not in bought_two:
                            rinha_cooldown.append(ctx.author)
                            await asyncio.sleep(15)  # time in seconds
                            rinha_cooldown.remove(ctx.author)


# Duelo
# Extremamente utíl pra fazer GF- D-Digo, roleplay.
@bot.hybrid_command(name="duelo", description="Resolva seus problemas com honra...")
@app_commands.describe(user="A Pessoa com quem você quer duelar")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def duelo(ctx, user: discord.Member):
    blah = user
    checkprofile(ctx.author.id)
    if ctx.channel.id == 1164700096668114975:

        await ctx.send("O Tiran- digo, ADM do Server mandou tirar esse comando do Geral. Foi mal!")
    else:
        if ctx.author in rinha_cooldown:

            await ctx.send("Opaaa pera lá, você já duelou. Espere o cooldown acabar. (Dica: Você pode pular esse cooldown comprando o benefício 2 na d$lojinha)")
        else:
            if user.id == ctx.author.id:

                await ctx.send("Você não pode duelar contra você mesmo.")
            else:
                checkprofile(user.id)

                aposta_message = await ctx.send(f"**Atenção {user.mention}, o {ctx.author.mention} quer duelar com você. Reaja a esta mensagem com um emoji de espada '⚔️' em 15 segundos para concordar com o duelo.**")
                await aposta_message.add_reaction('⚔️')

                def check(reaction, user):
                    return user == blah and str(reaction.emoji) == '⚔️'

                try:
                    reaction, user = await bot.wait_for('reaction_add', timeout=15.0, check=check)
                except asyncio.TimeoutError:

                    await ctx.send("Duelo cancelada")
                else:
                    resultado = random.choice(["win", "lose"])
                    if resultado == 'win':

                        await aposta_message.edit(content=f"O Ganhador foi...\n{ctx.author.mention}! Parabéns, você ganhou duelo!")
                        current_duels_user = open(f"profile/{ctx.author.id}/duelos_vencidos", "r+").read()
                        new_duels_user = int(current_duels_user) + 1
                        with open(f'profile/{ctx.author.id}/duelos_vencidos', 'w') as f:
                            f.write(str(new_duels_user))
                        current_duels_user = open(f"profile/{user.id}/duelos_perdidos", "r+").read()
                        new_duels_user = int(current_duels_user) + 1
                        with open(f'profile/{user.id}/duelos_perdidos', 'w') as f:
                            f.write(str(new_duels_user))

                    else:

                        await aposta_message.edit(content=f"O Ganhador foi...\n{user.mention}! Parabéns, você ganhou o duelo!")
                        current_duels_user = open(f"profile/{user.id}/duelos_vencidos", "r+").read()
                        new_duels_user = int(current_duels_user) + 1
                        with open(f'profile/{user.id}/duelos_vencidos', 'w') as f:
                            f.write(str(new_duels_user))
                        current_duels_user = open(f"profile/{ctx.author.id}/duelos_perdidos", "r+").read()
                        new_duels_user = int(current_duels_user) + 1
                        with open(f'profile/{ctx.author.id}/duelos_perdidos', 'w') as f:
                            f.write(str(new_duels_user))
                    if ctx.author not in bought_two:
                        rinha_cooldown.append(ctx.author)
                        await asyncio.sleep(15)
                        rinha_cooldown.remove(ctx.author)
                    else:
                        pass


# Avatar
# See user avatar
@bot.hybrid_command(name="avatar", description="Veja a foto de perfil dos seus amigos!")
@app_commands.describe(user="A Pessoa que você quer ver a foto")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def avatar(ctx, user: discord.Member):
    embed = discord.Embed(title=f"Avatar de {user.display_name}",
                          colour=0x00b0f4)

    embed.set_image(url=user.display_avatar)

    await ctx.send(embed=embed)


@bot.hybrid_command(name="banner", description="Veja o banner dos seus amigos!")
@app_commands.describe(user="A Pessoa que você quer ver a foto")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def banner(ctx, user: discord.Member):

    user = await bot.fetch_user(user.id)
    if user.banner is None:
        embed = discord.Embed(title=f"Me parece que {user.display_name} não tem um banner... 😕",
                              colour=0x00b0f4)
        await ctx.send(embed=embed)
        return
    embed = discord.Embed(title=f"Banner de {user.display_name}",
                          colour=0x00b0f4)

    embed.set_image(url=user.banner.url)

    await ctx.send(embed=embed)


@bot.hybrid_group(fallback="ajuda")
async def casamento(ctx: commands.Context) -> None:
    embed = discord.Embed(title="Casamento",
                          description="Comandos disponíveis:\n\n- `casar`\n- `divorciar`",
                          colour=0x00b0f4)

    await ctx.send(embed=embed)


@casamento.command(name="casar", description="Se case com uma pessoa!")
@app_commands.describe(user="A Pessoa com quem você quer se casar")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def casamento_1(ctx: commands.Context, user: discord.Member) -> None:
    blah = user
    checkprofile(ctx.author.id)
    checkprofile(user.id)
    if user.id == 1167643852786638889:
        await ctx.reply("Olha... eu te vejo só como amigo... me desculpa...")
        if Path(f"profile/{ctx.author.id}/conquistas/conquista8.toml").exists() is False:
            dar_conquistas(ctx.author.id, "8")
            await ctx.send("**Conquista obtida:** *Eu não sou a pessoa certa pra você...*")
    else:
        if Path(f"profile/{user.id}/casado").is_file() is True:
            if Path(f"profile/{ctx.author.id}/conquistas/conquista3.toml").exists() is False:
                dar_conquistas(ctx.author.id, "3")
                await ctx.send("**Conquista obtida:** *Sempre o coadjuvante, nunca o protagonista*")

            await ctx.send(f"Essa pessoa já está casada com alguém...")
        else:
            if Path(f"profile/{ctx.author.id}/casado").is_file() is True:

                await ctx.send(f"Você já é casado!")
                other = bot.get_user(int(open(f"profile/{ctx.author.id}/casado", "r+").read()))
                await other.send(f"Não é querendo ser fofoqueiro... mais o {ctx.author.display_name} tentou se casar com outra pessoa... 👀👀👀")
                if Path(f"profile/{other.id}/conquistas/conquista5.toml").exists() is False:
                    dar_conquistas(other.id, "5")
                    await other.send("**Conquista obtida:** *Doeu mais em mim do que em você*")
            else:
                if ctx.author in depression:

                    await ctx.send(f"Você está em depressão! Espere mais um tempo para se casar...")

                aposta_message = await ctx.send(f"**Atenção {user.mention}, o {ctx.author.mention} gostaria de se casar com você. Reaja a essa mensagem com um emoji de casamento (💒) para concordar com a cerimônia.**")
                await aposta_message.add_reaction('💒')

                def check(reaction, user):
                    return user == blah and str(reaction.emoji) == '💒'

                try:
                    reaction, user = await bot.wait_for('reaction_add', timeout=15.0, check=check)
                except asyncio.TimeoutError:

                    await aposta_message.edit(content=f"Casamento cancelado! {ctx.author.display_name} agora entrou em depressão...")
                    if Path(f"profile/{ctx.author.id}/conquistas/conquista7.toml").exists() is False:
                        dar_conquistas(ctx.author.id, "7")
                        await ctx.send("**Conquista obtida:** *Eu te vejo apenas como amigo...*")
                    depression.append(ctx.author)
                    await asyncio.sleep(60)
                    depression.remove(ctx.author)
                else:
                    embed = discord.Embed(title=f"💍 {ctx.author.display_name} agora é casado com {user.display_name}! 💍",
                                          colour=0x00b0f4)

                    embed.set_image(url="https://cdn.discordapp.com/attachments/1164700096668114975/1172541249077653514/image0.gif?ex=6560b122&is=654e3c22&hm=02abfda2588e3a62874ba2c16ea8e579bf5dba86b197bfc2fd36478e8ac6832f&")

                    await aposta_message.edit(embed=embed, content="")
                    if Path(f"profile/{ctx.author.id}/conquistas/conquista4.toml").exists() is False:
                        dar_conquistas(ctx.author.id, "4")
                        await ctx.send("**Conquista obtida:** *Até que a conexão ruim nos separe!*")
                    if Path(f"profile/{user.id}/conquistas/conquista4.toml").exists() is False:
                        dar_conquistas(user.id, "4")
                        await ctx.send("**Conquista obtida:** *Até que a conexão ruim nos separe!*")
                    with open(f'profile/{user.id}/casado', 'w') as f:
                        f.write(str(ctx.author.id))
                    with open(f'profile/{ctx.author.id}/casado', 'w') as f:
                        f.write(str(user.id))


@casamento.command(name="divorciar", description="Se divorcie do seu parceiro atual!")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def casamento_2(ctx: commands.Context) -> None:
    if Path(f"profile/{ctx.author.id}/casado").is_file() is True:
        other = bot.get_user(int(open(f"profile/{ctx.author.id}/casado", "r+").read()))
        if int(open(f"profile/{ctx.author.id}/casado", "r+").read()) == ctx.author.id:
            os.remove(f"profile/{ctx.author.id}/casado")
            await ctx.send(f"Você se divorciou de {other.display_name}... 💔")
        else:
            if other is None:
                await ctx.send("Nós não conseguimos achar um usuário com essa ID. Se você era casado com essa pessoa, ela provavelmente saiu do servidor.")
            else:
                await other.send(f"O {ctx.author.display_name} se divorciou de você! 💔")
            os.remove(f"profile/{ctx.author.id}/casado")
            os.remove(f"profile/{other.id}/casado")
            await ctx.send(f"Você se divorciou de {other.display_name}... 💔")
    else:
        await ctx.send("Você nem é casado!")


@bot.hybrid_command(name="rank", description=f"Veja o Rank de XP ou de {coin_name}")
@app_commands.describe(arg1=f"Ver o rank de XP ou de {coin_name}?")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def rank(ctx, arg1: Literal["coins", "xp", "duelos"] | None = None):
    arg1 = arg1 or "coins"
    if arg1 == 'coins':
        ranked_arg = 'coins'
        another_thing = 'ricos'
    elif arg1 == 'xp':
        ranked_arg = 'xp'
        another_thing = 'experientes do servidor'
    elif arg1 == 'duelos':
        ranked_arg = 'duelos'
        another_thing = 'vencedores de duelos'
    else:
        await ctx.send("Argumento não reconhecido; Mudando para 'coins'")
        another_thing = 'ricos'
        ranked_arg = 'coins'

    pages = round(len(os.listdir("profile")) / 5) - 1
    cur_page = 1
    embed = discord.Embed(title=f"Os mais {another_thing}:",
                          description=rank_command(ranked_arg, cur_page - 1, ctx.guild.id),
                          colour=0x00b0f4)

    embed.set_author(name=f"Página {cur_page}:")

    message = await ctx.send(embed=embed)
    # getting the message object for editing and reacting

    await message.add_reaction("◀️")
    await message.add_reaction("▶️")

    def amogus(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["◀️", "▶️"]
        # This makes sure nobody except the command sender can interact with the "menu"

    while True:
        try:
            reaction, user = await bot.wait_for("reaction_add", timeout=60, check=amogus)
            # waiting for a reaction to be added - times out after x seconds, 60 in this
            # example

            if str(reaction.emoji) == "▶️" and cur_page != pages:
                cur_page = cur_page + 1
                command = rank_command(ranked_arg, cur_page - 1, ctx.guild.id)
                embed = discord.Embed(title=f"Os mais {another_thing} do servidor:",
                                      description=command,
                                      colour=0x00b0f4)

                embed.set_author(name=f"Página {cur_page}:")
                await message.edit(embed=embed)
                await message.remove_reaction(reaction, user)

            elif str(reaction.emoji) == "◀️" and cur_page > 1:
                cur_page = cur_page - 1
                command = rank_command(ranked_arg, cur_page - 1, ctx.guild.id)
                embed = discord.Embed(title=f"Os mais {another_thing} do servidor:",
                                      description=command,
                                      colour=0x00b0f4)

                embed.set_author(name=f"Página {cur_page}:")
                await message.edit(embed=embed)
                await message.remove_reaction(reaction, user)

            else:
                await message.remove_reaction(reaction, user)
                # removes reactions if the user tries to go forward on the last page or
                # backwards on the first page
        except asyncio.TimeoutError:
            break
            # ending the loop if user doesn't react after x seconds


@bot.hybrid_command(name="darpremium", description="Comando pro ADM te dar premium")
@app_commands.describe(user="Quem comprou?")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def darpremium(ctx, user: discord.Member):
    checkprofile(user.id)
    if ctx.author.id == 727194765610713138:
        if Path(f"profile/{user.id}/premium").exists() is True:
            await ctx.send("Pô ADM, ele já é Premium...")
        else:
            os.makedirs(f"profile/{user.id}/premium")
            current_date = datetime.datetime.now()
            with open(f'profile/{user.id}/premium/date', 'w') as f:
                f.write(current_date.isoformat())
            current_coins_user = open(f"profile/{user.id}/coins", "r+").read()
            new_coins_user = int(float(current_coins_user)) + 100000
            with open(f'profile/{user.id}/coins', 'w') as f:
                f.write(str(new_coins_user))

            await ctx.send(f"Parabéns {user.mention}, você agora é premium! Você já pode aproveitar todos os benefícios, e P£ 100K já foram transferidos para sua conta. Obrigado por apoiar o {bot_name}!")
    else:
        await ctx.send("Você não é o ADM...")


@bot.hybrid_group(fallback="ajuda")
async def nsfw(ctx: commands.Context) -> None:
    embed = discord.Embed(title="NSFW",
                          description="Comandos disponíveis:\n\n- `hentai`",
                          colour=0x00b0f4)

    await ctx.send(embed=embed)


@nsfw.command(name="hentai", description="Pra Garantir a Famosa Fanheta")
@app_commands.describe(tag="Tags, separadas por espaços")
# Gelbooru currently has a shitty limit of 10 requests evevery second, so we increase the limit.
@commands.cooldown(5, cooldown_command, commands.BucketType.user)
async def nsfw_1(ctx, *, tag: str | None = None):
    checkprofile(ctx.author.id)
    if isinstance(ctx.message.channel, discord.DMChannel):
        await ctx.reply("Esse comando não está disponível via DM.")
        return
    async with ctx.typing():
        tag = tag or None
        if tag is not None:
            if 'reze' in tag.lower() and ctx.guild.id == 1187166078305046539:
                await ctx.reply("Sem hentai da reze.")
                return
        if Path(f"config_nsfw.toml").exists() is False:
            with open(f'config_nsfw.toml', 'w') as f:
                f.write("channels = []")
        with open("config_nsfw.toml", mode="r") as fp:
            config = toml.load(fp)
        if isinstance(ctx.channel, discord.DMChannel):
            pass
        elif ctx.channel.id not in config["channels"]:
            await ctx.reply("O Administrador não autorizou o uso desse comando neste canal.")
            if Path(f"profile/{ctx.author.id}/conquistas/conquista2.toml").exists() is False:
                dar_conquistas(ctx.author.id, "2")
                await ctx.send("**Conquista obtida:** *Sem fanheta...*")
            return
        dan = booru.Danbooru()
        if tag is not None:
            if len(tag.split(' ')) > 2:
                await ctx.reply("Você não pode inserir mais que duas tags.")
                return
            try:
                result_random = await dan.search(query=tag, gacha=True)
            except Exception:
                await ctx.reply("Nenhum resultado encontrado.")
                return
        else:
            try:
                result_random = await dan.search(query="", gacha=True) # We do not support a search without a query for some reason.
            except Exception:
                await ctx.reply("Nenhum resultado encontrado.") 
                return
        data = json.loads(result_random)
        if data.get("file_ext") == 'mp4' or data.get("file_ext") == 'webm':
            resultado = data.get("file_url")
            await ctx.reply(f"NSFW\n{resultado}")
            increase_punheta(ctx.author.id, 1)
        else:
            resultado = data.get("file_url")
            embed = discord.Embed(title="NSFW")
            embed.set_image(url=resultado)
            await ctx.reply(embed=embed)
            increase_punheta(ctx.author.id, 1)


@bot.hybrid_command(name="ppp", description="Pego, penso e passo")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def ppp(ctx):
    if isinstance(ctx.message.channel, discord.DMChannel):
        await ctx.reply("Esse comando não está disponível via DM.")
        return
    oldlist = ctx.guild.members
    verycoollist = []
    mention_list = []
    for member in oldlist:
        if member.bot is True:
            pass
        else:
            if member == ctx.author:
                pass
            else:
                checkprofile(member.id)
                if Path(f"profile/{member.id}/experience-{ctx.guild.id}").exists() is False:
                    pass
                elif int(open(f"profile/{member.id}/experience-{ctx.guild.id}", "r+").read()) >= 1000:
                    verycoollist.append(member)
                else:
                    pass
    while True:
        if len(mention_list) == 3:
            break
        while True:
            thing = random.choice(verycoollist).display_name
            if thing not in mention_list:
                mention_list.append(thing)
                break
            else:
                pass
    await ctx.reply(f"""{mention_list[0]}
{mention_list[1]}
{mention_list[2]}""")


@bot.hybrid_command(name="conquistas", description=f"Veja todas as suas conquistas obtidas com o {bot_name}")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def conquistas(ctx) -> None:
    checkprofile(ctx.author.id)
    conquistas_obtidas = os.listdir(f"profile/{ctx.author.id}/conquistas/")
    if len(conquistas_obtidas) == 0:
        await ctx.reply("*Você não conseguiu nenhuma conquista...*")
        return
    embed = discord.Embed(title=f"🏆 Conquistas [{len(conquistas_obtidas)}/10]",
                          colour=0x00b0f4)

    if "conquista1.toml" in conquistas_obtidas:
        with open(f'profile/{ctx.author.id}/conquistas/conquista1.toml', 'r') as f:
            a_conquista = toml.load(f)
        embed.add_field(name="<:Precoce:1170304359175827476> Eu confio na sorte!",
                        value=f"Apostou todo o dinheiro que tinha na conta\n**Obtido em:** <t:{a_conquista['timestamp']}:f>",
                        inline=True)
    if "conquista2.toml" in conquistas_obtidas:
        with open(f'profile/{ctx.author.id}/conquistas/conquista2.toml', 'r') as f:
            a_conquista = toml.load(f)
        embed.add_field(name="<:socouforte:1174400309498486874> Sem Fanheta...",
                        value=f"Tentou usar o comando NSFW em um canal não habilitado\n**Obtido em:** <t:{a_conquista['timestamp']}:f>",
                        inline=True)
    if "conquista3.toml" in conquistas_obtidas:
        with open(f'profile/{ctx.author.id}/conquistas/conquista3.toml', 'r') as f:
            a_conquista = toml.load(f)
        embed.add_field(name="<:foice:1164982086235594803> Sempre o coadjuvante, nunca o protagonista",
                        value=f"Tentou se casar com alguém que já estava casado\n**Obtido em:** <t:{a_conquista['timestamp']}:f>",
                        inline=True)
    if "conquista4.toml" in conquistas_obtidas:
        with open(f'profile/{ctx.author.id}/conquistas/conquista4.toml', 'r') as f:
            a_conquista = toml.load(f)
        embed.add_field(name="<:DomPedro2:1170304386321358889> Até que a conexão ruim nos separe!",
                        value=f"Se casou pela primeira vez\n**Obtido em:** <t:{a_conquista['timestamp']}:f>",
                        inline=True)
    if "conquista5.toml" in conquistas_obtidas:
        with open(f'profile/{ctx.author.id}/conquistas/conquista5.toml', 'r') as f:
            a_conquista = toml.load(f)
        embed.add_field(name="<:grief:1166038742847471638> Doeu mais em mim do que em você",
                        value=f"Foi chifrado pela primeira vez\n**Obtido em:** <t:{a_conquista['timestamp']}:f>",
                        inline=True)
    if "conquista6.toml" in conquistas_obtidas:
        with open(f'profile/{ctx.author.id}/conquistas/conquista6.toml', 'r') as f:
            a_conquista = toml.load(f)
        embed.add_field(name="<:corvozina:1180386634202615879> Suro",
                        value=f"Falou 'suro' pela primeira vez\n**Obtido em:** <t:{a_conquista['timestamp']}:f>",
                        inline=True)
    if "conquista7.toml" in conquistas_obtidas:
        with open(f'profile/{ctx.author.id}/conquistas/conquista7.toml', 'r') as f:
            a_conquista = toml.load(f)
        embed.add_field(name="<:Pomni:1170330955685298207> Eu te vejo apenas como amigo...",
                        value=f"Foi rejeitado pela primeira vez\n**Obtido em:** <t:{a_conquista['timestamp']}:f>",
                        inline=True)
    if "conquista8.toml" in conquistas_obtidas:
        with open(f'profile/{ctx.author.id}/conquistas/conquista8.toml', 'r') as f:
            a_conquista = toml.load(f)
        embed.add_field(name="<:temumdifintonaminhageladeira:1166038617156767755> Eu não sou a pessoa certa pra você...",
                        value=f"Foi rejeitado pelo {bot_name}\n**Obtido em:** <t:{a_conquista['timestamp']}:f>",
                        inline=True)
    if "conquista9.toml" in conquistas_obtidas:
        with open(f'profile/{ctx.author.id}/conquistas/conquista9.toml', 'r') as f:
            a_conquista = toml.load(f)
        embed.add_field(name="<:amanhavomematar:1167897942405959731> Auto-estima é sempre bom!",
                        value=f"Se shippou consigo mesmo\n**Obtido em:** <t:{a_conquista['timestamp']}:f>",
                        inline=True)
    if "conquista10.toml" in conquistas_obtidas:
        with open(f'profile/{ctx.author.id}/conquistas/conquista10.toml', 'r') as f:
            a_conquista = toml.load(f)
        embed.add_field(name="<:sequisokkkkkk:1168035330377654332> Vai que dá certo né?",
                        value=f"Se shippou com uma pessoa casada\n**Obtido em:** <t:{a_conquista['timestamp']}:f>",
                        inline=True)

    await ctx.reply(embed=embed)


@bot.hybrid_command(name="ajuda", description="Veja os comandos disponíveis!")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def ajuda(ctx):
    embed = discord.Embed(title=f"Menu de ajuda",
                          colour=0x00b0f4)

    embed.add_field(name="Entretenimento", value="d$adivinhar, d$aposta, d$battle, d$cancelamento, d$duelo, d$jogo, d$ppp, d$ppt, d$sabio, d$uwu, d$roll, d$cowsay", inline=True)

    embed.add_field(name="Financeiro", value="d$aposta, d$comprar, d$daily, d$doar, d$investir, d$lojinha, d$perfil, d$premium, d$roleta", inline=True)

    embed.add_field(name="Pessoal", value="d$avatar, d$banner, d$casamento, d$conquistas, d$rank", inline=True)

    embed.add_field(name="Comandos Internos", value="d$ajuda, d$sobre, d$ping", inline=True)

    embed.add_field(name="Administrador", value="d$habilitarcomandos, d$habilitarnsfw, d$habilitarboasvindas, d$desabilitarnsfw, d$desabilitarcomandos, d$desabilitarboasvindas, d$mensagemdeboasvindas", inline=True)

    embed.set_author(name=f"{bot_name}", icon_url=bot.user.display_avatar)

    await ctx.send(embed=embed, delete_after=15)


@bot.hybrid_command(name="roll", description="Rode um dado!")
@app_commands.describe(dice="Quantidade de lados do dado escolhido", times="Quantidade de vezes que o dado vai ser rodado")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def roll(ctx, dice: int, times: int | None = None):
    times = times or 1
    if dice <= 1:
        await ctx.reply("Existe dado de 1 lado?")
        return

    dice_lol = range(1, dice)
    times1 = times
    array = []
    while times1 > 0:
        array.append(random.choice(dice_lol))
        times1 -= 1
    await ctx.reply(f"`{sum(array)}` <-- {array} {times}d{dice}")


@bot.hybrid_command(name="cowsay", description="Faça a vaquinha falar coisas")
@app_commands.describe(phrase="A frase escolhida")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def saycow(ctx, *, phrase: str):
    friend = "cow"
    phrase = phrase
    await ctx.reply(f"```{cowsay.get_output_string(friend, phrase)}```")


@bot.hybrid_command(name="ship", description="O amor está no ar...")
@app_commands.describe(pessoa1="A primeira pessoa", pessoa2="A segunda pessoa")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def ship(ctx, pessoa1: str, pessoa2: str):
    possibilities = range(0, 100)
    if Path(f"ships/{pessoa1}{pessoa2}.toml").exists() is True:
        with open(f'ships/{pessoa1}{pessoa2}.toml', 'r') as f:
            config = toml.load(f)
        the_actual_possibility = config["shipvalue"]
        do_it = False
    else:
        the_actual_possibility = random.choice(possibilities)
        do_it = True
    if the_actual_possibility == 0:
        message = "São inimigos jurados!"
    elif the_actual_possibility <= 20:
        message = "Tem certa inimizade..."
    elif the_actual_possibility <= 50:
        message = "São amigos do peito, mas acho que não servem pra um namoro."
    elif the_actual_possibility <= 70:
        message = "Se os dois quiserem, pode dar certo!"
    elif the_actual_possibility <= 90:
        message = "São almas gêmeas!"
    elif the_actual_possibility <= 100:
        message = "Foram feitos um para o outro!"
    if pessoa1 == f"<@{ctx.author.id}>" and pessoa2 == f"<@{ctx.author.id}>":
        the_actual_possibility = 100
        message = "Amor próprio!"
        do_it = False
        if Path(f"profile/{ctx.author.id}/conquistas/conquista9.toml").exists() is False:
            dar_conquistas(ctx.author.id, "9")
            await ctx.send("**Conquista obtida:** *Auto-estima é sempre bom!*")
    if pessoa1 == f"<@{ctx.author.id}>" and Path(f"profile/{pessoa2.replace('<@', '').replace('>', '')}/casado").is_file() is True:
        if Path(f"profile/{ctx.author.id}/conquistas/conquista10.toml").exists() is False:
            dar_conquistas(ctx.author.id, "10")
            await ctx.send("**Conquista obtida:** *Vai que dá certo né?*")

    message_content = f"""❤️Temos um novo ship na área?❤️
{pessoa1} + {pessoa2}, a probabilidade de vocês darem certo é de... *{the_actual_possibility}%*!
**{message}**"""

    await ctx.send(message_content)
    if do_it is True:
        with open(f'ships/{pessoa1}{pessoa2}.toml', 'w') as f:
            f.write(f"shipvalue = {the_actual_possibility}")


@bot.hybrid_command(name="subornarship", description=f"Suborne o ship do {bot_name}! Caso tenha {coin_name} o suficiente...")
@app_commands.describe(porcentagem="A porcentagem do ship", pessoa="A pessoa pra quem você quer subornar")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def subornarship(ctx, porcentagem: int, pessoa: discord.User):
    current_xp = int(float(open(f"profile/{ctx.author.id}/coins", "r+").read()))
    if current_xp < 100000:

        await ctx.reply(f"Ah mais que triste. Você não tem {coin_name} o suficiente. (Você precisa de 100k)")

        return
    decrease_coins(ctx.author.id, 100000)
    with open(f'ships/<@{ctx.author.id}><@{pessoa.id}>.toml', 'w') as f:
        f.write(f"shipvalue = {porcentagem}")
    await ctx.reply("Suborno aceito. *Não conte pra ninguém...*", ephemeral=True)


# Onlyfans
@bot.hybrid_group(fallback="ajuda")
async def onlyjack(ctx: commands.Context) -> None:
    embed = discord.Embed(title="Onlyfans",
                          description=f"""
COMANDOS DISPONÍVEIS:
- d$onlyjack ver <@user>
Veja a sua página no Onlyjack, ou a de outras pessoas.
- d$onlyjack subscribe [@user]
Se inscreva na página de alguém
- d$onlyjack consumir
Consuma o conteúdo das páginas que você assinou!
- d$onlyjack upload [imagem]
Dê upload de uma Imagem para sua página! (Apenas Imagens são suportadas)
- d$onlyjack preco [1234]
Decida o preço da sua assinatura! (Todas as {coin_name} vai para você.)
- d$onlyjack description [blah blah blah]
Coloque sua descrição personalizada!""",
                          colour=0x00b0f4)

    await ctx.send(embed=embed)


@onlyjack.command(name="ver", description="Ver sua página no Onlyjack")
@app_commands.describe(member="Usuário que você quer ver")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def onlyjack_1(ctx, member: discord.Member | None = None):
    member = member or ctx.author
    checkonlyjack(member.id)

    embed = discord.Embed(title=f"Onlyfans do {member.display_name}",
                          description=open(f"profile/{member.id}/onlyjack/desc", "r+").read(),
                          colour=0x00b0f4)

    embed.set_author(name="Onlyjack")

    embed.add_field(name="Preço",
                    value=f"{open(f'profile/{member.id}/onlyjack/price', 'r+').read()} {coin_name}",
                    inline=True)
    embed.add_field(name="Número de posts",
                    value=open(f"profile/{member.id}/onlyjack/uploads/index", "r+").read(),
                    inline=True)
    embed.add_field(name="Número de subs",
                    value=open(f"profile/{member.id}/onlyjack/subs", "r+").read(),
                    inline=True)

    embed.set_thumbnail(url=member.display_avatar)

    embed.set_footer(text=bot_name,
                     icon_url=bot.user.display_avatar)

    await ctx.send(embed=embed)


@onlyjack.command(name="subscribe", description="Se inscrever em uma página no Onlyjack")
@app_commands.describe(member="Usuário que você quer se inscrever")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def onlyjack_2(ctx, member: discord.Member):
    checkonlyjack(member.id)
    checkonlyjack(ctx.author.id)
    amount = int(open(f"profile/{member.id}/onlyjack/price", "r+").read())
    if Path(f"profile/{ctx.author.id}/onlyjack/subto/{member.id}").exists() is True:
        await ctx.reply("Você já é inscrito nessa página!")
    else:
        if amount > int(open(f"profile/{ctx.author.id}/coins", "r+").read()):
            await ctx.send("Você não tem fundos o suficiente pra completar essa transação. (Dica: d$comprar)")
        else:
            decrease_coins(ctx.author.id, amount)
            increase_coins(member.id, amount)
            os.makedirs(f"profile/{ctx.author.id}/onlyjack/subto/{member.id}")
            current_date = datetime.date.today()
            with open(f'profile/{ctx.author.id}/onlyjack/subto/{member.id}/date', 'w') as f:
                f.write(current_date.isoformat())
            current_subs = int(open(f"profile/{member.id}/onlyjack/subs", "r+").read())
            with open(f'profile/{member.id}/onlyjack/subs', 'w') as f:
                f.write(str(current_subs + 1))
            newdate1 = dateutil.parser.parse(open(f"profile/{ctx.author.id}/onlyjack/subto/{member.id}/date", 'r+'))
            newdate1 = newdate1 + relativedelta(days=30)
            await ctx.reply(f"Parabéns!, Você se increveu no Onlyjack de {member.display_name}! Sua assinatura vence em `{newdate1.strftime('%d/%m')}`", ephemeral=True)
            await member.send("Alguém se inscreveu no seu Onlyjack!")


@onlyjack.command(name="upload", description="Mande conteudo para sua página. (Apenas imagens serão suportadas.)")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def onlyjack_3(ctx, attachment: discord.Attachment):
    checkonlyjack(ctx.author.id)
    if attachment.filename.endswith(('.png', '.gif', '.jpg', '.jpeg')) is False:
        await ctx.reply("O arquivo que você mandou não é um tipo reconhecido pelo discord. (Tipos suportados: png, gif, jpg, jpeg)")
    else:
        current_uploads = int(open(f"profile/{ctx.author.id}/onlyjack/uploads/index", "r+").read())
        with open(f'profile/{ctx.author.id}/onlyjack/uploads/image_{str(current_uploads + 1)}', 'w') as f:
            f.write(attachment.url)
        with open(f'profile/{ctx.author.id}/onlyjack/uploads/index', 'w') as f:
            f.write(str(current_uploads + 1))
        await ctx.reply(f"Você fez upload do arquivo {attachment.filename}!")


@onlyjack.command(name="consumir", description="Consuma conteudo dos criadores aos quais você se inscreveu!")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def onlyjack_4(ctx):
    checkonlyjack(ctx.author.id)
    subbed = os.listdir(f"profile/{ctx.author.id}/onlyjack/subto/")
    if len(subbed) == 0:
        await ctx.send("Você não se inscreveu em nenhuma página...")
    else:
        idx = 0
        text = "Páginas inscritas: (Responda com o número da pagina para selecionar)"
        for item in os.listdir(f"profile/{ctx.author.id}/onlyjack/subto/"):
            idx = idx + 1
            text = text + f"\n{idx} - {bot.get_user(int(item)).name}"

        embed = discord.Embed(title="Páginas inscritas",
                              description=text)

        await ctx.send(embed=embed)

        def sus(m):
            return m.author == ctx.author

        try:
            msg1 = await bot.wait_for('message', check=sus)
        except asyncio.TimeoutError:
            await ctx.send('Visualização cancelada. Tente novamente.')
        else:
            msg1 = int(msg1.content) - 1
            posts_index = int(open(f"profile/{subbed[msg1]}/onlyjack/uploads/index", "r+").read())
            if posts_index == 0:
                await ctx.send("Esse usuário não tem nenhum post...")
            else:
                current_index = 1
                embed = discord.Embed(title=f"{bot.get_user(int(subbed[msg1]))} posts")

                embed.set_image(url=open(f"profile/{subbed[msg1]}/onlyjack/uploads/image_1", "r+").read())
                embed.set_author(name=f"Página 1/{posts_index}:")

                message = await ctx.send(embed=embed)
                # message_id = message.id
                # getting the message object for editing and reacting

                await message.add_reaction("◀️")
                await message.add_reaction("▶️")

                def amogus(reaction, user):
                    return user == ctx.author and str(reaction.emoji) in ["◀️", "▶️"]
                    # This makes sure nobody except the command sender can interact with the "menu"

                while True:
                    try:
                        reaction, user = await bot.wait_for("reaction_add", timeout=15, check=amogus)
                        # waiting for a reaction to be added - times out after x seconds, 60 in this
                        # example

                        if str(reaction.emoji) == "▶️" and current_index != posts_index:
                            current_index = current_index + 1
                            embed = discord.Embed(title=f"{bot.get_user(int(subbed[msg1]))} posts")

                            embed.set_image(url=open(f"profile/{subbed[msg1]}/onlyjack/uploads/image_{current_index}", "r+").read())

                            embed.set_author(name=f"Página {current_index}/{posts_index}:")
                            await message.edit(embed=embed)
                            await message.remove_reaction(reaction, user)

                        elif str(reaction.emoji) == "◀️" and current_index > 1:
                            current_index = current_index - 1
                            embed = discord.Embed(title=f"{bot.get_user(int(subbed[msg1]))} posts")

                            embed.set_image(url=open(f"profile/{subbed[msg1]}/onlyjack/uploads/image_{current_index}", "r+").read())

                            embed.set_author(name=f"Página {current_index}/{posts_index}:")
                            await message.edit(embed=embed)
                            await message.remove_reaction(reaction, user)

                        else:
                            await message.remove_reaction(reaction, user)
                            # removes reactions if the user tries to go forward on the last page or
                            # backwards on the first page
                    except asyncio.TimeoutError:
                        await message.delete()
                        break
                        # ending the loop if user doesn't react after x seconds


@onlyjack.command(name="preco", description="Configure o preço da sua página!")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def onlyjack_5(ctx, number: int):
    checkonlyjack(ctx.author.id)
    with open(f'profile/{ctx.author.id}/onlyjack/price', 'w') as f:
        f.write(str(number))
    await ctx.reply(f"O preço da sua assinatura foi alterada para {number} {coin_name}!")


@onlyjack.command(name="description", description="Configure a descrição da sua página!")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def onlyjack_6(ctx, *, desc: str):
    checkonlyjack(ctx.author.id)
    with open(f'profile/{ctx.author.id}/onlyjack/desc', 'w') as f:
        f.write(str(desc))
    await ctx.reply(f"Sua descrição foi alterada para '{desc}'")


@bot.hybrid_command(name="images", description="Procure por imagens!")
@app_commands.describe(sobre_mim="Sua busca")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def images(ctx, *, sobre_mim: str):
    index = 0
    results = await AsyncDDGS().aimages(sobre_mim, safesearch='on', max_results=20)

    embed = discord.Embed(title=sobre_mim,
                          description=results[index]['title'],
                          colour=0x00b0f4)

    embed.set_image(url=results[index]['image'])
    message = await ctx.send(embed=embed)
    await message.add_reaction("◀️")
    await message.add_reaction("▶️")

    def amogus(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["◀️", "▶️"]
        # This makes sure nobody except the command sender can interact with the "menu"

    while True:
        try:
            reaction, user = await bot.wait_for("reaction_add", timeout=15, check=amogus)
            # waiting for a reaction to be added - times out after x seconds, 60 in this
            # example

            if str(reaction.emoji) == "▶️" and index < 20:
                index = index + 1
                embed = discord.Embed(title=sobre_mim, description=results[index]['title'], colour=0x00b0f4)

                embed.set_image(url=results[index]['image'])
                await message.edit(embed=embed)
                await message.remove_reaction(reaction, user)

            elif str(reaction.emoji) == "◀️" and index > 1:
                index = index - 1
                embed = discord.Embed(title=sobre_mim, description=results[index]['title'], colour=0x00b0f4)

                embed.set_image(url=results[index]['image'])
                await message.edit(embed=embed)
                await message.remove_reaction(reaction, user)
            else:
                await message.remove_reaction(reaction, user)
                # removes reactions if the user tries to go forward on the last page or
                # backwards on the first page
        except asyncio.TimeoutError:
            await message.delete()
            break
            # ending the loop if user doesn't react after x seconds


@bot.hybrid_command(name="gacha", description="Sorteie os cargos do server do R1ck! (Exclusivo para nação AntiCLT)")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def gacha(ctx):
    if ctx.guild.id != 1256346003817369620:
        await ctx.reply("Esse comando é exclusivo para o servidor Nação AntiCLT, pedimos desculpas pelo inconveniente.")
        return
    if ctx.author.id in gacha_array:
        await ctx.reply("Você já tem uma compra em andamento!")
        return

    if random.choice(range(1, 5)) == 3:
        is_m = True
    else:
        is_m = False

    rarity = random.choice(range(1, 100))
    if rarity >= 1 and rarity <= 50:
        if is_m:
            cargo = random.choice(roles.cargos_uma_estrela_m)
            preco = roles.preco_1m
        else:
            cargo = random.choice(roles.cargos_uma_estrela)
            preco = roles.preco_1
        cargo_especial = roles.cargo_especial_uma_estrela
    elif rarity >= 51 and rarity <= 70:
        if is_m:
            cargo = random.choice(roles.cargos_duas_estrelas_m)
            preco = roles.preco_2m
        else:
            cargo = random.choice(roles.cargos_duas_estrelas)
            preco = roles.preco_2
        cargo_especial = roles.cargo_especial_duas_estrelas
    elif rarity >= 71 and rarity <= 80:
        if is_m:
            cargo = random.choice(roles.cargos_tres_estrelas_m)
            preco = roles.preco_3m
        else:
            cargo = random.choice(roles.cargos_tres_estrelas)
            preco = roles.preco_3
        cargo_especial = roles.cargo_especial_tres_estrelas
    elif rarity >= 81 and rarity <= 87:
        if is_m:
            cargo = random.choice(roles.cargos_quatro_estrelas_m)
            preco = roles.preco_4m
        else:
            cargo = random.choice(roles.cargos_quatro_estrelas)
            preco = roles.preco_4
        cargo_especial = roles.cargo_especial_quatro_estrelas
    elif rarity >= 88 and rarity <= 92:
        if is_m:
            cargo = random.choice(roles.cargos_cinco_estrelas_m)
            preco = roles.preco_5m
        else:
            cargo = random.choice(roles.cargos_cinco_estrelas)
            preco = roles.preco_5
        cargo_especial = roles.cargo_especial_cinco_estrelas
    elif rarity >= 93 and rarity <= 96:
        if is_m:
            cargo = random.choice(roles.cargos_seis_estrelas_m)
            preco = roles.preco_6m
        else:
            cargo = random.choice(roles.cargos_seis_estrelas)
            preco = roles.preco_6
        cargo_especial = roles.cargo_especial_seis_estrelas
    elif rarity >= 97 and rarity <= 100:
        if is_m:
            cargo = random.choice(roles.cargos_sete_estrelas_m)
            preco = roles.preco_7m
        else:
            cargo = random.choice(roles.cargos_sete_estrelas)
            preco = roles.preco_7
        cargo_especial = roles.cargo_especial_sete_estrelas
    else:
        cargo = ""
        preco = ""
        cargo_especial = ""

    the_role = {"is_m": is_m, "preco": preco, "cargo": cargo, "cargo_especial": cargo_especial}

    if the_role["is_m"] is True:
        message = f"""**JACKPOT! JACKPOT!**
Você ganhou o cargo **mutado** {the_role['cargo']['nome']} de raridade {the_role['cargo_especial']['nome']}!
Este cargo custa {the_role['preco']}! Reaja a mensagem abaixo para obter este cargo."""
    else:
        message = f"""Você ganhou o cargo {the_role['cargo']['nome']} de raridade {the_role['cargo_especial']['nome']}!
Este cargo custa {the_role['preco']}! Reaja a mensagem abaixo para obter este cargo."""

    message = await ctx.reply(message)
    await message.add_reaction("🧐")
    gacha_array.append(ctx.author.id)

    def amogus(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["🧐"]
        # This makes sure nobody except the command sender can interact with the "menu"

    while True:
        try:
            reaction, user = await bot.wait_for("reaction_add", timeout=10, check=amogus)
            # waiting for a reaction to be added - times out after x seconds, 60 in this
            # example

            if str(reaction.emoji) == "🧐":
                gacha_array.remove(ctx.author.id)
                if int(open(f"profile/{ctx.author.id}/coins", "r+").read()) < the_role['preco']:
                    await ctx.send("Você não tem os recursos necessarios para comprar este cargo. Compra cancelada.")
                    return
                else:
                    if the_role['cargo_especial']['ID'] == None or the_role['cargo']['ID'] == None:
                        await ctx.send(f"Tem algo bem errado com esse cargo {the_role['cargo']['nome']} ou esse cargo: {the_role['cargo_especial']['ID']}...")
                        return
                    if ctx.guild.get_role(the_role['cargo']['ID']) in ctx.author.roles:
                        await ctx.send("Você já tem esse cargo.")
                        return
                    else:
                        await ctx.author.add_roles(ctx.guild.get_role(the_role['cargo']['ID']))
                        if ctx.guild.get_role(the_role['cargo_especial']['ID']) in ctx.author.roles:
                            pass
                        else:
                            await ctx.author.add_roles(ctx.guild.get_role(the_role['cargo_especial']['ID']))

                    decrease_coins(ctx.author.id, the_role['preco'])
                    await ctx.send(f"Você ganhou o cargo {the_role['cargo']['nome']}")

                    break

        except asyncio.TimeoutError:
            gacha_array.remove(ctx.author.id)
            break
            # ending the loop if user doesn't react after x seconds


@bot.hybrid_command(name="chess", description="Desafie os outros para uma partida de xadrez!")
@app_commands.describe(desafiante="A pessoa que você quer desafiar")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def xadrez(ctx, desafiante: discord.Member):

    message = await ctx.send(f"**Atenção {desafiante.mention}, o {ctx.author.mention} quer desafiar você para uma partida de xadrez. Reaja a esta mensagem com um emoji de dedão '👍' em 15 segundos para concordar com a partida.**")
    await message.add_reaction('👍')

    def check(reaction, user):
        return user == desafiante and str(reaction.emoji) == '👍'
    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=15.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send("Partida cancelada.")
    else:
        board = chess.Board()
        boardsvg = chess.svg.board(board)
        f = open(f"{ctx.author.id}{desafiante.id}.svg", "w")
        f.write(boardsvg)
        f.close()
        os.system(f"convert {ctx.author.id}{desafiante.id}.svg {ctx.author.id}{desafiante.id}.png")
        os.remove(f"{ctx.author.id}{desafiante.id}.svg")
        file = discord.File(f"{ctx.author.id}{desafiante.id}.png", filename="board.png")
        await ctx.send(f"Partida: {ctx.author.mention} x {desafiante.mention}\nRegras:\n- Mínimo de 240 segundos para pensar no movimento, caso excedido a partida será cancelada.\n- Você deverá colocar os movimentos conforme o protocolo UCI (Exemplo, `a2a4`, o peão na casa A2 irá se mover para a casa A4.\n\n É a vez de {ctx.author.name}", file=file)

        while True:
            def sus(m):
                return m.author == ctx.author
            while True:
                try:
                    msg2 = await bot.wait_for('message', timeout=240, check=sus)
                except asyncio.TimeoutError:
                    await ctx.send(f'Partida cancelada, {desafiante.mention} vence.')
                    os.remove(f"{ctx.author.id}{desafiante.id}.png")
                    return
                else:
                    if msg2.content == "desistir":
                        await ctx.send(f"O participante desiste. {desafiante.mention} vence.")
                        os.remove(f"{ctx.author.id}{desafiante.id}.png")
                        return
                    try:
                        move = chess.Move.from_uci(msg2.content)
                    except Exception:
                        await ctx.send("Movimento inválido, tente novamente.")
                    else:
                        if move not in board.legal_moves:
                            await ctx.send("Movimento inválido, tente novamente.")
                        else:
                            break

            board.push(move)
            boardsvg = chess.svg.board(board)
            f = open(f"{ctx.author.id}{desafiante.id}.svg", "w")
            f.write(boardsvg)
            f.close()
            os.system(f"convert {ctx.author.id}{desafiante.id}.svg {ctx.author.id}{desafiante.id}.png")
            os.remove(f"{ctx.author.id}{desafiante.id}.svg")
            file = discord.File(f"{ctx.author.id}{desafiante.id}.png", filename="board.png")
            if board.is_checkmate():
                await ctx.send(f"O ganhador é {ctx.author.mention}!", file=file)
                os.remove(f"{ctx.author.id}{desafiante.id}.png")
                return
            elif board.is_stalemate():
                await ctx.send(f"É um empate.", file=file)
                os.remove(f"{ctx.author.id}{desafiante.id}.png")
                return
            elif board.is_insufficient_material():
                await ctx.send(f"Não há mais peças suficientes. É um empate.", file=file)
                os.remove(f"{ctx.author.id}{desafiante.id}.png")
                return
            else:
                await ctx.send(f"É a vez de {desafiante.mention}", file=file)

            def amogus(m):
                return m.author == desafiante
            while True:
                try:
                    msg2 = await bot.wait_for('message', timeout=240, check=amogus)
                except asyncio.TimeoutError:
                    await ctx.send(f'Partida cancelada, {ctx.author.mention} vence.')
                    os.remove(f"{ctx.author.id}{desafiante.id}.png")
                    return
                else:
                    if msg2.content == "desistir":
                        await ctx.send(f"O participante desiste. {ctx.author.mention} vence.")
                        os.remove(f"{ctx.author.id}{desafiante.id}.png")
                        return
                    try:
                        move = chess.Move.from_uci(msg2.content)
                    except Exception:
                        await ctx.send("Movimento inválido, tente novamente.")
                    else:
                        if move not in board.legal_moves:
                            await ctx.send("Movimento inválido, tente novamente.")
                        else:
                            break

            board.push(move)
            boardsvg = chess.svg.board(board)
            f = open(f"{ctx.author.id}{desafiante.id}.svg", "w")
            f.write(boardsvg)
            f.close()
            os.system(f"convert {ctx.author.id}{desafiante.id}.svg {ctx.author.id}{desafiante.id}.png")
            os.remove(f"{ctx.author.id}{desafiante.id}.svg")
            file = discord.File(f"{ctx.author.id}{desafiante.id}.png", filename="board.png")
            if board.is_checkmate():
                await ctx.send(f"O ganhador é {desafiante.mention}!", file=file)
                os.remove(f"{ctx.author.id}{desafiante.id}.png")
                return
            elif board.is_stalemate():
                await ctx.send(f"É um empate.", file=file)
                os.remove(f"{ctx.author.id}{desafiante.id}.png")
                return
            elif board.is_insufficient_material():
                await ctx.send(f"Não há mais peças suficientes. É um empate.", file=file)
                os.remove(f"{ctx.author.id}{desafiante.id}.png")
                return
            else:
                await ctx.send(f"É a vez de {ctx.author.mention}", file=file)

@bot.hybrid_command(name="trabalhar", description="Encare a condução lotada e vá trabalhar")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def work(ctx):
    checkprofile(ctx.author.id)
    message = await ctx.reply(f"Parábens pelo dia de trabalho {ctx.author.mention}, você ganhou **200** Macca. Deseja guardar aonde? (O dinheiro será automaticamente guardado no bolso caso nenhuma opção seja selecionada.\n ")
    # Isso é o pior código que eu já escrevi btw. But gtg
    def sus(m):
        return m.author == ctx.author

    try:
        msg1 = await bot.wait_for('message', check=sus)
    except asyncio.TimeoutError:
        await ctx.send('Visualização cancelada. Tente novamente.')
    else:

        await message.add_reaction("🏦") # Bank
        await message.add_reaction("💸") # Pocket

        def amogus(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["🏦", "💸"]
            # This makes sure nobody except the command sender can interact with the "menu"

        while True:
            try:
                reaction, user = await bot.wait_for("reaction_add", timeout=15, check=amogus)
                # waiting for a reaction to be added - times out after x seconds, 60 in this
                # example

                if str(reaction.emoji) == "🏦": # Bank
                    current_xp = int(float(open(f"profile/{ctx.author.id}/banco", "r+").read())) + 200
                    with open(f'profile/{ctx.author.id}/banco', 'w') as f:
                        f.write(str(int(current_xp)))
                    log_message(f"{ctx.author.id} coins on bank increased to {current_xp}")
                    await message.edit(f"Dinheiro guardado no banco. Seu total é de {current_xp}")
                    await message.remove_reaction(reaction, user)

                elif str(reaction.emoji) == "💸": # Bolso
                    current_xp = int(float(open(f"profile/{ctx.author.id}/bolso", "r+").read())) + 200
                    with open(f'profile/{ctx.author.id}/bolso', 'w') as f:
                        f.write(str(int(current_xp)))
                    log_message(f"{ctx.author.id} coins on pocket increased to {current_xp}")
                    await message.edit(f"Dinheiro guardado no banco. Seu total é de {current_xp}")
                    await message.remove_reaction(reaction, user)

                else:
                    await message.remove_reaction(reaction, user)
                    # removes reactions if the user tries to go forward on the last page or
                    # backwards on the first page
            except asyncio.TimeoutError:
                current_xp = int(float(open(f"profile/{ctx.author.id}/bolso", "r+").read())) + 200
                with open(f'profile/{ctx.author.id}/bolso', 'w') as f:
                    f.write(str(int(current_xp)))
                log_message(f"{ctx.author.id} coins on pocket increased to {current_xp}")
                await message.edit(f"Dinheiro guardado no banco. Seu total é de {current_xp}")
                await message.remove_reaction(reaction, user) # ESSA PORRA DE LSP TÁ DANDO ERRO MAS FODASE EU NÃO LIGO
                break
                # ending the loop if user doesn't react after x seconds
    

# bot.remove_command('help')

with open(sys.argv[1], "r") as f:
    bot_token = f.read().strip()
bot.run(bot_token, log_level=logging.INFO)
