import nextcord
from nextcord import ButtonStyle
from typing import List, Dict, Any, Callable
from itertools import islice

from constant import EMOJI_UP, EMOJI_DOWN
from models.ReportParser import Match, GameType

class HistoryButton(nextcord.ui.Button):
    def __init__(self, **kwarg):
        super().__init__(**kwarg)

class ArrowUpButton(HistoryButton):
    async def callback(self, interaction: nextcord.Interaction):
        view : HistoryView = self.view
        if interaction.user != view.owner:
            return
        view.page -= 1
        await interaction.response.edit_message(**view.get_embed_and_view())

    def update_disabled_status(self, view):
         self.disabled = view.page == 1

class ArrowDownButton(HistoryButton):
    async def callback(self, interaction: nextcord.Interaction):
        view : HistoryView = self.view
        if interaction.user != view.owner:
            return
        view.page += 1
        await interaction.response.edit_message(**view.get_embed_and_view())

    def update_disabled_status(self, view):
         self.disabled = view.page >= view.max_page

class CloseButton(HistoryButton):
    async def callback(self, interaction: nextcord.Interaction):
        view : HistoryView = self.view
        if interaction.user != view.owner:
            return
        await view.msg.delete()
        interaction.response.is_done()

class FilterButton(HistoryButton):
    def __init__(self, active=False, **kwarg):
        super().__init__(row=1, **kwarg)
        self.active = active
        self.set_ui()

    async def callback(self, interaction: nextcord.Interaction):
        view: HistoryView = self.view
        for i in (view.button_f_all, view.button_f_ffa, view.button_f_teamer, view.button_f_pbc):
            i.active = i == self
            i.set_ui()
        view.update_filter(self.match_filter)
        await interaction.response.edit_message(**self.view.get_embed_and_view())

    def set_ui(self):
        if self.active:
            self.style = ButtonStyle.green
            self.disabled = True
        else:
            self.style = ButtonStyle.blurple
            self.disabled = False

    @staticmethod
    def match_filter(match : Match) -> bool:
        return True

class FilterFFAButton(FilterButton):
    @staticmethod
    def match_filter(match : Match) -> bool:
        return match.gametype == GameType.FFA

class FilterTeamerButton(FilterButton):
    @staticmethod
    def match_filter(match : Match) -> bool:
        return match.gametype == GameType.TEAMER

class FilterPBCButton(FilterButton):
    @staticmethod
    def match_filter(match : Match) -> bool:
        return match.gametype == GameType.PBC

class HistoryView(nextcord.ui.View):
    def __init__(self, owner : nextcord.Member, target : nextcord.Member, history : List[Match], msg : nextcord.Message, client : nextcord.Client):
        super().__init__()
        self.client = client
        self.owner = owner
        self.target = target
        self.history = history
        self.msg = msg
        self.page = 1
        self.max_page = (len(history)-1) // 10 + 1
        self.filter_func : Callable[[Match], bool] = FilterButton.match_filter

        self.button_up = ArrowUpButton(emoji=EMOJI_UP, style=ButtonStyle.gray)
        self.button_down = ArrowDownButton(emoji=EMOJI_DOWN, style=ButtonStyle.gray)
        self.button_close = CloseButton(label='X', style=ButtonStyle.red)
        self.button_f_all = FilterButton(label='All', active=True)
        self.button_f_ffa = FilterFFAButton(label='FFA')
        self.button_f_teamer = FilterTeamerButton(label='Team')
        self.button_f_pbc = FilterPBCButton(label='PBC')

        self.add_item(HistoryButton(label='\u200b', style=ButtonStyle.gray, disabled=True))
        self.add_item(self.button_up)
        self.add_item(self.button_down)
        self.add_item(self.button_close)
        self.add_item(self.button_f_all)
        self.add_item(self.button_f_ffa)
        self.add_item(self.button_f_teamer)
        self.add_item(self.button_f_pbc)

    def update_filter(self, new_filter):
        self.filter_func = new_filter
        self.page = 1
        self.max_page = (sum(1 for i in filter(self.filter_func, self.history))-1) // 10 + 1

    def get_embed_and_view(self) -> Dict[str, Any]:
        self.button_down.update_disabled_status(self)
        self.button_up.update_disabled_status(self)
        desc = '\n'.join([match.to_history_line_for_player(self.target.id, self.client)
                          for match in islice(filter(self.filter_func, self.history), (self.page - 1) * 10, self.page * 10)])
        embed = nextcord.Embed(
            title=f"{self.target.display_name} - History",
            description=desc if desc else "No Match found",
            color=self.target.color
        ).set_footer(text=f"Page {self.page}/{self.max_page}")
        return dict(embed=embed, view=self)
