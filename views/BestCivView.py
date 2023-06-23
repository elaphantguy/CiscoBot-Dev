import nextcord
from nextcord import ButtonStyle
from typing import List, Dict, Any, Callable
from itertools import islice

from Leaders import leaders
from constant import EMOJI_UP, EMOJI_DOWN, EMOJI_SPY

class BestCivButton(nextcord.ui.Button):
    def __init__(self, **kwarg):
        super().__init__(**kwarg)

class ArrowUpButton(BestCivButton):
    async def callback(self, interaction: nextcord.Interaction):
        view : BestCivView = self.view
        if interaction.user != view.owner:
            return
        view.page -= 1
        await interaction.response.edit_message(**view.get_embed_and_view())

    def update_disabled_status(self, view):
         self.disabled = view.page == 1

class ArrowDownButton(BestCivButton):
    async def callback(self, interaction: nextcord.Interaction):
        view : BestCivView = self.view
        if interaction.user != view.owner:
            return
        view.page += 1
        await interaction.response.edit_message(**view.get_embed_and_view())

    def update_disabled_status(self, view):
         self.disabled = view.page >= view.max_page

class CloseButton(BestCivButton):
    async def callback(self, interaction: nextcord.Interaction):
        view : BestCivView = self.view
        if interaction.user != view.owner:
            return
        await view.msg.delete()
        interaction.response.is_done()


class BestCivView(nextcord.ui.View):
    def __init__(self, owner : nextcord.Member, target : nextcord.Member, civs : Dict[str, Dict[str, int]],
                 msg : nextcord.Message, client : nextcord.Client):
        super().__init__()
        self.client = client
        self.owner = owner
        self.target = target
        self.civs = civs
        self.msg = msg
        self.page = 1
        self.max_page = (len(civs)-1) // 10 + 1

        self.button_up = ArrowUpButton(emoji=EMOJI_UP, style=ButtonStyle.gray)
        self.button_down = ArrowDownButton(emoji=EMOJI_DOWN, style=ButtonStyle.gray)
        self.button_close = CloseButton(label='X', style=ButtonStyle.red)

        self.add_item(BestCivButton(label='\u200b', style=ButtonStyle.gray, disabled=True))
        self.add_item(self.button_up)
        self.add_item(self.button_down)
        self.add_item(self.button_close)

    def get_embed_and_view(self) -> Dict[str, Any]:
        self.button_down.update_disabled_status(self)
        self.button_up.update_disabled_status(self)
        desc = '\n'.join([self.to_civ_line(k, v, client=self.client)
                          for k, v in islice(self.civs.items(), (self.page - 1) * 10, self.page * 10)])
        embed = nextcord.Embed(
            title=f"{self.target.display_name} - Best civs",
            description=desc if desc else "No Match found",
            color=self.target.color
        ).set_footer(text=f"Page {self.page}/{self.max_page}")
        return dict(embed=embed, view=self)

    @staticmethod
    def to_civ_line(leader_uuname, stats : Dict[str, int], client : nextcord.Client=None) -> str:
        win_percent = stats['win'] / (stats['win']+stats['lose'])
        if client:
            leader = leaders.get_leader(leader_uuname)
            leader_name = leader.civ if leader else "???"
            leader_emoji = client.get_emoji(leader.emoji_id) if leader else EMOJI_SPY
            return f"{leader_emoji} ``{leader_name[:15]:<15}`` ``[{stats['win']:^3}-{stats['lose']:^3}]`` ``{win_percent:.0%}``"
        else:
            return f"``{leader_uuname[:15]:<15}`` [{stats['win']:^3}-{stats['lose']:^3}]`` ``{win_percent:.0%}``"