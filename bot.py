from __future__ import annotations
import discord
import os
import os.path
import random
from pathlib import Path
from discord.ext import commands
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
from waifuim import WaifuAioClient
import traceback

humanize.activate('pt_BR')


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
chatgptcooldown = []
uwu_array = []
depression = []

# Defining the cooldown.
cooldown_command = 5

# BANNED USERS
banned_users = []

# Useful Functions


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
            await interaction.response.send_message(
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
            await interaction.response.send_message(message, ephemeral=True)
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


def uptime():
    return str(datetime.timedelta(seconds=int(time.time() - BOOT_TIME)))


# Define the XP functions we need.
def increase_xp(user_sent, amount: int):
    checkprofile(user_sent)
    current_xp = int(open(f"profile/{user_sent}/experience", "r+").read())
    with open(f'profile/{user_sent}/experience', 'w') as f:
        f.write(str(current_xp + amount))


def decrease_xp(user_sent, amount: int):
    checkprofile(user_sent)
    current_xp = int(open(f"profile/{user_sent}/experience", "r+").read())
    with open(f'profile/{user_sent}/experience', 'w') as f:
        if current_xp - amount < 0:
            f.write("0")
        else:
            f.write(str(current_xp - amount))


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
    if Path(f"profile/{user_sent}/experience").exists() is False:
        with open(f'profile/{user_sent}/experience', 'w') as f:
            f.write("0")
    if Path(f"profile/{user_sent}/about").exists() is False:
        with open(f'profile/{user_sent}/about', 'w') as f:
            f.write("Uma pessoa legal!")


# Set up command tree Sync
class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()


# Define the fucking modal I hate this thing fucking idiot thing
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
        message = f"Um Erro aconteceu e deu merda:\n```py\n{tb}\n```"
        try:
            await interaction.response.send_message(message, ephemeral=True)
        except discord.InteractionResponded:
            await interaction.edit_original_response(content=message, view=None)
        self.stop()

    @property
    def interaction(self) -> discord.Interaction | None:
        return self._interaction


# The worst command ever
def rank_command(arg1, multiplier):
    if arg1 == "coins":
        the_ranked_array = []
        profiles = os.listdir("profile")
        profiles.remove("727194765610713138")
        for profile in profiles:
            if bot.get_user(int(profile)) is None:
                pass
            else:
                checkprofile(profile)
                coins = open(f"profile/{profile}/coins", "r+").read()
                the_ranked_array.append({'name': f'{bot.get_user(int(profile))}', 'coins': int(coins)})
        newlist = sorted(the_ranked_array, key=lambda d: d['coins'], reverse=True)
        the_array_to_send = []
        the_actual_array = []
        backslash = '\n'
        val = 5 * multiplier
        for idx, thing in enumerate(newlist):
            the_array_to_send.append(f"{idx+1} - {thing['name'].split('#')[0]}: P£ {humanize.intcomma(thing['coins'])}")
        for i in range(val, val + 5):
            the_actual_array.append(the_array_to_send[i])
        thing = f"""
{backslash.join(the_actual_array)}
"""
    elif arg1 == "xp":
        the_ranked_array = []
        profiles = os.listdir("profile")
        for profile in profiles:
            if bot.get_user(int(profile)) is None:
                pass
            else:
                checkprofile(profile)
                coins = open(f"profile/{profile}/experience", "r+").read()
                the_ranked_array.append({'name': f'{bot.get_user(int(profile))}', 'coins': int(coins)})
        newlist = sorted(the_ranked_array, key=lambda d: d['coins'], reverse=True)
        the_array_to_send = []
        the_actual_array = []
        backslash = '\n'
        val = 5 * multiplier
        for idx, thing in enumerate(newlist):
            the_array_to_send.append(f"{idx+1} - {thing['name'].split('#')[0]}: {humanize.intcomma(thing['coins'])} XP")
        for i in range(val, val + 5):
            the_actual_array.append(the_array_to_send[i])

        thing = f"""
{backslash.join(the_actual_array)}
"""
    return thing


def create_commands_folder():
    if Path(f"custom_commands").exists() is False:
        os.makedirs("custom_commands")


# Now This is the bot's code.
# First, define perms, prefix and the rest of useless shit.
intents = discord.Intents.all()
intents.message_content = True
prefixes = "d$", "D$"
client = MyClient(intents=intents)
bot = commands.Bot(command_prefix=prefixes, intents=intents)


# Initiate Bot's log, and define on_message functions.
@bot.event
async def on_ready():
    print(f'Logged on as {bot.user}!')
    await bot.change_presence(activity=discord.CustomActivity(name='Tentando pegar em uns peitos | d$help', emoji='👀'))


# Set up on message stuff
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    elif message.author.bot is True:
        return
    elif "d$" in message.content.lower():
        with open('config_channels.toml', 'r') as f:
            config = toml.load(f)
        if message.channel.id in config["channels"]:
            await message.channel.send(f"O Administrador desabilitou comandos no canal {message.channel.name}", reference=message)
        else:
            create_commands_folder()
            commands = os.listdir("custom_commands")
            command = message.content.lower().replace("d$", "")
            if message.content.lower().replace("d$", "") in commands:
                await message.channel.send(open(f"custom_commands/{command.lower()}", "r+").read())
            else:
                await bot.process_commands(message)
    elif "calcinha" in message.content.lower():
        if "active" in uwu_array:
            jokes = "Quewia tanto OwO tew uma..."
        else:
            jokes = "Queria tanto ter uma..."
        await message.channel.send(jokes)
    elif "peitos" in message.content.lower():
        if "active" in uwu_array:
            jokes = ["PEITOS?!?! aONDE?!?1 *sweats* PEITOS PEITOS PEITOS PEITOS AAAAAAAAAAAAAA", "São >w< tão macios... quewia pegaw em uns peitos...", "EU QUEWO PEITOOOOOOOOOOS", "Sou o maiow fã de peitos do mundo", "E-Eu nwao ligo maisw pwo mundo, só UWU q-qewo peitos"]
        else:
            jokes = ["PEITOS???? AONDE?????? PEITOS PEITOS PEITOS PEITOS AAAAAAAAAAAAAA", "São tão macios... queria pegar em uns peitos...", "EU QUERO PEITOOOOOOOOOOS", "Sou o maior fã de peitos do mundo", "Eu não ligo mais pro mundo, só quero peitos"]
        await message.channel.send(random.choice(jokes))
    else:
        if len(message.content) < 5:
            msg_xp = 0
        else:
            msg_xp = 2
        increase_xp(message.author.id, msg_xp)
        profiles = os.listdir("profile")
        for profile in profiles:
            if Path(f"profile/{profile}/premium").exists() is False:
                pass
            else:
                if bot.get_user(int(profile)) not in bought_two:
                    bought_two.append(bot.get_user(int(profile)))
                if bot.get_user(int(profile)) not in bought_four:
                    bought_four.append(bot.get_user(int(profile)))
                newdate1 = dateutil.parser.parse(open(f"profile/{profile}/premium/date", 'r+'))
                if newdate1 + relativedelta(days=7) <= datetime.datetime.now():
                    shutil.rmtree(f"profile/{profile}/premium")
                    await bot.get_user(int(profile)).send("Opa, só passando pra avisar que seu premium expirou. Compre mais pra continuar aproveitando os benefícios!")
                    bought_two.remove(bot.get_user(int(profile)))
                    bought_four.remove(bot.get_user(int(profile)))

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
    elif isinstance(error, discord.ext.commands.CommandError):
        await ctx.reply("Oops! Infelizmente aconteceu um erro no comando :(")
        embed = discord.Embed(title=':x: Event Error', colour=0xe74c3c)
        embed.add_field(name='Event', value=error)
        embed.description = '```py\n%s\n```' % traceback.format_exc()
        embed.timestamp = datetime.datetime.utcnow()
        await bot.get_user(727194765610713138).send(embed=embed)


@bot.event
async def on_error(event, *args, **kwargs):
    embed = discord.Embed(title=':x: Event Error', colour=0xe74c3c)
    embed.add_field(name='Event', value=event)
    embed.description = '```py\n%s\n```' % traceback.format_exc()
    embed.timestamp = datetime.datetime.utcnow()
    await bot.get_user(727194765610713138).send(embed=embed)


# Let's do something
async def on_member_join(member):
    if Path(f"welcome_message").exists() is False:
        with open(f'welcome_message', 'w') as f:
            f.write("Uma pessoa nova entrou! Bem vindo {{user}}!")
    if Path(f"welcome_channel.toml").exists() is False:
        with open(f'welcome_channel.toml', 'w') as f:
            f.write("channels = []")

    with open('welcome_channel.toml', 'r') as f:
        channels = toml.load(f)

    if len(channels["channels"]) <= 0:
        pass
    else:
        for channel in channels["channels"]:
            channel_to_send = bot.get_channel(channel)
            channel_to_send.send(open(f"welcome_message", "r+").read().replace("{{user}}", f"{member.mention}"))


####################################################################################
# COMANDOS DE ADMINISTRADOR
####################################################################################

@bot.command()
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def sync(ctx):
    if ctx.author.id == 727194765610713138:
        await ctx.bot.tree.sync()
        print(f'Commands Synced!')
        await ctx.reply("Comandos sincronizados")
    else:
        await ctx.send("Ei, você não é o Joca, SAI FORA!")


@bot.hybrid_command(name="increasexp", description="Aumenta um XP de um usuário")
@app_commands.describe(quantidade="Quantidade de XP", usuário="Usuário escolhido")
@commands.has_permissions(administrator=True)
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def increasexp(ctx, quantidade: int, usuário: discord.Member) -> None:
    increase_xp(usuário.id, quantidade)
    await ctx.send(f"Adicionou {humanize.intcomma(quantidade)} XP para {usuário.display_name}")


# UWU COMMAND
# Enables the UwU mode Nya!
@bot.hybrid_command(name="decreasexp", description="Diminui o XP de um usuário")
@app_commands.describe(quantidade="Quantidade de XP", usuário="Usuário escolhido")
@commands.has_permissions(administrator=True)
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def decreasexp(ctx, quantidade: int, usuário: discord.Member):
    decrease_xp(usuário.id, quantidade)
    await ctx.send(f"Removeu {humanize.intcomma(quantidade)} XP de {usuário.display_name}")


@bot.hybrid_command(name="habilitarnsfw", description="DEIXE A FANHETA LIVRE")
@commands.has_permissions(administrator=True)
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def habilitarnsfw(ctx) -> None:
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
    if Path(f"welcome_channel.toml").exists() is False:
        with open(f'welcome_channel.toml', 'w') as f:
            f.write("channels = []")
    with open('welcome_channel.toml', 'r') as f:
        config = toml.load(f)

    if ctx.channel.id in config["channels"]:
        config["channels"].append(ctx.channel.id)
    else:
        pass

    with open('config_channels.toml', 'w') as f:
        toml.dump(config, f)

    await ctx.reply(f"Mensagem de boas vindas habilitados no canal {ctx.channel} (Use d$desabilitarboasvindas para desabilitar.)")


@bot.hybrid_command(name="desabilitarboasvindas", description="Desabilitar a mensagem de boas vindas em um canal específico")
@commands.has_permissions(administrator=True)
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def desabilitarboasvindas(ctx) -> None:
    if Path(f"welcome_channel.toml").exists() is False:
        with open(f'welcome_channel.toml', 'w') as f:
            f.write("channels = []")
    with open('welcome_channel.toml', 'r') as f:
        config = toml.load(f)

    if ctx.channel.id not in config["channels"]:
        config["channels"].remove(ctx.channel.id)
    else:
        pass

    with open('config_channels.toml', 'w') as f:
        toml.dump(config, f)

    await ctx.reply(f"Mensagem de boas vindas desativados no canal {ctx.channel} (Use d$habilitarboasvindas para habilitar.)")


class TagModal(BaseModal, title="Mensagem de boas vindas"):
    tag_content = discord.ui.TextInput(label="A mensagem", placeholder="Lembre-se que {{user}} vai mencionar o novo usuário!", min_length=1, max_length=300, style=discord.TextStyle.long)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        with open(f'welcome_message', 'w') as f:
            f.write(self.tag_content.value)
        message = open(f"welcome_message", "r+").read().replace("{{user}}", "{usuário mencionado}")
        await interaction.response.send_message(f"Sua mensagem foi registrada! ela vai ficar assim:\n\n{message}", ephemeral=True)
        await super().on_submit(interaction)


@bot.hybrid_command(name="mensagemdeboasvindas", description="Editar a mensagem de boas vindas")
@commands.has_permissions(administrator=True)
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def mensagemdeboasvindas(ctx: discord.ApplicationContext):
    if Path(f"welcome_message").exists() is False:
        with open(f'welcome_message', 'w') as f:
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
    the_user = bot.get_user(int("727194765610713138"))
    embed = discord.Embed(title='DenjiBot', colour=0x00b0f4)
    embed.set_thumbnail(url=bot.user.display_avatar)
    embed.add_field(name="Tempo Ligado:", value=uptime(), inline=True)
    embed.set_footer(text="Feito por Jocadbz",
                     icon_url=the_user.display_avatar)
    await ctx.send(embed=embed)


@bot.hybrid_command(name="uwu", description="Ative o modo UWU")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def uwu(ctx):
    if 'active' in uwu_array:
        uwu_array.remove("active")
        await ctx.reply("Modo UWU desativado!")
    else:
        uwu_array.append("active")
        await ctx.reply("Modo UWU Ativado!")


# Battle Command
# Simmulates an idiotic battle between two concepts.
@bot.hybrid_command(name="battle", description="Simula uma batalha")
@app_commands.describe(arg1="Pessoa um", arg2="Pessoa Dois")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def battle(ctx, arg1: str, arg2: str) -> None:
    rand1 = [0, 1]
    if "active" in uwu_array:
        if random.choice(rand1) == 0:
            comeco = ["Foi pow pouco, mas ", "E com gwande fowga ", "Foi uma wuta justa, mas "]
            fim = ["esmagando seu c-cwânyio", "abwindo um buwaco em seu peito.", "decepando s-s-sua cabeça."]
            jokes = f"{random.choice(comeco)}{arg1} ganhow a l-luta contwa {arg2} {random.choice(fim)}"
            await ctx.send(jokes)
        else:
            comeco = ["Foi pow pouco, mas ", "E com gwande fowga ", "Foi uma wuta justa, mas "]
            fim = ["esmagando seu c-cwânyio", "abwindo um buwaco em seu peito.", "decepando s-s-sua cabeça.", "desintegwando seu cowpo.", "sewwando seu c-cowpo ao meio."]
            jokes = f"{random.choice(comeco)}{arg2} ganhow a l-luta contwa {arg1} {random.choice(fim)}"
            await ctx.send(jokes)
    else:
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
    if "active" in uwu_array:
        motivos = ["sew ;;w;; atwaente d-demais", "tew chawme d-demais", "sew ;;w;; uma pessoa howwívew", "sew ;;w;; uma gwande gostosa", "sew ;;w;; boy wixo", "sew ;;w;; comunyista", "debochaw *blushes* demais sew intewigente d-demais", "sew ;;w;; p-padwãozinho", "pediw ^w^ muito biscoito", "sew ;;w;; cownyo sew uma dewícia", "sew ;;w;; gado d-demais", "não sew nyinguém", "sew ;;w;; posew", "sew ;;w;; insupowtávew", "sew ;;w;; insensívew", "não fazew nyada", "sew ;;w;; twouxa", "se atwasaw", "sempwe sew impaciente d-demais", "tew viwado o Cowonga", "sew ;;w;; BV", "tew muita pweguiça", "sew ;;w;; inútiw", "sew ;;w;; inyadimpwente >w< nyo S-Sewasa", "contaw muita piada wuim", "pwocwastinyaw d-demais", "pow se considewaw incancewávew"]
        await ctx.send(f"{ctx.author.mention} foi cancewado pow {random.choice(motivos)}")
    else:
        motivos = ["ser atraente demais", "ter charme demais", "ser uma pessoa horrível", "ser uma grande gostosa", "ser boy lixo", "ser comunista", "debochar demais ser inteligente demais", "ser padrãozinho", "pedir muito biscoito", "ser corno ser uma delícia", "ser gado demais", "não ser ninguém", "ser poser", "ser insuportável", "ser insensível", "não fazer nada", "ser trouxa", "se atrasar", "sempre ser impaciente demais", "ter virado o Coronga", "ser BV", "ter muita preguiça", "ser inútil", "ser inadimplente no Serasa", "contar muita piada ruim", "procrastinar demais", "por se considerar incancelável"]
        await ctx.send(f"{ctx.author.mention} foi cancelado por {random.choice(motivos)}")


# SÁBIO
# Obtenha respostas para as questões mais importantes da vida.
@bot.hybrid_command(name="sabio", description="Obtenha as respostas para todas as questões da vida")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def sabio(ctx):
    if "active" in uwu_array:
        jokes = ["SIM, C-C-COM TODA CEWTEZA", "Sim, >w< com cewteza.", "Sim.", "Pwovavewmente.", "Não sei dizew.", "Pwovavewmente não.", "Não.", 'Com c-cewteza n-não.', "NÃO, C-C-COM TODA CEWTEZA NÃO", "O Padowa é-é quem decide UWU"]
    else:
        jokes = ["SIM, COM TODA CERTEZA", "Sim, com certeza.", "Sim.", "Provavelmente.", "Não sei dizer.", "Provavelmente não.", "Não.", 'Com certeza não.', "NÃO, COM TODA CERTEZA NÃO", "O Padola decide."]
    await ctx.send(random.choice(jokes))


# PPT
# Declaração de amor via Discord... que brega.
@bot.hybrid_command(name="ppt", description="Declare seu amor!")
@app_commands.describe(lover="Seu amado")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def ppt(ctx, lover: discord.Member) -> None:
    if 'active' in uwu_array:
        jokes = f"Cawo/Cawa {lover}, o {ctx.author.mention} gostawia de d-decwawaw seus sentimentos a você."
    else:
        jokes = f"Caro/Cara {lover}, o {ctx.author.mention} gostaria de declarar seus sentimentos a você."
    await ctx.send(jokes)


# Jogo
# Simulação do jogo de futebol do seu time. Que você sabe que vai perder.
@bot.hybrid_command(name="jogo", description="Deixe o bot decidir o resultado do jogo do seu time de coração")
@app_commands.describe(time1="Time Um", time2="Time dois")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def jogo(ctx, time1: str, time2: str) -> None:
    rand1 = [0, 1, 2, 3, 4, 5]
    if "active" in uwu_array:
        jokes = f"O wesuwtado da pawtida de {time1} x {time2} vai sew {random.choice(rand1)} x {random.choice(rand1)} UWU"
    else:
        jokes = f"O resultado da partida de {time1} x {time2} vai ser {random.choice(rand1)} x {random.choice(rand1)}"
    await ctx.send(jokes)


# Comprar
# Cobrando por PadolaCoins KKKKKKKKKKKKKKK.
@bot.hybrid_command(name="comprar", description="Informações sobre a compra de PadolaCoins")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def comprar(ctx):
    thing = """Ficou sem dinheiro apostando com o ADM? Agora você pode realizar a compra de PadolaCoins!
Comprar PadolaCoins é um jeito de ajudar o bot a continuar online, ajuda o criador a pagar as contas, e principalmente, nos ajuda a continuar desenvolvendo!

Para comprar, chame o criador do DenjiBot (@jocadbz) na DM. O valor é negociável."""
    await ctx.send(thing)
    await ctx.send("https://tenor.com/view/mlem-silly-goofy-cat-silly-cat-goofy-gif-27564930")


# Comprar
# Cobrando por PadolaCoins KKKKKKKKKKKKKKK.
@bot.hybrid_command(name="premium", description="Informações sobre a compra do Premium")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def premium(ctx):
    if Path(f"profile/{ctx.author.id}/premium").exists() is False:
        thing = """Agora ficou ainda mais fácil de ganhar beneficíos no Denji. O Premium é um jeito barato, rápido, e fácil de ostentar para os pobres.
Os benefícios incluem:
- 100K De PadolaCoins
- O DOBRO de dinheiro no d$daily
- Todos os benefícios da lojinha permanentemente
- Perfil diferenciado

O preço estabelecido é de R$2/Semana (50% OFF!!). Para realizar a compra, chame @jocadbz na DM."""
        await ctx.reply(f"{thing}\nhttps://cdn.discordapp.com/attachments/1164700096668114975/1175195963636322334/image0.gif?ex=656a5987&is=6557e487&hm=1e638b6daaa7c3f5661b8356b67eadae6231b7220b6cb25ecd5c0612e98dd514&")
    else:
        newdate1 = dateutil.parser.parse(open(f"profile/{ctx.author.id}/premium/date", 'r+'))
        newdate1 = newdate1 + relativedelta(days=7)
        embed = discord.Embed(title="Premium",
                              colour=0xf5c211)

        embed.set_author(name=f"Bem vindo {ctx.author.display_name}",
                         icon_url=ctx.author.display_avatar.url)

        embed.add_field(name="Data",
                        value=f"Seu premium acaba em {newdate1.strftime('%d/%m')}",
                        inline=True)

        embed.set_footer(text="Denji",
                         icon_url=bot.user.display_avatar.url)

        await ctx.reply(embed=embed)


# Ping
# Não estamos nos referindo ao esporte.
@bot.hybrid_command(name="ping", description="Teste a latência do bot")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def ping(ctx):
    if round(bot.latency * 1000) <= 50:
        embed = discord.Embed(title="Ping", description=f":ping_pong: Pingpingpingpingping! O ping é de **{round(bot.latency *1000)}** millisegundos!", color=0x44ff44)
    elif round(bot.latency * 1000) <= 100:
        embed = discord.Embed(title="Ping", description=f":ping_pong: Pingpingpingpingping! O ping é de **{round(bot.latency *1000)}** millisegundos!", color=0xffd000)
    elif round(bot.latency * 1000) <= 200:
        embed = discord.Embed(title="Ping", description=f":ping_pong: Pingpingpingpingping! O ping é de **{round(bot.latency *1000)}** millisegundos!", color=0xff6600)
    else:
        embed = discord.Embed(title="Ping", description=f":ping_pong: Pingpingpingpingping! O ping é de **{round(bot.latency *1000)}** millisegundos!", color=0x990000)
    await ctx.send(embed=embed)


# DAILY
# Win 100 PadolaCoins every 40 minutes.
@bot.hybrid_command(name="daily", description="Ganhe PadolaCoins diários")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def daily(ctx):
    checkprofile(ctx.author.id)

    if ctx.author in daily_cooldown:
        if 'active' in uwu_array:
            await ctx.send("opaaa ÚwÚ pewa *cries* w-wá, você já pegou seus PadolaCoins diáwios. Espewe m-mais um tempo pawa pegaw nyovamente. *sweats* (Dica UWU: d$comprar)")
        else:
            await ctx.send("Opaaa pera lá, você já pegou seus PadolaCoins diários. Espere mais um tempo para pegar novamente. (Dica: d$comprar)")

    else:
        current_coins = open(f"profile/{ctx.author.id}/coins", "r+").read()
        if Path(f"profile/{ctx.author.id}/premium").exists() is True:
            new_coins = int(current_coins) + 2200
            if 'active' in uwu_array:
                await ctx.send(f"Você ganhou 2200 PadowaCoins?!?1 (Bônyus de Pwemium)")
            else:
                await ctx.send(f"Você ganhou 2200 PadolaCoins! (Bônus de Premium)")
        else:
            new_coins = int(current_coins) + 1100
            if 'active' in uwu_array:
                await ctx.send(f"Você ganhou 1100 PadowaCoins?!?1")
            else:
                await ctx.send(f"Você ganhou 1100 PadolaCoins!")
        with open(f'profile/{ctx.author.id}/coins', 'w') as f:
            f.write(str(new_coins))
        daily_cooldown.append(ctx.author)
        await asyncio.sleep(2500)
        daily_cooldown.remove(ctx.author)


# Profile
# Check User Profile
@bot.hybrid_command(name="profile", description="Verifique o seu perfil e o de outros usuários")
@app_commands.describe(rsuser="O Usuário para verificar o perfil")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
# TODO: Try to find a way of reducing code in this specific command.
async def profile(ctx, rsuser: discord.User | None = None):
    rsuser = rsuser or None
    if rsuser is not None:
        # TODO: Fix the fact that this gets ignored if we throw any letters at it.
        user_sent = rsuser.id
        if bot.get_user(int(user_sent)) is None:
            await ctx.send(f"Tem certeza de que esse user existe?")
            return
    else:
        user_sent = ctx.author.id
    checkprofile(user_sent)

    if Path(f"profile/{user_sent}/premium").exists() is True:
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
    embed.add_field(name="Padola Coins",
                    value=f"""P£ {humanize.intcomma(open(f"profile/{user_sent}/coins", "r+").read())}""",
                    inline=False)
    embed.add_field(name="Pontos de Experiência",
                    value=f"""{humanize.intcomma(open(f"profile/{user_sent}/experience", "r+").read())} XP""",
                    inline=False)
    embed.add_field(name="Apostas vencidas",
                    value=f"""{open(f"profile/{user_sent}/duelos", "r+").read()}""",
                    inline=False)
    embed.add_field(name="Duelos Mortalmente Mortais",
                    value=f"""Ganhou {open(f"profile/{user_sent}/duelos_vencidos", "r+").read()} - Perdeu {open(f"profile/{user_sent}/duelos_perdidos", "r+").read()}""",
                    inline=False)

    embed.set_thumbnail(url=bot.get_user(int(user_sent)).display_avatar)

    embed.set_footer(text="Denji-kun Bot",
                     icon_url=bot.user.display_avatar)
    await ctx.reply(embed=embed)


# Escolhas da Lojinha
class Item(str, enum.Enum):
    Item_1 = "1"
    Item_2 = "2"
    Item_3 = "3"


# Lojinha
@bot.hybrid_command(name="lojinha", description="Verifique os itens da lojinha")
@app_commands.describe(arg1="O Item para comprar")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def lojinha(ctx, arg1: Item | None = None):
    arg1 = arg1 or None
    checkprofile(ctx.author.id)
    if arg1 == "1":
        current_coins = open(f"profile/{ctx.author.id}/coins", "r+").read()
        if int(current_coins) >= 500:
            new_coins = int(current_coins) - 500
            with open(f'profile/{ctx.author.id}/coins', 'w') as f:
                f.write(str(new_coins))
            if "active" in uwu_array:
                await ctx.send("Você compwou o benyefício 1.")
            else:
                await ctx.send("Você comprou o benefício 1.")
            bought_two.append(ctx.author)
            await asyncio.sleep(2500)  # time in seconds
            bought_two.remove(ctx.author)
        else:
            if "active" in uwu_array:
                await ctx.send("Ah mais que triste. Você não tem PadolaCoins o suficiente. (Dica: d$comprar)")
            else:
                await ctx.send("A-Ah, m-mais que twiste!!11 você não tem PadowaCoins o suficiente. *looks at you* (Dica UWU: d$comprar)")
    elif arg1 == "2":
        current_coins = open(f"profile/{ctx.author.id}/coins", "r+").read()
        if int(current_coins) >= 10000:
            if "active" in uwu_array:
                await ctx.send("Você compwou o benyefício 2. Pwimeiwamente, wesponda a essa mensagem com o nyome do comando. (Exempwo, se você cowocaw 'exampwe', seu comando vai sew 'cd$exampwe')")
            else:
                await ctx.send("Você comprou o benefício 2. Primeiramente, responda a essa mensagem com o nome do comando. (Exemplo, se você colocar 'example', seu comando vai ser 'cd$example')")

            def sus(m):
                return m.author == ctx.author

            try:
                msg1 = await bot.wait_for('message', check=sus)
            except asyncio.TimeoutError:
                await ctx.send('Compra cancelada. Tente novamente.')
            else:
                array = ["adivinhar", "ajuda", "avatar", "battle", "cancelamento", "casamento", "comprar", "daily", "darpremium", "doar", "duelo", "help", "investir", "jogo", "lojinha", "nsfw", "ping", "ppp", "ppt", "premium", "profile", "rank", "rinha", "roleta", "sabio", "sobre", "sync", "uwu"]
                if msg1.content.lower() in array:
                    await ctx.reply("Oops, esse comando já existe.")
                    return
                else:
                    if Path(f"custom_commands/{msg1.content.lower()}").exists() is True:
                        await ctx.reply("Oops, esse comando já existe.")
                        return
                if "active" in uwu_array:
                    await ctx.send("gowa, wesponda a essa mensagem com o que você quew que o comando mande (GIFs, mensagens, etc)")
                else:
                    await ctx.send("Agora, responda a essa mensagem com o que você quer que o comando mande (GIFs, mensagens, etc)")

                def sus(m):
                    return m.author == ctx.author

                try:
                    msg2 = await bot.wait_for('message', check=sus)
                except asyncio.TimeoutError:
                    await ctx.send('Compra cancelada. Tente novamente.')
                else:
                    await ctx.send('Comando registrado.')
                    new_coins = int(current_coins) - 10000
                    with open(f'profile/{ctx.author.id}/coins', 'w') as f:
                        f.write(str(new_coins))
                    with open(f'custom_commands/{msg1.content.lower()}', 'w') as f:
                        f.write(msg2.content)
        else:
            if "active" not in uwu_array:
                await ctx.send("Ah mais que triste. Você não tem PadolaCoins o suficiente. (Dica: d$comprar)")
            else:
                await ctx.send("A-Ah, m-mais que twiste!!11 você não tem PadowaCoins o suficiente. *looks at you* (Dica UWU: d$comprar)")
    elif arg1 == "3":
        current_coins = open(f"profile/{ctx.author.id}/coins", "r+").read()
        if int(current_coins) >= 1500:
            new_coins = int(current_coins) - 1500
            with open(f'profile/{ctx.author.id}/coins', 'w') as f:
                f.write(str(new_coins))
            if "active" in uwu_array:
                await ctx.send("Você compwou o benyefício 3.")
            else:
                await ctx.send("Você comprou o benefício 3.")
            bought_four.append(ctx.author)
            await asyncio.sleep(2500)  # time in seconds
            bought_four.remove(ctx.author)
        else:
            if "active" not in uwu_array:
                await ctx.send("Ah mais que triste. Você não tem PadolaCoins o suficiente. (Dica: d$comprar)")
            else:
                await ctx.send("A-Ah, m-mais que twiste!!11 você não tem PadowaCoins o suficiente. *looks at you* (Dica UWU: d$comprar)")

    elif arg1 is None:
        if "active" in uwu_array:
            embed = discord.Embed(title="wojinha *huggles tightly* do Denji",
                                  description="compwe >w< benyefícios :3 com seus Padowa *walks away* Coins aqui?!?! - Mande o comando 'd$lojinha <numero>' pawa compwaw!!11 *screeches*",
                                  colour=0x00b0f4)

            embed.add_field(name="I - Rinha e d-duelo Coowdown Wemuvw UWU",
                            value="Não seja afetado pewo coowdown das apostas e d-duelo pow 40 m-minyutos - 500 PadowaCoins",
                            inline=False)
            embed.add_field(name="II - C-Comando customizado",
                            value="cowoque :3 um comando customizado com seu usewnyame ;;w;; - 10,000 PadowaCoins",
                            inline=False)
            embed.add_field(name="III - Sonyegaw impostos",
                            value="Seja um fowa da wei e pague zewo impostos nya s-suas twansfewencias pow 40 m-minyutos - 1,500 PadowaCoins",
                            inline=False)

            embed.set_footer(text="Denji-kun Bot",
                             icon_url=bot.user.display_avatar)
        else:
            embed = discord.Embed(title="Lojinha do Denji",
                                  description="Compre benefícios com seus Padola Coins aqui! - Mande o comando '$lojinha <numero>' para comprar!",
                                  colour=0x00b0f4)

            embed.add_field(name="I - Rinha e Duelo Cooldown Remover",
                            value="Não seja afetado pelo cooldown das apostas e duelos por 40 minutos - 500 PadolaCoins",
                            inline=False)
            embed.add_field(name="II - Comando customizado",
                            value="Coloque um comando customizado com seu username - 10,000 PadolaCoins",
                            inline=False)
            embed.add_field(name="III - Sonegar impostos",
                            value="Seja um fora da lei e pague zero impostos na suas transferencias por 40 minutos - 1,500 PadolaCoins",
                            inline=False)

            embed.set_footer(text="Denji-kun Bot",
                             icon_url=bot.user.display_avatar)

        await ctx.send(embed=embed)


# Investir
# Perder ou ganhar? É o bot quem decide.
@bot.hybrid_command(name="investir", description="O lobo de Wall Street")
@app_commands.describe(arg1="A quantidade para investir")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def investir(ctx, arg1: int) -> None:
    checkprofile(ctx.author.id)

    investir_random = ["win", "lose", "lose", "lose", "win", "lose", "win", "lose"]
    resultado = random.choice(investir_random)
    win_thing = [4, 10, 2, 2, 4, 5]
    win_thing = random.choice(win_thing)

    if arg1 > int(open(f"profile/{ctx.author.id}/coins", "r+").read()):
        if 'active' in uwu_array:
            await ctx.send("Você não tem fundos o s-suficiente pwa i-investiw. (Dica UWU: d$comprar)")
        else:
            await ctx.send("Você não tem fundos o suficiente pra investir. (Dica: d$comprar)")
    else:
        if resultado == "win":
            if 'active' in uwu_array:
                await ctx.send(f"Você wucwou {humanize.intcomma(str(win_thing).replace('0.', ''))}%! seu ^w^ wucwo totaw :3 foi {int(int(arg1)*win_thing / 100)} PadowaCoins!")
            else:
                await ctx.send(f"Você lucrou {humanize.intcomma(str(win_thing).replace('0.', ''))}%! Seu lucro total foi {int(int(arg1)*win_thing / 100)} PadolaCoins!")
            current_coins = open(f"profile/{ctx.author.id}/coins", "r+").read()
            new_coins = int(round(int(arg1) * win_thing / 100))
            new_coins = int(int(current_coins) + new_coins)
            with open(f'profile/{ctx.author.id}/coins', 'w') as f:
                f.write(str(new_coins))
        else:
            if 'active' in uwu_array:
                await ctx.send(f"Você pewdeu {humanize.intcomma(str(win_thing).replace('0.', ''))}%! Suas pewdas totais fowam *twerks* {int(round(int(arg1)*win_thing / 100))} PadowaCoins... Boa sowte nya pwóxima...")
            else:
                await ctx.send(f"Você perdeu {humanize.intcomma(str(win_thing).replace('0.', ''))}%! Suas perdas totais foram {int(round(int(arg1)*win_thing / 100))} PadolaCoins... Boa sorte na próxima...")
            current_coins = open(f"profile/{ctx.author.id}/coins", "r+").read()
            new_coins = int(round(int(arg1) * win_thing / 100))
            new_coins = int(int(current_coins) - new_coins)
            with open(f'profile/{ctx.author.id}/coins', 'w') as f:
                f.write(str(new_coins))


# Roleta
# Roda a Roda jequiti
@bot.hybrid_command(name="roleta", description="Roda a Roda Jequiti")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def roleta(ctx):
    checkprofile(ctx.author.id)
    roleta_random = [1100, 110, 150, 1200, 0, 1100, 110, 110, 1400, 1400, 1200, 1200, 1100, 1100, 110, 1200, 0, 0, 1400]
    resultado = random.choice(roleta_random)

    if ctx.author in roleta_cooldown:
        if 'active' in uwu_array:
            await ctx.send("opaaa ÚwÚ pewa *cries* w-wá, você já pegou seu giwo. Espewe m-mais um tempo pawa pegaw nyovamente. *sweats* (Dica UWU: d$comprar)")
        else:
            await ctx.send("Opaaa pera lá, você já pegou seu giro. Espere mais um tempo para pegar novamente. (Dica: d$comprar)")

    else:
        if 'active' in uwu_array:
            await ctx.send(f"O wesuwtado da s-s-sua w-woweta foi... {resultado} PadowaCoins?!?1")
        else:
            await ctx.send(f"O resultado da sua roleta foi... {resultado} PadolaCoins!")
            current_coins = open(f"profile/{ctx.author.id}/coins", "r+").read()
            new_coins = int(current_coins) + resultado
            with open(f'profile/{ctx.author.id}/coins', 'w') as f:
                f.write(str(new_coins))
            roleta_cooldown.append(ctx.author)
            await asyncio.sleep(2000)
            roleta_cooldown.remove(ctx.author)


# Doar
# MrBeast
@bot.hybrid_command(name="doar", description="Doe dinheiro para pessoas!")
@app_commands.describe(amount="A quantidade de PadolaCoins", user="A Pessoa para quem você quer doar")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def doar(ctx, amount: int, user: discord.Member):
    checkprofile(ctx.author.id)
    if bot.get_user(user.id) is None:
        await ctx.send("Tem certeza de que esse user existe?")
    else:
        checkprofile(user.id)
        if amount > int(open(f"profile/{ctx.author.id}/coins", "r+").read()):
            if 'active' in uwu_array:
                await ctx.send("Você não tem fundos o s-suficiente pwa compwetaw essa t-twansação. (Dica UWU: d$comprar)")
            else:
                await ctx.send("Você não tem fundos o suficiente pra completar essa transação. (Dica: d$comprar)")
        else:
            current_coins = open(f"profile/{ctx.author.id}/coins", "r+").read()
            new_coins = int(current_coins) - amount
            if ctx.author in bought_four:
                imposto = 0
            else:
                imposto = round(amount) * 0.05
            current_coins_user = open(f"profile/{user.id}/coins", "r+").read()
            new_coins_user = int(current_coins_user) + amount
            new_coins_user = new_coins_user - imposto
            joca_coins = int(open(f"profile/727194765610713138/coins", "r+").read()) + imposto
            with open(f'profile/{ctx.author.id}/coins', 'w') as f:
                f.write(str(int(new_coins)))
            with open(f'profile/{user.id}/coins', 'w') as f:
                f.write(str(int(new_coins_user)))
            with open(f'profile/727194765610713138/coins', 'w') as f:
                f.write(str(int(joca_coins)))
            if ctx.author not in bought_four:
                if "active" in uwu_array:
                    await ctx.send(f"Você twansfewiu *looks at you* {humanize.intcomma(amount)} :3 Padowa *walks away* coins pawa {user.mention}! (imposto cobwado: {str(int(imposto))} PadowaCoins)")
                    await ctx.send(f"compwe >w< o benyefício 4 nya d$wojinha pawa não pagaw ^w^ impostos?!!")
                else:
                    await ctx.send(f"Você transferiu {humanize.intcomma(amount)} Padola coins para {user.mention}! (Imposto cobrado: {str(int(imposto))} PadolaCoins)")
                    await ctx.send(f"Compre o benefício 4 na d$lojinha para não pagar impostos!")
            else:
                if "active" in uwu_array:
                    await ctx.send(f"Você twansfewiu *looks at you* {humanize.intcomma(amount)} :3 Padowa *walks away* coins pawa {user.mention}! (Sem impostos cobwados *notices buldge*)")
                else:
                    await ctx.send(f"Você transferiu {humanize.intcomma(amount)} Padola coins para {user.mention}! (Sem impostos cobrados)")


@bot.hybrid_command(name="adivinhar", description="Adivinhe um número e ganhe sonhos... ou perca eles...")
@app_commands.describe(amount="A quantia que você quer apostar", number="O número em qual você quer apostar")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def adivinhar(ctx, amount: int, number: app_commands.Range[int, 0, 10]):
    possibilities = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    checkprofile(ctx.author.id)
    if amount > int(open(f"profile/{ctx.author.id}/coins", "r+").read()):
        if 'active' in uwu_array:
            await ctx.reply("me *screeches* pawece que você não pode cobwiw essa aposta... (Dica UWU: d$comprar)")
        else:
            await ctx.reply("Me parece que você não pode cobrir essa aposta... (Dica: d$comprar)")
    else:
        if number == random.choice(possibilities):
            if 'active' in uwu_array:
                await ctx.reply(f"Pawabéns!!11 Você acewtou, e ganhou {humanize.intcomma(amount)}!")
            else:
                await ctx.reply(f"Parabéns! Você acertou, e ganhou {humanize.intcomma(amount)}!")
            current_coins_user = open(f"profile/{ctx.author.id}/coins", "r+").read()
            new_coins_user = int(current_coins_user) + amount
            with open(f'profile/{ctx.author.id}/coins', 'w') as f:
                f.write(str(int(new_coins_user)))
        else:
            if 'active' in uwu_array:
                await ctx.reply(f"Poxa!!11 Você pewdeu  {humanize.intcomma(amount)}...")
            else:
                await ctx.reply(f"Poxa! Você perdeu {humanize.intcomma(amount)}...")
            current_coins_user = open(f"profile/{ctx.author.id}/coins", "r+").read()
            new_coins_user = int(current_coins_user) - amount
            with open(f'profile/{ctx.author.id}/coins', 'w') as f:
                f.write(str(int(new_coins_user)))


@bot.hybrid_command(name="rinha", description="Perca sua fortuna apostando!")
@app_commands.describe(amount="A quantidade de PadolaCoins", user="A Pessoa com quem você quer apostar")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def rinha(ctx, amount: int, user: discord.Member):
    blah = user
    checkprofile(ctx.author.id)
    if ctx.author in rinha_cooldown:
        if 'active' in uwu_array:
            await ctx.send("opaaa ÚwÚ pewa *cries* w-wá, você já apostou. Espewe m-mais um tempo pawa pegaw nyovamente. *sweats* (Dica: Você pode puwaw esse coowdown compwando o benyefício 2 nya d$wojinha)")
        else:
            await ctx.send("Opaaa pera lá, você já apostou. Espere o cooldown acabar. (Dica: Você pode pular esse cooldown comprando o benefício 2 na d$lojinha)")
    else:
        if amount > int(open(f"profile/{ctx.author.id}/coins", "r+").read()):
            if 'active' in uwu_array:
                await ctx.send("Você não tem fundos o s-suficiente pwa apostaw UWU (Dica UWU: d$comprar)")
            else:
                await ctx.send("Você não tem fundos o suficiente pra apostar. (Dica: d$comprar)")
        else:
            if user.id == ctx.author.id:
                if 'active' in uwu_array:
                    await ctx.send("Você não pode apostaw com você mesmo.")
                else:
                    await ctx.send("Você não pode apostar com você mesmo.")
            else:
                checkprofile(user.id)
                if amount > int(open(f"profile/{user.id}/coins", "r+").read()):
                    if 'active' in uwu_array:
                        await ctx.send("me *screeches* pawece que seu o-oponyente não pode cobwiw essa aposta... (Dica UWU: d$comprar)")
                    else:
                        await ctx.send("Me parece que seu oponente não pode cobrir essa aposta... (Dica: d$comprar)")
                else:
                    if 'active' in uwu_array:
                        aposta_message = await ctx.send(f"**Atenção {user.mention}, *screeches* o {ctx.author.mention} quew apostaw {humanize.intcomma(amount)} :3 PadowaCoins com você. Weaja a esta mensagem com um e-emoji de d-dedão '👍' em 15 segundos pawa concowdaw com a aposta.**")
                    else:
                        aposta_message = await ctx.send(f"**Atenção {user.mention}, o {ctx.author.mention} quer apostar {humanize.intcomma(amount)} PadolaCoins com você. Reaja a esta mensagem com um emoji de dedão '👍' em 15 segundos para concordar com a aposta.**")
                    await aposta_message.add_reaction('👍')

                    def check(reaction, user):
                        return user == blah and str(reaction.emoji) == '👍'
                    try:
                        reaction, user = await bot.wait_for('reaction_add', timeout=15.0, check=check)
                    except asyncio.TimeoutError:
                        if 'active' in uwu_array:
                            await ctx.send("Aposta c-cancewada UWU")
                        else:
                            await ctx.send("Aposta cancelada")
                    else:
                        things = ["win", "lose", "win", "lose", "win", "lose", "win", "lose", "win", "lose"]
                        resultado = random.choice(things)
                        # You see this text down here? Pretty messy heh?
                        # The first thing you will think of doing is removing those useless variables, but here is the catch: It doesn't work without them.
                        # The code has a absolutely stroke, so I don't reccoment changing anything here.
                        if resultado == 'win':
                            if 'active' in uwu_array:
                                await aposta_message.edit(content=f"O Ganhadow foi...\n{ctx.author.mention}!!11 Pawabéns, você ganhou {humanize.intcomma(amount)} :3 PadowaCoins?!?1")
                            else:
                                await aposta_message.edit(content=f"O Ganhador foi...\n{ctx.author.mention}! Parabéns, você ganhou {humanize.intcomma(amount)} PadolaCoins!")
                            current_coins = open(f"profile/{ctx.author.id}/coins", "r+").read()
                            new_coins = int(current_coins) + amount
                            current_coins_user = open(f"profile/{user.id}/coins", "r+").read()
                            new_coins_user = int(current_coins_user) - amount
                            with open(f'profile/{ctx.author.id}/coins', 'w') as f:
                                f.write(str(new_coins))
                            with open(f'profile/{user.id}/coins', 'w') as f:
                                f.write(str(new_coins_user))
                            current_duels_user = open(f"profile/{ctx.author.id}/duelos", "r+").read()
                            new_duels_user = int(current_duels_user) + 1
                            with open(f'profile/{ctx.author.id}/duelos', 'w') as f:
                                f.write(str(new_duels_user))

                        else:
                            if 'active' in uwu_array:
                                await aposta_message.edit(content=f"O Ganhadow foi...\n{user.mention}!!11 Pawabéns, você ganhou {humanize.intcomma(amount)} :3 PadowaCoins?!?1")
                            else:
                                await aposta_message.edit(content=f"O Ganhador foi...\n{user.mention}! Parabéns, você ganhou {humanize.intcomma(amount)} PadolaCoins!")
                            current_coins = open(f"profile/{ctx.author.id}/coins", "r+").read()
                            new_coins = int(current_coins) - amount
                            current_coins_user = open(f"profile/{user.id}/coins", "r+").read()
                            new_coins_user = int(current_coins_user) + amount
                            with open(f'profile/{ctx.author.id}/coins', 'w') as f:
                                f.write(str(new_coins))
                            with open(f'profile/{user.id}/coins', 'w') as f:
                                f.write(str(new_coins_user))
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
        if 'active' in uwu_array:
            await ctx.send("O Tiwan- digo, ADM do Sewvew mandou tiwaw esse comando do G-Gewaw. Foi maw?!?1")
        else:
            await ctx.send("O Tiran- digo, ADM do Server mandou tirar esse comando do Geral. Foi mal!")
    else:
        if ctx.author in rinha_cooldown:
            if 'active' in uwu_array:
                await ctx.send("opaaa ÚwÚ pewa *cries* w-wá, você já duelou. Espewe m-mais um tempo pawa pegaw nyovamente. *sweats* (Dica: Você pode puwaw esse coowdown compwando o benyefício 2 nya d$lojinha)")
            else:
                await ctx.send("Opaaa pera lá, você já duelou. Espere o cooldown acabar. (Dica: Você pode pular esse cooldown comprando o benefício 2 na d$lojinha)")
        else:
            if user.id == ctx.author.id:
                if 'active' in uwu_array:
                    await ctx.send("Você não pode duewaw contwa você mesmo.")
                else:
                    await ctx.send("Você não pode duelar contra você mesmo.")
            else:
                checkprofile(user.id)
                if 'active' in uwu_array:
                    aposta_message = await ctx.send(f"**Atenção {user.mention}, *screeches* o {ctx.author.mention} quew duelaw :3 com você. Weaja a esta mensagem com um e-emoji de e-espada '⚔️' em 15 segundos pawa concowdaw com o d-duelo.**")
                else:
                    aposta_message = await ctx.send(f"**Atenção {user.mention}, o {ctx.author.mention} quer duelar com você. Reaja a esta mensagem com um emoji de espada '⚔️' em 15 segundos para concordar com o duelo.**")
                await aposta_message.add_reaction('⚔️')

                def check(reaction, user):
                    return user == blah and str(reaction.emoji) == '⚔️'

                try:
                    reaction, user = await bot.wait_for('reaction_add', timeout=15.0, check=check)
                except asyncio.TimeoutError:
                    if 'active' in uwu_array:
                        await ctx.send("Duelo c-cancewada UWU")
                    else:
                        await ctx.send("Duelo cancelada")
                else:
                    resultado = random.choice(["win", "lose"])
                    if resultado == 'win':
                        if 'active' in uwu_array:
                            await aposta_message.edit(content=f"O Ganhadow foi...\n{ctx.author.mention}!!11 Pawabéns, você ganhou o d-duelo!")
                        else:
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
                        if 'active' in uwu_array:
                            await aposta_message.edit(content=f"O Ganhadow foi...\n{user.mention}!!11 Pawabéns, você ganhou o d-duelo!")
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


# Ajuda
# O comando de ajuda
@bot.command()
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def ajuda(ctx):
    texto = """```
Guia de comandos:
- d$duelo <pessoa>
Inicia um duelo amigável.

- d$rinha <quantidade> <pessoa>
Aposta PadolaCoins com outra pessoa.

- d$doar <quantidade> <pessoa>
Transfere PadolaCoins para outra pessoa.

- d$roleta
Gire a roleta para ganhar PadolaCoins.

- d$lojinha
Uma lojinha para gastar seus PadolaCoins

- d$profile
Verifique seu perfil.

- d$daily
Ganhe seus PadolaCoins diários.

- d$suro, d$fanho, d$reze69
Cada um invoca um GIF diferente.

- d$comprar
Obtenha informações de como comprar PadolaCoins.

- d$jojo <time1> <time2>
Simule uma partida de futebol.

- d$sabio <pergunta>
Deixe o sábio responder a sua pergunta.

- d$battle <fighter1> <fighter2>
Simule uma batalha entre dois oponentes.

- d$rank <xp ou coins>
Calcule os top 5 mais ricos do servidor.

- d$uwu
A-Ative o modo UWU

- d$avatar <pessoa>
Veja o avatar de alguém.

- d$casamento <casar ou divorciar> <pessoa>
Casamento no discord... que brega...

### Apenas para Mods ###

- d$increasexp <quantidade> <pessoa>
Aumenta a quantidade de XP de uma pessoa.

- d$decreasexp <quantidade> <pessoa>
Diminui a quantidade de XP de uma pessoa.
```
"""
    await ctx.author.send(texto)


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


@bot.hybrid_group(fallback="ajuda")
async def casamento(ctx: commands.Context) -> None:
    embed = discord.Embed(title="Casamento",
                          description="Comandos disponíveis:\n\n- `casar`\n- `divorciar`",
                          colour=0x00b0f4)

    await ctx.send(embed=embed)


@casamento.command(name="casar")
async def casamento_1(ctx: commands.Context, user: discord.Member) -> None:
    blah = user
    checkprofile(ctx.author.id)
    checkprofile(user.id)
    if user.id == 1167643852786638889:
        await ctx.reply("Olha... eu te vejo só como amigo... me desculpa...")
    else:
        if Path(f"profile/{user.id}/casado").is_file() is True:
            if 'active' in uwu_array:
                await ctx.send(f"Essa pessoa já está casada *screams* com awguém...")
            else:
                await ctx.send(f"Essa pessoa já está casada com alguém...")
        else:
            if Path(f"profile/{ctx.author.id}/casado").is_file() is True:
                if 'active' in uwu_array:
                    await ctx.send(f"Você já é casado!!11")
                else:
                    await ctx.send(f"Você já é casado!")
                other = bot.get_user(int(open(f"profile/{ctx.author.id}/casado", "r+").read()))
                await other.send(f"Não é querendo ser fofoqueiro... mais o {ctx.author.display_name} tentou se casar com outra pessoa... 👀👀👀")
            else:
                if ctx.author in depression:
                    if 'active' in uwu_array:
                        await ctx.send(f"Você está em depwessão?!! Espewe m-mais um tempo pawa se casaw...")
                    else:
                        await ctx.send(f"Você está em depressão! Espere mais um tempo para se casar...")
                if 'active' in uwu_array:
                    aposta_message = await ctx.send(f"**Atenção {user.mention}, *screeches* o {ctx.author.mention} gostawia de se c-c-casaw com você. Weaja a essa mensagem com um e-emoji de casamento (💒) pawa concowdaw com a cewimônyia.**")
                else:
                    aposta_message = await ctx.send(f"**Atenção {user.mention}, o {ctx.author.mention} gostaria de se casar com você. Reaja a essa mensagem com um emoji de casamento (💒) para concordar com a cerimônia.**")
                await aposta_message.add_reaction('💒')

                def check(reaction, user):
                    return user == blah and str(reaction.emoji) == '💒'

                try:
                    reaction, user = await bot.wait_for('reaction_add', timeout=15.0, check=check)
                except asyncio.TimeoutError:
                    if 'active' in uwu_array:
                        await aposta_message.edit(content=f"Casamento cancewado?!?1 {ctx.author.display_name} agowa entwou em depwessão...")
                    else:
                        await aposta_message.edit(content=f"Casamento cancelado! {ctx.author.display_name} agora entrou em depressão...")
                    depression.append(ctx.author)
                    await asyncio.sleep(60)
                    depression.remove(ctx.author)
                else:
                    embed = discord.Embed(title=f"💍 {ctx.author.display_name} agora é casado com {user.display_name}! 💍",
                                          colour=0x00b0f4)

                    embed.set_image(url="https://cdn.discordapp.com/attachments/1164700096668114975/1172541249077653514/image0.gif?ex=6560b122&is=654e3c22&hm=02abfda2588e3a62874ba2c16ea8e579bf5dba86b197bfc2fd36478e8ac6832f&")

                    await aposta_message.edit(embed=embed, content="")
                    with open(f'profile/{user.id}/casado', 'w') as f:
                        f.write(str(ctx.author.id))
                    with open(f'profile/{ctx.author.id}/casado', 'w') as f:
                        f.write(str(user.id))


@casamento.command(name="divorciar")
async def casamento_2(ctx: commands.Context) -> None:
    if Path(f"profile/{ctx.author.id}/casado").is_file() is True:
        other = bot.get_user(int(open(f"profile/{ctx.author.id}/casado", "r+").read()))
        await other.send(f"O {ctx.author.display_name} se divorciou de você! 💔")
        os.remove(f"profile/{ctx.author.id}/casado")
        os.remove(f"profile/{other.id}/casado")
        await ctx.send(f"Você se divorciou de {other.display_name}... 💔")
    else:
        await ctx.send("Você nem é casado!")


@bot.hybrid_command(name="rank", description="Veja o Rank de XP ou de PadolaCoins")
@app_commands.describe(arg1="Ver o rank de XP ou de PadolaCoins?")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def rank(ctx, arg1: Literal["coins", "xp"] | None = None):
    arg1 = arg1 or "coins"
    if arg1 == 'coins':
        ranked_arg = 'coins'
        another_thing = 'ricos'
    elif arg1 == 'xp':
        ranked_arg = 'xp'
        another_thing = 'experientes'
    else:
        await ctx.send("Argumento não reconhecido; Mudando para 'coins'")
        another_thing = 'ricos'
        ranked_arg = 'coins'

    pages = round(len(os.listdir("profile")) / 5) - 1
    cur_page = 1
    embed = discord.Embed(title=f"Os mais {another_thing} do servidor:",
                          description=rank_command(ranked_arg, cur_page - 1),
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
                command = rank_command(ranked_arg, cur_page - 1)
                embed = discord.Embed(title=f"Os mais {another_thing} do servidor:",
                                      description=command,
                                      colour=0x00b0f4)

                embed.set_author(name=f"Página {cur_page}:")
                await message.edit(embed=embed)
                await message.remove_reaction(reaction, user)

            elif str(reaction.emoji) == "◀️" and cur_page > 1:
                cur_page = cur_page - 1
                command = rank_command(ranked_arg, cur_page - 1)
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
            current_date = datetime.date.today()
            with open(f'profile/{user.id}/premium/date', 'w') as f:
                f.write(current_date.isoformat())
            current_coins_user = open(f"profile/{user.id}/coins", "r+").read()
            new_coins_user = int(current_coins_user) + 100000
            with open(f'profile/{user.id}/coins', 'w') as f:
                f.write(str(new_coins_user))
            if 'active' in uwu_array:
                await ctx.send(f"pawabéns *sweats* {user.mention}, você agowa é pwemium?!! Você já pode a-apwuvitaw todos os benyefícios, e P£ *blushes* 100K já fowam *twerks* twansfewidos pawa s-s-sua conta. Obwigado pow apoiaw o Denji?!?!")
            else:
                await ctx.send(f"Parabéns {user.mention}, você agora é premium! Você já pode aproveitar todos os benefícios, e P£ 100K já foram transferidos para sua conta. Obrigado por apoiar o Denji!")
    else:
        await ctx.send("Você não é o ADM...")


@bot.hybrid_command(name="nsfw", description="Pra Garantir a Famosa Fanheta")
@app_commands.describe(tag="Suas Tags preferidas hehehe")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def nsfw(ctx, tag: Literal["ass", "hentai", "milf", "oral", "paizuri", "ecchi", "ero"] | None = None):
    if Path(f"config_nsfw.toml").exists() is False:
        with open(f'config_nsfw.toml', 'w') as f:
            f.write("channels = []")
    with open("config_nsfw.toml", mode="r") as fp:
        config = toml.load(fp)
    if ctx.channel.id in config["channels"]:
        arg1 = tag or None
        wf = WaifuAioClient()
        if arg1 is None:
            images = await wf.search(
                is_nsfw='True',
            )
        else:
            images = await wf.search(
                included_tags=[arg1],
                is_nsfw='True',
            )
        embed = discord.Embed(title="NSFW")

        embed.set_image(url=images.url)

        await ctx.reply(embed=embed)
    else:
        await ctx.reply("O Administrador não autorizou o uso desse comando neste canal.")


@bot.hybrid_command(name="ppp", description="Pego, penso e passo")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def ppp(ctx):
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
                if int(open(f"profile/{member.id}/experience", "r+").read()) >= 500:
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


@bot.hybrid_command(name="sobremim", description="Edite seu perfil")
@app_commands.describe(sobre_mim="O texto que vai estar no seu perfil")
@commands.cooldown(1, cooldown_command, commands.BucketType.user)
async def sobremim(ctx, *, sobre_mim: str):
    checkprofile(ctx.author.id)
    if len(sobre_mim) > 300:
        await ctx.reply("Sua descrição é longa demais...", ephemeral=True)
        return
    with open(f'profile/{ctx.author.id}/about', 'w') as f:
        f.write(sobre_mim)
    await ctx.reply("Seu perfil foi atualizado!", ephemeral=True)

bot.run(open(f"token", "r+").read(), log_level=logging.INFO)
