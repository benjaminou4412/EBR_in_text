"""
Woods terrain set card implementations
"""
from typing import Optional, Callable
from ..models import *
from ..json_loader import load_card_fields #type:ignore
from ..utils import get_display_id
from ..engine import GameEngine

class ProwlingWolhund(Card):
    def __init__(self):
        super().__init__(**load_card_fields("Prowling Wolhund", "woods")) #type:ignore
        self.art_description = "A tense canine being with a distinct mane running from its " \
        "forehead all the way down to join its tail. It steps lightly on the balls of its " \
        "paws, oriented slightly away from you but with its head turned to give you a glare."

class SitkaBuck(Card):
    def __init__(self):
        # Load all common PathCard fields from JSON
        super().__init__(**load_card_fields("Sitka Buck", "woods")) #type:ignore
        self.art_description = "A deer-like being stands tall and alert in the woods. Its " \
        "neck is nearly as long as the rest of its body, and coated in an extra-thick layer of " \
        "bushy fur. Its snout resembles a cow's. Its antlers are multi-pronged and symmetrical, " \
        "with both branching in many directions in both smooth curves and sharp angles. If it " \
        "charged antlers-forward, those sharp points would hurt."

class SitkaDoe(Card):
    def __init__(self):
        # Load all common PathCard fields from JSON
        super().__init__(**load_card_fields("Sitka Doe", "woods")) #type:ignore
        self.art_description = "A deer-like being looking closely at a low bush. Its neck is " \
        "nearly as long as the rest of its body, and coated in an extra-thick layer of bushy fur. " \
        "Its snout resembles a cow's. It lacks antlers, and it's not clear whether it's noticed you."

    def get_tests(self) -> list[Action]:
        """Returns all tests this card provides"""
        return [
            Action(
                id=f"test-{self.id}",
                name=f"{self.title} (SPI + Conflict) [X=presence]",
                aspect=Aspect.SPI,
                approach=Approach.CONFLICT,
                verb="Spook",
                target_provider=lambda _s: [self],
                difficulty_fn=lambda _s, _t: 1,
                on_success=self._on_spook_success,
                source_id=self.id,
                source_title=self.title,
            )
        ]

    def _on_spook_success(self, engine: GameEngine, effort: int, target_id: Optional[str]) -> None:
        """Spook test success: move to Along the Way"""
        engine.move_card(self.id, Zone.ALONG_THE_WAY)

    def get_symbol_handlers(self) -> dict[ChallengeIcon, Callable[[GameEngine], None]] | None:
        """Returns challenge symbol effects for this card"""
        return {
            ChallengeIcon.SUN: self._sun_effect,
            ChallengeIcon.MOUNTAIN: self._mountain_effect
        }

    def _sun_effect(self, engine: GameEngine) -> None:
        """Sun effect: If there are 1 or more Sitka Bucks in play >> Move each Sitka Buck within reach"""
        bucks = engine.state.get_cards_by_title("Sitka Buck")
        if bucks is None:
            engine.add_message(f"Challenge (Sun) on {get_display_id(engine.state.all_cards_in_play(), self)}: (no Sitka Buck in play)")
        else:
            engine.add_message(f"Challenge (Sun) on {get_display_id(engine.state.all_cards_in_play(), self)}: The Sitka Buck are drawn to the doe. They move within reach.")
            for buck in bucks:
                engine.move_card(buck.id, Zone.WITHIN_REACH)
            

    def _mountain_effect(self, engine: GameEngine) -> None:
        """Mountain effect: If there is an active predator, exhaust it >> Add harm to this being equal to that predator's presence"""
        self.harm_from_predator(engine, ChallengeIcon.MOUNTAIN)

class CausticMulcher(Card):
    def __init__(self):
        # Load all common PathCard fields from JSON
        super().__init__(**load_card_fields("Caustic Mulcher", "woods")) #type:ignore
        self.art_description = "A large, many-limbed being that stands at least 10 feet tall, nearly " \
        "brushing up against the boughs of the wood's trees. Its main body resembles a bulb or a pod " \
        "with a rocky texture along its surface, topped with a circular maw ringed with sharp talon-like " \
        "teeth. Extending from the center of its maw is a prehensile tentacle-tube, with a ring of " \
        "grabber-claws at the end of it. You count at least 8 legs extending haphazardly from just below " \
        "the maw, each with two joints along its length. They're coated in exoskeleton, like a spider's."


