"""
Location set card implementations
"""
from typing import Callable

from src.models import ConstantAbility


from ..models import *
from ..json_loader import load_card_fields #type:ignore
from ..engine import GameEngine

class LoneTreeStation(Card):
    def __init__(self):
        # Load all common PathCard fields from JSON
        super().__init__(**load_card_fields("Lone Tree Station", "Locations")) #type:ignore
        self.art_description = "A towering tree straddles much of a grassy plateau, standing " \
        "as tall as a skyscraper and several times as wide. A few buildings dot its surroundings, " \
        "some a small distance away and others ensconsced by its enormous roots. Some structures " \
        "are visible in its branches, including large hanging planters the size of rooms and balconies " \
        "carved out from the trunk."

    def do_arrival_setup(self, engine: GameEngine) -> None:
        engine.add_message(f"Search the path deck for the next predator and discard it.")
        target = None
        engine.add_message(f"Searching...")
        for card in engine.state.path_deck:
            if card.has_trait("Predator"):
                target = card
                break
        if target is not None:
            engine.add_message(f"Found Predator {target.title}. Discarding...")
            engine.state.path_deck.remove(target)
            engine.state.path_discard.append(target)
        else:
            engine.add_message(f"No predator found in path deck.")
        
        engine.add_message(f"Lead Ranger: Draw 1 path card.")
        engine.draw_path_card(None, None)

    def get_tests(self) -> list[Action]:
        from ..registry import get_search_test
        return [get_search_test(self, "Search")]


class AncestorsGrove(Card):
    def __init__(self):
        # Load all common PathCard fields from JSON
        super().__init__(**load_card_fields("Ancestor's Grove", "Locations")) #type:ignore
        self.art_description = "A small clearing within the dense wood, showered by sunbeams " \
        "that pour in through the thick canopy above. Several structures dot the clearing, " \
        "each consisting of two parts: the lower part a dome the size and shape of an igloo, " \
        "but built with stone, earth, and wood; and the upper part a copse of trees growing " \
        "atop the dome, their roots snaking down over the grassy roof of the dome. Several people " \
        "gather around the entrance to the closest dome, each wearing hooded robes of a different color."

    def do_arrival_setup(self, engine: GameEngine) -> None:
        engine.add_message(f"Search the path deck for the next card with a presence of 3 and discard it.")
        target = None
        engine.add_message(f"Searching...")
        for card in engine.state.path_deck:
            if card.get_current_presence(engine) == 3:
                target = card
                break
        if target is not None:
            engine.add_message(f"Found {target.title} with presence of 3. Discarding...")
            engine.state.path_deck.remove(target)
            engine.state.path_discard.append(target)
        else:
            engine.add_message(f"No card with presence of 3 found in path deck.")
        
        engine.add_message(f"Lead Ranger: Search the path deck for the next prey and put it into play.")
        target = None
        for card in engine.state.path_deck:
            if card.has_trait("Prey"):
                target = card
                break
        if target is not None:
            engine.add_message(f"Found prey {target.title}. Putting into play...")
            engine.state.path_deck.remove(target)
            engine.draw_path_card(target, None)
        else:
            engine.add_message(f"No prey found in path deck.")

        engine.add_message(f"Next Ranger: Search the path deck for the next prey and put it into play. (Skipped)")


    def get_challenge_handlers(self) -> dict[ChallengeIcon, Callable[[GameEngine], bool]] | None:
        """Returns challenge symbol effects for this card"""
        return {
            ChallengeIcon.SUN: self._sun_effect
        }

    def _sun_effect(self, engine: GameEngine) -> bool:
        """Sun effect: Choose a card from your ranger discard. Place it on top of your fatigue stack."""
        if engine.state.ranger.discard:
            engine.add_message(f"Challenge (Sun) on {self.title}: Choose a card from your discard pile to move to your fatigue stack.")
            target = engine.card_chooser(engine, engine.state.ranger.discard)
            engine.state.ranger.fatigue_stack.insert(0, target)
            engine.state.ranger.discard.remove(target)
            return True
        else:
            engine.add_message(f"Challenge (Sun) on {self.title}: (ranger discard is empty)")
            return False
    
class BoulderField(Card):
    def __init__(self):
        # Load all common PathCard fields from JSON
        super().__init__(**load_card_fields("Boulder Field", "Locations")) #type:ignore
        self.art_description = "A wide-open field filled with boulders of all shapes and sizes. " \
        "The skull of a horned being - perhaps a Sitka Buck? - lies in the center of the scene."


    def do_arrival_setup(self, engine: GameEngine) -> None:
        engine.add_message(f"Lead Ranger: Draw 1 challenge card and do the following based on the challenge icon on that card:")
        engine.add_message(f"Sun: Scout 2 path cards, then draw 1 path card.")
        engine.add_message(f"Mountain: Draw 1 path card.")
        engine.add_message(f"Crest: Scout 3 path cards, then draw 2 path cards.")
        drawn = engine.state.challenge_deck.draw_challenge_card(engine)
        icon = drawn.icon
        if icon == ChallengeIcon.SUN:
            engine.scout_cards(engine.state.path_deck, 2)
            engine.draw_path_card(None, None)
        elif icon == ChallengeIcon.MOUNTAIN:
            engine.draw_path_card(None, None)
        elif icon == ChallengeIcon.CREST:
            engine.scout_cards(engine.state.path_deck, 3)
            engine.draw_path_card(None, None)
            engine.draw_path_card(None, None)
        else:
            raise RuntimeError(f"Challenge card drawn due to Boulder Field has no icon!")

    
    def get_constant_abilities(self) -> list[ConstantAbility] | None:
        """Reduce the presence of all beings in play by 1."""
        return [ConstantAbility(ConstantAbilityType.MODIFY_PRESENCE,
                                source_card_id=self.id,
                                condition_fn=lambda _s, c: c.has_type(CardType.BEING),
                                modifier=ValueModifier(target="presence",
                                                       amount = -1,
                                                       source_id=self.id))]