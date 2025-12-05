from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .engine import GameEngine

class CampaignGuide:
    def __init__(self):
        self.entries : dict[str, Callable[['CampaignGuide', 'GameEngine', str | None], None]] = {"80": self.resolve_entry_80}

    def resolve_entry_80(self, engine: 'GameEngine', clear_type: str | None): #clear_type of None indicates non-clear resolution
        engine.add_message("=== Campaign Log Entry 80: Quisi Vos, Rascal ===")
        if clear_type is None:
            engine.add_message("Quisi enters play:")
            engine.add_message("> If a Ranger has Biscuit Basket Equipped, go to 80.1.")
            if engine.state.get_cards_by_title("Biscuit Basket") is not None:
                engine.add_message("Biscuit Basket found. Resolving Entry 80.1...")
                self.entries["80.1"](engine, clear_type)
                return
            engine.add_message("Biscuit Basket not found. Proceeding...")
            engine.add_message("> If Oura Vos is in play, go to 80.2.")
            if engine.state.get_cards_by_title("Oura Vos, Traveler") is not None:
                engine.add_message("Oura Vos found. Resolving Entry 80.2...")
                self.entries["80.2"](engine, clear_type)
                return
            engine.add_message("Oura Vos not found. Proceeding...")
            engine.add_message("> Otherwise, go to 80.3.")
            self.entries["80.3"](engine, clear_type)
        elif clear_type.casefold() == "progress".casefold():
            engine.add_message("Quisi was cleared by Progress:")
            engine.add_message("> Go to 80.5")
            self.entries["80.5"](engine, clear_type)
            return
        elif clear_type.casefold() == "harm".casefold():
            engine.add_message("Quisi was cleared by Harm:")
            engine.add_message("> Go to 80.6")
            self.entries["80.6"](engine, clear_type)
            return
        else:
            raise RuntimeError("Campaign guide entry resolving with invalid clear type!")

        