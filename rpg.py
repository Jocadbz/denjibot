from __future__ import annotations
import os
from pathlib import Path
from discord.ext import commands
from discord import app_commands
import discord
import asyncio
import humanize
import datetime as dt
import shutil
import toml
import typing
import traceback
from discord.ui.select import BaseSelect
import time
import random


_t = humanize.i18n.activate("pt_BR")
user_sleep_tasks = {}
bot_name = "Jack Frost"
coin_name = "Jacktitas"

############## BASE VIEW ##############
# Our objectives:
# - Create a view that handles errors
# - Create a view that disables all components after timeout
# - Make sure that the view only processes interactions from the user who invoked the command
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
                "Você não pode mais interagir com este componente.", ephemeral=True
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
        message = f"An error occurred while processing the interaction for {str(item)}:\n```py\n{tb}\n```"
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


def check_rpg(user_sent):
    checkprofile(user_sent)
    if Path(f"profile/{user_sent}/rpg").exists() is False:
        os.makedirs(f"profile/{user_sent}/rpg")
    if Path(f"profile/{user_sent}/rpg/xp").exists() is False:
        with open(f'profile/{user_sent}/rpg/xp', 'w') as f:
            f.write("100")
    if Path(f"profile/{user_sent}/rpg/lv").exists() is False:
        with open(f'profile/{user_sent}/rpg/lv', 'w') as f:
            f.write("1")
    if Path(f"profile/{user_sent}/rpg/missions_count").exists() is False:
        with open(f'profile/{user_sent}/rpg/missions_count', 'w') as f:
            f.write("0")
    if Path(f"profile/{user_sent}/rpg/items").exists() is False:
        os.makedirs(f"profile/{user_sent}/rpg/items")
    if Path(f"profile/{user_sent}/rpg/items/weapons").exists() is False:
        os.makedirs(f"profile/{user_sent}/rpg/items/weapons")
    if Path(f"profile/{user_sent}/rpg/items/armor").exists() is False:
        os.makedirs(f"profile/{user_sent}/rpg/items/armor")
    if Path(f"profile/{user_sent}/rpg/equip").exists() is False:
        os.makedirs(f"profile/{user_sent}/rpg/equip")


def calculate_level_up(current_xp, xp_gained, current_level, base_xp=100):
    """
    Calcula se a pessoa subiu de nível após ganhar XP.

    Parâmetros:
    - current_xp (int): XP atual do usuário.
    - xp_gained (int): XP ganho.
    - current_level (int): Nível atual do usuário.
    - base_xp (int): XP base necessário para o nível 1 (padrão é 100).

    Retorna:
    - tuple: (novo_nível, xp_restante, subiu_de_nível)
    """
    total_xp = current_xp + xp_gained
    level = current_level
    leveled_up = False

    # Função para calcular o XP necessário para o próximo nível
    def xp_for_next_level(level):
        return base_xp * (2 ** (level - 1))

    # Verifica se o usuário subiu de nível
    while total_xp >= xp_for_next_level(level):
        total_xp -= xp_for_next_level(level)
        level += 1
        leveled_up = True

    return leveled_up


def add_weapon(item, user_sent):
    shutil.copyfile(f'rpg/items/weapon/{item}', f'profile/{user_sent}/rpg/items/weapons/{item}')


def add_armor(item, user_sent):
    shutil.copyfile(f'rpg/items/armor/{item}', f'profile/{user_sent}/rpg/items/armor/{item}')


def equip_weapon(item, user_sent):
    shutil.copyfile(f'profile/{user_sent}/rpg/items/weapons/{item}', f'profile/{user_sent}/rpg/equip/weapon.toml')


def equip_armor(item, user_sent):
    shutil.copyfile(f'profile/{user_sent}/rpg/items/armor/{item}', f'profile/{user_sent}/rpg/equip/armor.toml')


async def check_for_news(ctx):
    if Path(f"profile/{ctx.author.id}/rpg/didnt_saw_news").exists() is True:
        await ctx.send("Existem novas notícias. Utilize `/rpg news` para visualizar e remover este anúncio")



def return_names(level_selected):
    dungeon_files = os.listdir(f"rpg/dungeons/{level_selected}/")
    dungeon_names = []
    for file in dungeon_files:
        with open(f'rpg/dungeons/{level_selected}/{file}', 'r') as f:
            dungeon = toml.load(f)
        dungeon_names.append(f"{dungeon['dungeon']['name']} - Rank DHA {dungeon['dungeon']['lv_required']}")

    return dungeon_names



class SuperCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(fallback="rpg")
    async def rpg(self, ctx: commands.Context):
        """This is a hybrid command group."""
        await ctx.send("Bem vindo ao RPG do Jack Frost! Insira `/rpg` para ver todos os comandos disponíveis.")


    @rpg.command(name="news", description="Veja as notícias do RPG")
    async def news(self, ctx: commands.Context):
        checkprofile(ctx.author.id)
        check_rpg(ctx.author.id)
        if Path(f"profile/{ctx.author.id}/rpg/didnt_saw_news").exists() is True:
            os.remove(f"profile/{ctx.author.id}/rpg/didnt_saw_news")
        await ctx.send(content=open('rpg/news', 'r+').read())

    # /foo bar | !foo bar
    @rpg.command(name="status", description="Veja o status do seu personagem")
    async def status(self, ctx: commands.Context):
        checkprofile(ctx.author.id)
        check_rpg(ctx.author.id)
        await check_for_news(ctx)
        if Path(f"profile/{ctx.author.id}/rpg/name").exists() is False:
            await ctx.reply("Você não se registrou ainda. Faça isso com `/rpg register <nome do seu personagem>`")
            return
        with open(f'profile/{ctx.author.id}/rpg/equip/weapon.toml', 'r') as f:
            weapon = toml.load(f)
        with open(f'profile/{ctx.author.id}/rpg/equip/armor.toml', 'r') as f:
            armor = toml.load(f)
        equipped_items = f"Arma: {weapon['item']['name']}\nArmadura: {armor['item']['name']}"
        items_obtained = len(os.listdir(f'profile/{ctx.author.id}/rpg/items/weapons/')) + len(os.listdir(f'profile/{ctx.author.id}/rpg/items/armor/'))
        embed=discord.Embed(title=f"DHA Indentification: {open(f'profile/{ctx.author.id}/rpg/name', 'r+').read()}", color=0x1c71d8)
        embed.add_field(name="Itens Obtidos", value=f"{items_obtained}", inline=True)
        embed.add_field(name="Missões realizadas", value=f"{open(f'profile/{ctx.author.id}/rpg/missions_count', 'r+').read()}", inline=True)
        embed.add_field(name="Itens equipados", value=equipped_items, inline=False)
        embed.add_field(name="XP Atual", value=f"{open(f'profile/{ctx.author.id}/rpg/xp', 'r+').read()}", inline=True)
        embed.add_field(name="Rank da DHA", value=f"{open(f'profile/{ctx.author.id}/rpg/lv', 'r+').read()}", inline=True)
        embed.set_footer(text=f"{bot_name}",
                         icon_url=self.bot.user.display_avatar)
        await ctx.send(embed=embed)

    # /foo baz | !foo baz
    @rpg.command(name="intro", description="Veja uma introdução ao mundo de Da'at")
    async def intro(self, ctx: commands.Context):
        """This is a regular command."""
        checkprofile(ctx.author.id)
        check_rpg(ctx.author.id)
        if Path(f"profile/{ctx.author.id}/rpg/saw_intro").exists() is True:
            await ctx.reply("Você já jogou a intro. Refira-se ao manual para quaisquer dúvidas.")
            return
        await ctx.reply("Bem vindo ao mundo de Da'at. A DHA parabeniza a sua bravura em se candidatar para as fileiras de caçadores. Seu trabalho principal será destruir dêmonios por incursões em Da'at, e manter a paz no nosso mundo. Agora, se registre com `/rpg register` e faça o seu trabalho")
        with open(f"profile/{ctx.author.id}/rpg/saw_intro", 'w') as f:
            f.write("nice")

    @rpg.command(name="register", description="Registre seu personagem")
    @app_commands.describe(nome="O nome do seu personagem")
    async def register(self, ctx: commands.Context, nome: str):
        checkprofile(ctx.author.id)
        check_rpg(ctx.author.id)
        await check_for_news(ctx)
        with open(f"profile/{ctx.author.id}/rpg/name", 'w') as f:
            f.write(nome)

        await ctx.send(f"Bem vindo ao mundo de Da'at, **{nome}**! Você ganhou 1 espada comum e 1 armadura comum.")
        add_weapon("1.toml", ctx.author.id)
        add_armor("1.toml", ctx.author.id)
        equip_armor("1.toml", ctx.author.id)
        equip_weapon("1.toml", ctx.author.id)



    @rpg.command(name="dungeon", description="Vá em uma Aventura!")
    async def dungeon(self, ctx: commands.Context):
        if Path("rpg/no_new_quests").exists() is True:
            await ctx.send("O administrador desabilitou a criação de novas quests. Isto foi feito provavelmente por uma manutenção planejada no servidor. Para mais informações, consulte `/rpg news`")
            return
        user_sent = ctx.author.id
        level_selected = ""
        dungeon_selected = ""

        checkprofile(ctx.author.id)
        check_rpg(ctx.author.id)
        await check_for_news(ctx)
        if Path(f"profile/{user_sent}/rpg/name").exists() is False:
            await ctx.reply("Você não se registrou ainda. Faça isso com `/rpg register <nome do seu personagem>`")
            return

        user_id = ctx.author.id


        # Check if the user already has a task running
        if user_id in user_sleep_tasks:
            task_data = user_sleep_tasks[user_id]
            elapsed = time.monotonic() - task_data["start_time"]
            remaining = task_data["duration"] - elapsed

            if remaining > 0:
                await ctx.send(f"Você já está em uma aventura! {humanize.naturaldelta(dt.timedelta(seconds=remaining))} restantes.")
                return
            else:
                # Task has completed but wasn't cleaned up
                del user_sleep_tasks[user_id]

        # view = Levelselect(ctx.author)
        # view.message = await ctx.send("Select Menu", view=view)
        level_array = os.listdir("rpg/dungeons/")
        index_page = 0
        embed=discord.Embed(title=f"Nível {level_array[index_page]}", description=f"", color=0x1c71d8)
        embed.set_footer(text=f"{bot_name}",
                         icon_url=self.bot.user.display_avatar)
        embed.set_author(name=f"Página {index_page + 1}/{len(level_array)}:")
        message = await ctx.send(content="Reaja com '✅' para selecionar o nível.", embed=embed)
        # getting the message object for editing and reacting

        await message.add_reaction("◀️")
        await message.add_reaction("▶️")
        await message.add_reaction("✅")

        def amogus(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["◀️", "▶️", "✅"]
            # This makes sure nobody except the command sender can interact with the "menu"

        while True:
            while True:
                try:
                    reaction, user = await self.bot.wait_for("reaction_add", timeout=15, check=amogus)
                    # waiting for a reaction to be added - times out after x seconds, 60 in this
                    # example

                    if str(reaction.emoji) == "▶️" and index_page != len(level_array) - 1:
                        index_page = index_page + 1
                        embed=discord.Embed(title=f"Nível {level_array[index_page]}", description=f"", color=0x1c71d8)
                        embed.set_footer(text=f"{bot_name}",
                                         icon_url=self.bot.user.display_avatar)
                        embed.set_author(name=f"Página {index_page + 1}/{len(level_array)}:")
                        await message.edit(embed=embed)
                        await message.remove_reaction(reaction, user)

                    elif str(reaction.emoji) == "◀️" and index_page != 0:
                        index_page = index_page - 1
                        embed=discord.Embed(title=f"Nível {level_array[index_page]}", description=f"", color=0x1c71d8)
                        embed.set_footer(text=f"{bot_name}",
                                         icon_url=self.bot.user.display_avatar)
                        embed.set_author(name=f"Página {index_page + 1}/{len(level_array)}:")
                        await message.edit(embed=embed)
                        await message.remove_reaction(reaction, user)

                    elif str(reaction.emoji) == "✅":
                        level_selected = level_array[index_page]
                        await message.remove_reaction(reaction, user)
                        break
                    else:
                        await message.remove_reaction(reaction, user)
                        # removes reactions if the user tries to go forward on the last page or
                        # backwards on the first page
                except asyncio.TimeoutError:
                    await message.delete()
                    await ctx.send("Escolha de dungeon cancelada.")
                    return
            dungeons_array = os.listdir(f"rpg/dungeons/{level_selected}")
            dungeons_array = sorted(dungeons_array, key=lambda x: int(x.split('.')[0]))
            index_page = 0
            with open(f'rpg/dungeons/{level_selected}/{dungeons_array[index_page]}', 'r') as f:
                dungeon_idk = toml.load(f)
            duration = dungeon_idk['dungeon']['time']
            embed=discord.Embed(title=f"{dungeon_idk['dungeon']['name']}", description=f"{dungeon_idk['dungeon']['description']}", color=0x1c71d8)
            embed.add_field(name="Rank da DHA mínimo", value=f"Rank {dungeon_idk['dungeon']['lv_required']}", inline=True)
            embed.add_field(name="XP Max/Min", value=f"{dungeon_idk['dungeon']['max_xp']}/{dungeon_idk['dungeon']['min_xp']}", inline=True)
            embed.add_field(name="Tempo de missão", value=humanize.naturaldelta(dt.timedelta(seconds=duration)), inline=True)
            embed.set_footer(text=f"{bot_name}",
                             icon_url=self.bot.user.display_avatar)
            embed.set_author(name=f"Página {index_page + 1}/{len(dungeons_array)}:")
            await message.edit(embed=embed)
            while True:
                try:
                    reaction, user = await self.bot.wait_for("reaction_add", timeout=15, check=amogus)
                    # waiting for a reaction to be added - times out after x seconds, 60 in this
                    # example

                    if str(reaction.emoji) == "▶️" and index_page != len(dungeons_array) - 1:
                        index_page = index_page + 1
                        with open(f'rpg/dungeons/{level_selected}/{dungeons_array[index_page]}', 'r') as f:
                            dungeon_idk = toml.load(f)
                        embed=discord.Embed(title=f"{dungeon_idk['dungeon']['name']}", description=f"{dungeon_idk['dungeon']['description']}", color=0x1c71d8)
                        embed.add_field(name="Rank da DHA mínimo", value=f"Rank {dungeon_idk['dungeon']['lv_required']}", inline=True)
                        embed.add_field(name="XP Max/Min", value=f"{dungeon_idk['dungeon']['max_xp']}/{dungeon_idk['dungeon']['min_xp']}", inline=True)
                        embed.add_field(name="Tempo de missão", value=humanize.naturaldelta(dt.timedelta(seconds=duration)), inline=True)
                        embed.set_footer(text=f"{bot_name}",
                                         icon_url=self.bot.user.display_avatar)
                        embed.set_author(name=f"Página {index_page + 1}/{len(dungeons_array)}:")
                        await message.edit(embed=embed)
                        await message.remove_reaction(reaction, user)

                    elif str(reaction.emoji) == "◀️" and index_page != 0:
                        index_page = index_page - 1
                        with open(f'rpg/dungeons/{level_selected}/{dungeons_array[index_page]}', 'r') as f:
                            dungeon_idk = toml.load(f)
                        embed=discord.Embed(title=f"{dungeon_idk['dungeon']['name']}", description=f"{dungeon_idk['dungeon']['description']}", color=0x1c71d8)
                        embed.add_field(name="Rank da DHA mínimo", value=f"Rank {dungeon_idk['dungeon']['lv_required']}", inline=True)
                        embed.add_field(name="XP Max/Min", value=f"{dungeon_idk['dungeon']['max_xp']}/{dungeon_idk['dungeon']['min_xp']}", inline=True)
                        embed.add_field(name="Tempo de missão", value=humanize.naturaldelta(dt.timedelta(seconds=duration)), inline=True)
                        embed.set_footer(text=f"{bot_name}",
                                         icon_url=self.bot.user.display_avatar)
                        embed.set_author(name=f"Página {index_page + 1}/{len(dungeons_array)}:")
                        await message.edit(embed=embed)
                        await message.remove_reaction(reaction, user)

                    elif str(reaction.emoji) == "✅":
                        dungeon_selected = dungeons_array[index_page]
                        await message.remove_reaction(reaction, user)
                        break
                    else:
                        await message.remove_reaction(reaction, user)
                        # removes reactions if the user tries to go forward on the last page or
                        # backwards on the first page
                except asyncio.TimeoutError:
                    await message.delete()
                    await ctx.send("Escolha de dungeon cancelada.")
                    return
            await message.delete()
            break

        with open(f'rpg/dungeons/{level_selected}/{dungeon_selected}', 'r') as f:
            dungeon_idk = toml.load(f)
        duration = dungeon_idk['dungeon']['time']
        if int(open(f'profile/{ctx.author.id}/rpg/lv', 'r+').read()) < dungeon_idk['dungeon']['lv_required']:
            await ctx.send("O seu rank da DHA não é alto o suficiente para essa missão.")
            return
        with open(f'profile/{ctx.author.id}/rpg/equip/armor.toml', 'r') as f:
            equipped_armor = toml.load(f)
        if equipped_armor['item']['effect'] == "None":
            pass
        else:
            # Extract the effect from the equipped armor
            effect = equipped_armor['item']['effect']

            # Check if the effect is in the format "-X% tempo de missão"
            if effect.endswith("tempo de missão"):
                # Extract the percentage value
                percentage = int(effect[1:effect.index("%")])  # Get the number between "-" and "%"

                # Calculate the new duration based on the percentage
                duration -= int(duration * (percentage / 100))
        embed=discord.Embed(title=dungeon_idk['dungeon']['name'], description=f"*{dungeon_idk['dungeon']['description']}*", color=0x1c71d8)
        embed.add_field(name="Rank da DHA mínimo", value=f"Rank {dungeon_idk['dungeon']['lv_required']}", inline=True)
        embed.add_field(name="XP Max/Min", value=f"{dungeon_idk['dungeon']['max_xp']}/{dungeon_idk['dungeon']['min_xp']}", inline=True)
        embed.add_field(name="Tempo de missão", value=humanize.naturaldelta(dt.timedelta(seconds=duration)), inline=True)
        embed.set_footer(text=f"{bot_name}",
                         icon_url=self.bot.user.display_avatar)

        aposta_message = await ctx.send("Estes são os detalhes da missão. Reaja com ✅ para aceitar a missão.", embed=embed)
        await aposta_message.add_reaction('✅')

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == '✅'

        try:
            await self.bot.wait_for('reaction_add', timeout=15.0, check=check)
        except asyncio.TimeoutError:

            await aposta_message.edit(content="Missão cancelada.", embed=None)
        else:
            user_id = ctx.author.id
            quest_file = os.path.join("rpg/current_quests/", f"{user_id}_quest.txt")

            # Check if the user already has a task running
            if user_id in user_sleep_tasks:
                task_data = user_sleep_tasks[user_id]
                elapsed = time.monotonic() - task_data["start_time"]
                remaining = task_data["duration"] - elapsed

                if remaining > 0:
                    await ctx.send(f"Você já está em uma aventura! {humanize.naturaldelta(dt.timedelta(seconds=remaining))} restantes.")
                    return
                else:
                    # Task has completed but wasn't cleaned up
                    del user_sleep_tasks[user_id]


            with open(quest_file, "w") as f:
                f.write(f"Quest started for {ctx.author} with duration {duration} seconds.\n")

            # Start a new task for the user
            user_sleep_tasks[user_id] = {
                "start_time": time.monotonic(),
                "duration": duration,
            }

            await aposta_message.edit(content="A missão começou!", embed=None)

            try:
                await asyncio.sleep(duration)
                with open(f'rpg/dungeons/{level_selected}/{dungeon_selected}', 'r') as f:
                    dungeon_idk = toml.load(f)
                with open(f'profile/{ctx.author.id}/rpg/equip/weapon.toml', 'r') as f:
                    equipped_weapon = toml.load(f)
                results_text = []
                values = list(range(int(dungeon_idk['dungeon']['min_xp']), int(dungeon_idk['dungeon']['max_xp']) + 1))
                xp_gained = random.choice(values)
                if equipped_weapon['item']['effect'] == "None":
                    pass
                else:
                    # Extract the percentage from the effect string
                    effect = equipped_weapon['item']['effect']

                    # Check if the effect is in the format "+X% XP"
                    if effect.endswith("% XP"):
                        # Extract the percentage value
                        percentage = int(effect[:-4])  # Remove the last 4 characters ("% XP") and convert to int

                        # Calculate the XP gained based on the percentage
                        xp_gained += int(xp_gained * (percentage / 100))


                if dungeon_idk['dungeon']['loot'] is False:
                    pass
                else:
                    for weapon in dungeon_idk['dungeon']['real_weapon_loot']:
                        add_weapon(weapon, ctx.author.id)
                    for armor in dungeon_idk['dungeon']['real_armor_loot']:
                        add_armor(armor, ctx.author.id)

                with open(f"profile/{user_sent}/rpg/xp", "r") as f:
                    current_xp = int(float(f.read()))
                with open(f"profile/{user_sent}/rpg/lv", "r") as f:
                    current_lv = int(float(f.read()))
                did_we_lv_up = calculate_level_up(current_xp, xp_gained, current_lv)
                with open(f'profile/{user_sent}/rpg/xp', 'w') as f:
                    f.write(str(current_xp + xp_gained))
                results_text.append(f"XP ganho: {xp_gained}")
                if did_we_lv_up is True:
                    with open(f'profile/{user_sent}/rpg/lv', 'w') as f:
                        f.write(str(current_lv + 1))
                    results_text.append(f"Novo rank da DHA!: {current_lv + 1}")
                if dungeon_idk['dungeon']['loot'] is True:
                    results_text.append(f"Armas ganhas: {' - '.join(dungeon_idk['dungeon']['fake_weapon_loot'])}")
                    results_text.append(f"Armaduras ganhas: {' - '.join(dungeon_idk['dungeon']['fake_armor_loot'])}")

                with open(f"profile/{user_sent}/rpg/missions_count", "r") as f:
                    current_mission = int(float(f.read()))
                with open(f'profile/{user_sent}/rpg/missions_count', 'w') as f:
                    f.write(str(current_mission + 1))

                await ctx.send(f"""Sua quest terminou, {ctx.author.mention}!
Resultados:
{' - '.join(results_text)}""")

            finally:
                # Cleanup the task after completion
                if user_id in user_sleep_tasks:
                    del user_sleep_tasks[user_id]
                if os.path.exists(quest_file):
                    os.remove(quest_file)


    @rpg.command(name="equipar_arma", description="Equipe uma arma")
    async def equipar_arma(self, ctx: commands.Context):
        checkprofile(ctx.author.id)
        check_rpg(ctx.author.id)
        await check_for_news(ctx)
        user_id = ctx.author.id
        if user_id in user_sleep_tasks:
            task_data = user_sleep_tasks[user_id]
            elapsed = time.monotonic() - task_data["start_time"]
            remaining = task_data["duration"] - elapsed

            if remaining > 0:
                await ctx.send("Você não pode trocar o seu equipamento enquanto estiver em uma aventura.")
                return
            else:
                # Task has completed but wasn't cleaned up
                del user_sleep_tasks[user_id]
        if Path(f"profile/{ctx.author.id}/rpg/name").exists() is False:
            await ctx.reply("Você não se registrou ainda. Faça isso com `/rpg register <nome do seu personagem>`")
            return
        index_page = 0
        weapons_list = os.listdir(f'profile/{ctx.author.id}/rpg/items/weapons/')
        with open(f'profile/{ctx.author.id}/rpg/items/weapons/{weapons_list[index_page]}', 'r') as f:
            weapon = toml.load(f)


        embed=discord.Embed(title=f"{weapon['item']['name']}", description=f"{weapon['item']['description']}", color=0x1c71d8)
        embed.add_field(name="Efeito", value=f"{weapon['item']['effect']}", inline=True)
        embed.set_footer(text=f"{bot_name}",
                         icon_url=self.bot.user.display_avatar)
        embed.set_author(name=f"Página {index_page + 1}/{len(weapons_list)}:")

        message = await ctx.send(content="Reaja com '✅' para equipar a arma desejada.", embed=embed)
        # getting the message object for editing and reacting

        await message.add_reaction("◀️")
        await message.add_reaction("▶️")
        await message.add_reaction("✅")

        def amogus(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["◀️", "▶️", "✅"]
            # This makes sure nobody except the command sender can interact with the "menu"

        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=60, check=amogus)
                # waiting for a reaction to be added - times out after x seconds, 60 in this
                # example

                if str(reaction.emoji) == "▶️" and index_page != len(weapons_list) - 1:
                    index_page = index_page + 1
                    with open(f'profile/{ctx.author.id}/rpg/items/weapons/{weapons_list[index_page]}', 'r') as f:
                        weapon = toml.load(f)


                    embed=discord.Embed(title=f"{weapon['item']['name']}", description=f"{weapon['item']['description']}", color=0x1c71d8)
                    embed.add_field(name="Efeito", value=f"{weapon['item']['effect']}", inline=True)
                    embed.set_footer(text=f"{bot_name}",
                                     icon_url=self.bot.user.display_avatar)
                    embed.set_author(name=f"Página {index_page + 1}/{len(weapons_list)}:")
                    await message.edit(embed=embed)
                    await message.remove_reaction(reaction, user)

                elif str(reaction.emoji) == "◀️" and index_page != 0:
                    index_page = index_page - 1
                    with open(f'profile/{ctx.author.id}/rpg/items/weapons/{weapons_list[index_page]}', 'r') as f:
                        weapon = toml.load(f)


                    embed=discord.Embed(title=f"{weapon['item']['name']}", description=f"{weapon['item']['description']}", color=0x1c71d8)
                    embed.add_field(name="Efeito", value=f"{weapon['item']['effect']}", inline=True)
                    embed.set_footer(text=f"{bot_name}",
                                     icon_url=self.bot.user.display_avatar)
                    embed.set_author(name=f"Página {index_page + 1}/{len(weapons_list)}:")
                    await message.edit(embed=embed)
                    await message.remove_reaction(reaction, user)

                elif str(reaction.emoji) == "✅":
                    await ctx.send(content=f"Você equipou {weapon['item']['name']}", embed=None)
                    equip_weapon(weapons_list[index_page], ctx.author.id)
                    await message.delete()
                    break
                else:
                    await message.remove_reaction(reaction, user)
                    # removes reactions if the user tries to go forward on the last page or
                    # backwards on the first page
            except asyncio.TimeoutError:
                break
                # ending the loop if user doesn't react after x seconds


    @rpg.command(name="equipar_armadura", description="Equipe uma armadura")
    async def equipar_armadura(self, ctx: commands.Context):
        checkprofile(ctx.author.id)
        check_rpg(ctx.author.id)
        await check_for_news(ctx)
        user_id = ctx.author.id
        if user_id in user_sleep_tasks:
            task_data = user_sleep_tasks[user_id]
            elapsed = time.monotonic() - task_data["start_time"]
            remaining = task_data["duration"] - elapsed

            if remaining > 0:
                await ctx.send("Você não pode trocar o seu equipamento enquanto estiver em uma aventura.")
                return
            else:
                # Task has completed but wasn't cleaned up
                del user_sleep_tasks[user_id]
        if Path(f"profile/{ctx.author.id}/rpg/name").exists() is False:
            await ctx.reply("Você não se registrou ainda. Faça isso com `/rpg register <nome do seu personagem>`")
            return
        weapons_list = os.listdir(f'profile/{ctx.author.id}/rpg/items/armor/')
        index_page = 0
        with open(f'profile/{ctx.author.id}/rpg/items/armor/{weapons_list[index_page]}', 'r') as f:
            weapon = toml.load(f)


        embed=discord.Embed(title=f"{weapon['item']['name']}", description=f"{weapon['item']['description']}", color=0x1c71d8)
        embed.add_field(name="Efeito", value=f"{weapon['item']['effect']}", inline=True)
        embed.set_footer(text=f"{bot_name}",
                         icon_url=self.bot.user.display_avatar)
        embed.set_author(name=f"Página {index_page + 1}/{len(weapons_list)}:")

        message = await ctx.send(content="Reaja com '✅' para equipar a arma desejada.", embed=embed)
        # getting the message object for editing and reacting

        await message.add_reaction("◀️")
        await message.add_reaction("▶️")
        await message.add_reaction("✅")

        def amogus(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["◀️", "▶️", "✅"]
            # This makes sure nobody except the command sender can interact with the "menu"

        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=60, check=amogus)
                # waiting for a reaction to be added - times out after x seconds, 60 in this
                # example

                if str(reaction.emoji) == "▶️" and index_page != len(weapons_list) - 1:
                    index_page = index_page + 1
                    with open(f'profile/{ctx.author.id}/rpg/items/armor/{weapons_list[index_page]}', 'r') as f:
                        weapon = toml.load(f)


                    embed=discord.Embed(title=f"{weapon['item']['name']}", description=f"{weapon['item']['description']}", color=0x1c71d8)
                    embed.add_field(name="Efeito", value=f"{weapon['item']['effect']}", inline=True)
                    embed.set_footer(text=f"{bot_name}",
                                     icon_url=self.bot.user.display_avatar)
                    embed.set_author(name=f"Página {index_page + 1}/{len(weapons_list)}:")
                    await message.edit(embed=embed)
                    await message.remove_reaction(reaction, user)

                elif str(reaction.emoji) == "◀️" and index_page != 0:
                    index_page = index_page - 1
                    with open(f'profile/{ctx.author.id}/rpg/items/armor/{weapons_list[index_page]}', 'r') as f:
                        weapon = toml.load(f)


                    embed=discord.Embed(title=f"{weapon['item']['name']}", description=f"{weapon['item']['description']}", color=0x1c71d8)
                    embed.add_field(name="Efeito", value=f"{weapon['item']['effect']}", inline=True)
                    embed.set_footer(text=f"{bot_name}",
                                     icon_url=self.bot.user.display_avatar)
                    embed.set_author(name=f"Página {index_page + 1}/{len(weapons_list)}:")
                    await message.edit(embed=embed)
                    await message.remove_reaction(reaction, user)

                elif str(reaction.emoji) == "✅":
                    await ctx.send(content=f"Você equipou {weapon['item']['name']}", embed=None)
                    equip_armor(weapons_list[index_page], ctx.author.id)
                    await message.delete()
                    break
                else:
                    await message.remove_reaction(reaction, user)
                    # removes reactions if the user tries to go forward on the last page or
                    # backwards on the first page
            except asyncio.TimeoutError:
                break
                # ending the loop if user doesn't react after x seconds


    @rpg.command(name="guild", description="Veja o status da sua guilda")
    async def guild(self, ctx: commands.Context):
        checkprofile(ctx.author.id)
        check_rpg(ctx.author.id)
        await check_for_news(ctx)
        if Path(f"profile/{ctx.author.id}/rpg/guild/name").exists() is True:
            members_array = os.listdir(f'profile/{ctx.author.id}/rpg/guild/members/')
            new_members_array = []
            for member in members_array:
                with open(f'profile/{ctx.author.id}/rpg/guild/members/{member}', 'r') as f:
                    temp_guild_member = toml.load(f)
                new_members_array.append(self.bot.get_user(int(temp_guild_member['member']['id'])).global_name)
            embed=discord.Embed(title=f"{open(f'profile/{ctx.author.id}/rpg/guild/name', 'r+').read()}", description=f"*{open(f'profile/{ctx.author.id}/rpg/guild/mantra', 'r+').read()}*", color=0x1c71d8)
            embed.add_field(name="Líder", value=f"{ctx.author.global_name}", inline=False)
            embed.add_field(name="Membros", value=f"{' - '.join(new_members_array)}", inline=True)
            embed.set_footer(text=f"{bot_name}",
                             icon_url=self.bot.user.display_avatar)
            if Path(f"profile/{ctx.author.id}/rpg/guild/championship_winner").exists() is True:
                embed.set_author(name="👑 Atual campeã do torneio de Guildas")
            await ctx.send(embed=embed)
        elif Path(f"profile/{ctx.author.id}/rpg/guild.toml").exists() is True:
            with open(f'profile/{ctx.author.id}/rpg/guild.toml', 'r') as f:
                temp_guild_data = toml.load(f)
            guild_leader = temp_guild_data['guild']['leader_id']
            members_array = os.listdir(f'profile/{guild_leader}/rpg/guild/members/')
            new_members_array = []
            for member in members_array:
                with open(f'profile/{guild_leader}/rpg/guild/members/{member}', 'r') as f:
                    temp_guild_member = toml.load(f)
                new_members_array.append(self.bot.get_user(int(temp_guild_member['member']['id'])).global_name)
            embed=discord.Embed(title=f"{open(f'profile/{guild_leader}/rpg/guild/name', 'r+').read()}", description=f"*{open(f'profile/{guild_leader}/rpg/guild/mantra', 'r+').read()}*", color=0x1c71d8)
            embed.add_field(name="Líder", value=f"{self.bot.get_user(temp_guild_data['guild']['leader_id']).global_name}", inline=False)
            embed.add_field(name="Membros", value=f"{' - '.join(new_members_array)}", inline=True)
            embed.set_footer(text=f"{bot_name}",
                             icon_url=self.bot.user.display_avatar)
            if Path(f"profile/{guild_leader}/rpg/guild/championship_winner").exists() is True:
                embed.set_author(name="👑 Atual campeã do torneio de Guildas")
            await ctx.send(embed=embed)
        else:
            await ctx.send("Hum... parece que você não está em nenhuma guilda. Entre em uma ou crie sua própria.")


    @rpg.command(name="guild_create", description="Crie uma guilda")
    async def guild_create(self, ctx: commands.Context):
        checkprofile(ctx.author.id)
        check_rpg(ctx.author.id)
        await check_for_news(ctx)
        if Path(f"profile/{ctx.author.id}/rpg/guild/name").exists() is True or Path(f"profile/{ctx.author.id}/rpg/guild.toml").exists() is True:
            await ctx.send("Você já tem uma guilda, ou faz parte de uma. Saia da sua guilda atual para criar uma nova.")
            return
        if int(open(f'profile/{ctx.author.id}/coins', 'r+').read()) < 150 or int(open(f'profile/{ctx.author.id}/rpg/lv', 'r+').read()) < 2:
            await ctx.send("Você não possui os requisitos necessários para criar uma guilda (150 de Macca/Rank DHA 2)")
            return
        await ctx.send("Informe o nome da sua guilda:")

        def sus(m):
            return m.author == ctx.author

        try:
            msg1 = await self.bot.wait_for('message', check=sus)
        except asyncio.TimeoutError:
            await ctx.send('Criação de guilda cancelada.')
            return
        else:
            await ctx.send("Agora informe o mantra da sua guilda.")

            try:
                msg2 = await self.bot.wait_for('message', check=sus)
            except asyncio.TimeoutError:
                await ctx.send('Criação de guilda cancelada.')
                return
            else:
                os.makedirs(f"profile/{ctx.author.id}/rpg/guild")
                os.makedirs(f"profile/{ctx.author.id}/rpg/guild/members")
                with open(f'profile/{ctx.author.id}/rpg/guild/name', 'w') as f:
                    f.write(msg1.content)
                with open(f'profile/{ctx.author.id}/rpg/guild/mantra', 'w') as f:
                    f.write(msg2.content)
                decrease_coins(ctx.author.id, 150)
                await ctx.send(f"Parabéns, sua guilda {msg1.content} foi criada.")


    @rpg.command(name="guild_leave", description="Saia da sua guilda")
    async def guild_leave(self, ctx: commands.Context):
        checkprofile(ctx.author.id)
        check_rpg(ctx.author.id)
        await check_for_news(ctx)
        if Path(f"profile/{ctx.author.id}/rpg/guild/name").exists() is True:
            guild_name = open(f'profile/{ctx.author.id}/rpg/guild/name', 'r+').read()
            message = await ctx.send(content=f"Você tem certeza que deseja deletar a guilda {guild_name}? Reaja com ✅ para concordar com a exclusão.")
            # getting the message object for editing and reacting

            await message.add_reaction("✅")

            def amogus(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["◀️", "▶️", "✅"]
                # This makes sure nobody except the command sender can interact with the "menu"

            while True:
                try:
                    reaction, user = await self.bot.wait_for("reaction_add", timeout=60, check=amogus)
                    # waiting for a reaction to be added - times out after x seconds, 60 in this
                    # example

                    if str(reaction.emoji) == "✅":
                        list_of_members = os.listdir(f"profile/{ctx.author.id}/rpg/guild/members/")
                        for guy in list_of_members:
                            with open(f'profile/{ctx.author.id}/rpg/guild/members/{guy}', 'r') as f:
                                guy_data = toml.load(f)
                            os.remove(f"profile/{guy_data['member']['id']}/rpg/guild.toml")
                        shutil.rmtree(f"profile/{ctx.author.id}/rpg/guild")
                        await message.edit(content="Guilda deletada. Todos os membros foram liberados.")
                        # removes reactions if the user tries to go forward on the last page or
                        # backwards on the first page
                except asyncio.TimeoutError:
                    await message.edit("Exclusão da guilda cancelada.")
                    break
        elif Path(f"profile/{ctx.author.id}/rpg/guild.toml").exists() is True:
            with open(f'profile/{ctx.author.id}/rpg/guild.toml', 'r') as f:
                temp_guild_data = toml.load(f)
            guild_leader = temp_guild_data['guild']['leader_id']
            guild_name = open(f'profile/{guild_leader}/rpg/guild/name', 'r+').read()
            message = await ctx.send(content=f"Você tem certeza que deseja sair da guilda {guild_name}? Reaja com ✅ para concordar com a exclusão.")
            # getting the message object for editing and reacting

            await message.add_reaction("✅")

            def amogus(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["◀️", "▶️", "✅"]
                # This makes sure nobody except the command sender can interact with the "menu"

            while True:
                try:
                    reaction, user = await self.bot.wait_for("reaction_add", timeout=60, check=amogus)
                    # waiting for a reaction to be added - times out after x seconds, 60 in this
                    # example

                    if str(reaction.emoji) == "✅":
                        os.remove(f"profile/{guild_leader}/rpg/guild/members/{ctx.author.id}.toml")
                        os.remove(f"profile/{ctx.author.id}/rpg/guild.toml")
                        await message.edit(content="Você saiu da guilda.")
                        # removes reactions if the user tries to go forward on the last page or
                        # backwards on the first page
                except asyncio.TimeoutError:
                    await message.edit("Saída da guilda cancelada.")
                    break
        else:
            await ctx.send("Você não faz parte de nenhuma guilda.")
            return


    @rpg.command(name="guild_invite", description="Convide um membro para sua guild")
    @app_commands.describe(user="O usuário ao qual você quer convidar")
    async def guild_invite(self, ctx: commands.Context, user: discord.User):
        checkprofile(ctx.author.id)
        check_rpg(ctx.author.id)
        checkprofile(user.id)
        check_rpg(user.id)
        await check_for_news(ctx)
        if Path(f"profile/{ctx.author.id}/rpg/guild/name").exists() is False:
            await ctx.send("Você não é dono de nenhuma guilda.")
            return
        guild_name = open(f'profile/{ctx.author.id}/rpg/guild/name', 'r+').read()
        if len(os.listdir(f"profile/{ctx.author.id}/rpg/guild/members/")) == 25:
            await ctx.send("Você já alcançou o limite de membros na sua guilda (25)")
            return
        if int(open(f'profile/{user.id}/rpg/lv', 'r+').read()) < 2:
            await ctx.send(f"Infelizmente, {user.mention} não atende aos requisitos para se juntar a uma guilda (Rank da DHA 2)")
            return
        message = await ctx.send(content=f"Atenção {user.mention}, o/a {ctx.author.mention} quer te convidar para a sua guilda, a {guild_name}. Reaja com ✅ para aceitar.")
        # getting the message object for editing and reacting

        await message.add_reaction("✅")

        def amogus(reaction, user):
            return user == user and str(reaction.emoji) in ["◀️", "▶️", "✅"]
            # This makes sure nobody except the command sender can interact with the "menu"

        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=15, check=amogus)
                # waiting for a reaction to be added - times out after x seconds, 60 in this
                # example

                if str(reaction.emoji) == "✅":
                    with open(f'profile/{ctx.author.id}/rpg/guild/members/{user.id}.toml', 'w') as f:
                        f.write(f"""[member]
id = {user.id}""")
                    with open(f'profile/{user.id}/rpg/guild.toml', 'w') as f:
                        f.write(f"""[guild]
leader_id = {ctx.author.id}""")
                    await message.edit(content="Você se juntou a guilda com sucesso!")
                    return
                    # removes reactions if the user tries to go forward on the last page or
                    # backwards on the first page
            except asyncio.TimeoutError:
                await message.delete()
                await ctx.send("Entrada na guilda cancelada.")
                break

        

async def setup(bot):
    await bot.add_cog(SuperCog(bot))