class SunberryBramble(Card):
    def __init__(self):
        # Load all common PathCard fields from JSON
        super().__init__(**load_card_fields("Sunberry Bramble", "woods")) #type:ignore
        self.art_description = "A clearing full of bulging, juicy-looking, bright-yellow fruit. " \
        "Each of the fruit has a vertical ring of thorns around its circumference, and a bundle " \
        "of stamen extending up from the top of the fruit shrouded by 5 dropping leaves. Extending " \
        "down from the fruits is a thick stem with even thicker horn-like thorns. Woody vines climb up " \
        "from the earth, wrapping around the stems."

    def get_tests(self) -> list[Action]:
        """Returns all tests this card provides"""
        return [
            Action(
                id=f"test-{self.id}",
                name=f"{self.title} (AWA + Reason) [2]",
                aspect=Aspect.AWA,
                approach=Approach.REASON,
                verb="Pluck",
                target_provider=lambda _s: [self],
                difficulty_fn=lambda _s, _t: 2,
                on_success=self._on_pluck_success,
                on_fail=self._fail_effect,
                source_id=self.id,
                source_title=self.title,
            )
        ]

    def _on_pluck_success(self, engine: GameEngine, effort: int, target_id: Optional[str]) -> None:
        """Pluck test success: add 1 harm"""
        engine.add_message(f"Target {self.title} takes 1 harm")
        self.add_harm(1)
        engine.soothe_ranger(engine.state.ranger, 2)

    def _fail_effect(self, engine: GameEngine, message: str | None) -> None:
        engine.add_message(f"Target {self.title} fatigues you.")
        curr_presence = self.get_current_presence()
        if curr_presence is not None:
            engine.fatigue_ranger(engine.state.ranger, curr_presence)



            


class OvergrownThicket(Card):
    def __init__(self):
        # Load all common PathCard fields from JSON
        super().__init__(**load_card_fields("Overgrown Thicket", "woods")) #type:ignore
        self.keywords = {Keyword.OBSTACLE}
        self.art_description = "The trees before you have grown thick and tangled, forming " \
        "a nearly impenetrable barrier in your path."

    def get_tests(self) -> list[Action] | None:
        """Returns all tests this card provides"""
        return [
            Action(
                id=f"test-{self.id}",
                name=f"{self.title} (AWA + Exploration)",
                aspect=Aspect.AWA,
                approach=Approach.EXPLORATION,
                verb="Hunt",
                target_provider=lambda _s: [self],
                difficulty_fn=lambda _s, _t: 1,
                on_success=self._on_hunt_success,
                source_id=self.id,
                source_title=self.title,
            )
        ]

    def _on_hunt_success(self, engine: GameEngine, effort: int, target_id: Optional[str]) -> None:
        """Hunt test success: add progress equal to effort"""
        self.add_progress(effort)

    def get_symbol_handlers(self) -> dict[ChallengeIcon, Callable[[GameEngine], None]] | None:
        """Returns challenge symbol effects for this card"""
        return {
            ChallengeIcon.MOUNTAIN: self._mountain_effect
        }

    def _mountain_effect(self, engine: GameEngine) -> None:
        """Mountain effect: discard 1 progress"""
        if self.progress > 0:
            self.progress -= 1
            engine.add_message(f"Challenge (Mountain) on {get_display_id(engine.state.all_cards_in_play(), self)}: discards 1 progress (now {self.progress}).")
            curr_presence = self.get_current_presence()
            if curr_presence is not None:
                engine.fatigue_ranger(engine.state.ranger, curr_presence)
        else:
            engine.add_message(f"Challenge: (Mountain) on {get_display_id(engine.state.all_cards_in_play(), self)}: (no progress to discard).")
