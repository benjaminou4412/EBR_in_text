"""
Woods terrain set card implementations
"""
from typing import Callable

from src.models import Area
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
    
    def enters_play(self, engine: GameEngine, area: Area) -> None:
        """If there is another predator in play, this predator comes into play exhausted"""
        super().enters_play(engine, area)
        predators = engine.state.get_cards_by_trait("Predator")
        # Check if there's another predator besides this one
        if predators and any(p.id != self.id for p in predators):
            self.exhaust()
            engine.add_message("   Another predator is present - Prowling Wolhund enters play exhausted.")
        

    def get_challenge_handlers(self) -> dict[ChallengeIcon, Callable[[GameEngine], bool]] | None:
        """Returns challenge symbol effects for this card"""
        return {
            ChallengeIcon.SUN: self._sun_effect,
            ChallengeIcon.CREST: self._crest_effect
        }
        
    def _sun_effect(self, engine: GameEngine) -> bool:
        """Sun effect: Ready another Prowling Wolhund"""
        self_display_id = get_display_id(engine.state.all_cards_in_play(), self)
        wolhunds = engine.state.get_cards_by_title("Prowling Wolhund")
        if wolhunds is None:
            engine.add_message(f"Challenge (Sun) on {self_display_id}: (no other Wolhunds in play)")
            return False
        else:
            wolhunds_excluding_self = [wol for wol in wolhunds if wol.id != self.id]
            exhausted_wolhunds = [wol for wol in wolhunds_excluding_self if wol.is_exhausted()]
            if exhausted_wolhunds:
                #prompt player to pick one to ready
                engine.add_message(f"Challenge (Sun) on {self_display_id}: Choose another Prowling Wolhund to ready:")
                target: Card = engine.card_chooser(engine, exhausted_wolhunds)
                engine.add_message(target.ready())
                return True
            else:
                engine.add_message(f"Challenge (Sun) on {self_display_id}: (all other Wolhunds already ready)")
                return False
            

    def _crest_effect(self, engine: GameEngine) -> bool:
        """Crest effect: If you have 3 or more fatigue, exhaust this being >> Suffer 1 injury"""
        self_display_id = get_display_id(engine.state.all_cards_in_play(), self)
        enough_fatigue = len(engine.state.ranger.fatigue_pile) >= 3
        if enough_fatigue:
            engine.add_message(f"Challenge (Crest) on {self_display_id}: You have {len(engine.state.ranger.fatigue_pile)} fatigue - Prowling Wolhund exhausts itself and you suffer 1 injury!")
            self.exhaust()
            engine.injure_ranger(engine.state.ranger)
            return True
        else:
            engine.add_message(f"Challenge (Crest) on {self_display_id}: (low enough fatigue to avoid injury)")
            return False

class SitkaBuck(Card):

    def __init__(self):
        # Load all common PathCard fields from JSON
        super().__init__(**load_card_fields("Sitka Buck", "woods")) #type:ignore
        self.art_description = "A deer-like being stands tall and alert in the woods. Its " \
        "neck is nearly as long as the rest of its body, and coated in an extra-thick layer of " \
        "bushy fur. Its snout resembles a cow's. Its antlers are multi-pronged and symmetrical, " \
        "with both branching in many directions in both smooth curves and sharp angles. If it " \
        "charged antlers-forward, those sharp points would hurt."

    def get_challenge_handlers(self) -> dict[ChallengeIcon, Callable[[GameEngine], bool]] | None:
        """Returns challenge symbol effects for this card"""
        return {
            ChallengeIcon.SUN: self._sun_effect,
            ChallengeIcon.MOUNTAIN: self._mountain_effect,
            ChallengeIcon.CREST: self._crest_effect
        }
    
    def _sun_effect(self, engine: GameEngine) -> bool:
        """If there is another active Sitka Buck, exhaust this being >> Add 2[harm] to both this
        and the other Sitka Buck."""
        self_display_id = get_display_id(engine.state.all_cards_in_play(), self)
        bucks = engine.state.get_cards_by_title("Sitka Buck")
        if not bucks:
            raise RuntimeError("This card should count itself as a buck, so we can't get no-bucks-found here.")
        else:
            other_active_bucks = [buck for buck in bucks if buck.id != self.id and buck.is_ready()]
            if other_active_bucks:
                if len(other_active_bucks)==1:
                    engine.add_message(f"Challenge (Sun) on {self_display_id}: Only one other active buck; automatically chosen for harm:")
                else:
                    engine.add_message(f"Challenge (Sun) on {self_display_id}: Choose another buck to harm:")
                target_buck = engine.card_chooser(engine, other_active_bucks)
                engine.add_message(self.exhaust())
                engine.add_message(self.add_harm(2))
                engine.add_message(target_buck.add_harm(2))
                return True
            else:
                engine.add_message(f"Challenge (Sun) on {self_display_id}: (no other active Sitka Bucks)")
                return False
    
    def _mountain_effect(self, engine: GameEngine) -> bool:
        """If there is an active predator, exhaust it >> Add 2 harm to it, then add harm to this
        being equal to that predator's presence."""
        self_display_id = get_display_id(engine.state.all_cards_in_play(), self)
        predators = engine.state.get_cards_by_trait("Predator")
        if not predators:
            engine.add_message(f"Challenge (Mountain) on {self_display_id}: (no predators in play)")
            return False
        else:
            active_predators = [predator for predator in predators if predator.is_ready()]
            if not active_predators:
                engine.add_message(f"Challenge (Mountain) on {self_display_id}: (no active predators in play)")
                return False
            elif len(active_predators) == 1:
                engine.add_message(f"Challenge (Mountain) on {self_display_id}: Only one active predator; automatically chosen for harm:")
            else:
                engine.add_message(f"Challenge (Mountain) on {self_display_id}: Choose an active predator to harm:")
            target_predator = engine.card_chooser(engine, active_predators)
            engine.add_message(target_predator.exhaust())
            engine.add_message(target_predator.add_harm(2))
            curr_presence = target_predator.get_current_presence()
            if curr_presence is not None:
                engine.add_message(self.add_harm(curr_presence))
                return True
            else:
                raise RuntimeError("A predator should always have a presence value!")
    
    def _crest_effect(self, engine: GameEngine) -> bool:
        """If there is an active Sitka Doe, the buck charges >> Suffer 1 injury."""
        self_display_id = get_display_id(engine.state.all_cards_in_play(), self)
        does = engine.state.get_cards_by_title("Sitka Doe")
        if does and any(doe.is_ready() for doe in does):
            engine.add_message(f"Challenge (Crest) on {self_display_id}: There is an active Sitka Doe, so the buck charges.")
            engine.injure_ranger(engine.state.ranger)
            return True
        else:
            engine.add_message(f"Challenge (Crest) on {self_display_id}: (no active Sitka Doe)")
            return False

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

    def _on_spook_success(self, engine: GameEngine, effort: int, card: Card | None) -> None:
        """Spook test success: move to Along the Way"""
        engine.move_card(self.id, Area.ALONG_THE_WAY)

    def get_challenge_handlers(self) -> dict[ChallengeIcon, Callable[[GameEngine], bool]] | None:
        """Returns challenge symbol effects for this card"""
        return {
            ChallengeIcon.SUN: self._sun_effect,
            ChallengeIcon.MOUNTAIN: self._mountain_effect
        }

    def _sun_effect(self, engine: GameEngine) -> bool:
        """Sun effect: If there are 1 or more Sitka Bucks in play >> Move each Sitka Buck within reach"""
        bucks = engine.state.get_cards_by_title("Sitka Buck")
        self_display_id = get_display_id(engine.state.all_cards_in_play(), self)
        if bucks is None:
            engine.add_message(f"Challenge (Sun) on {self_display_id}: (no Sitka Buck in play)")
            return False
        else:
            engine.add_message(f"Challenge (Sun) on {self_display_id}: The Sitka Buck are drawn to the doe. They move within reach.")
            any_moved = False
            for buck in bucks:
                if engine.move_card(buck.id, Area.WITHIN_REACH):
                    any_moved = True
            return any_moved
            

    def _mountain_effect(self, engine: GameEngine) -> bool:
        """Mountain effect: If there is an active predator, exhaust it >> Add harm to this being equal to that predator's presence"""
        return self.harm_from_predator(engine, ChallengeIcon.MOUNTAIN, self)

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

    def _on_pluck_success(self, engine: GameEngine, effort: int, card: Card | None) -> None:
        """Pluck test success: add 1 harm"""
        msg = self.add_harm(1)
        engine.add_message(msg)
        engine.soothe_ranger(engine.state.ranger, 2)

    def _fail_effect(self, engine: GameEngine, effort: int, card: Card | None) -> None:
        engine.add_message(f"Target {self.title} fatigues you.")
        curr_presence = self.get_current_presence()
        if curr_presence is not None:
            engine.fatigue_ranger(engine.state.ranger, curr_presence)


    def get_challenge_handlers(self) -> dict[ChallengeIcon, Callable[[GameEngine], bool]] | None:
        """Returns challenge symbol effects for this card"""
        return {
            ChallengeIcon.MOUNTAIN: self._mountain_effect
        }

    def _mountain_effect(self, engine: GameEngine) -> bool:
        """Mountain effect: If there is an active prey, exhaust it >>
        Add [progress] to it and [harm] to this feature, both equal to 
        that prey's presence."""
        return self.harm_from_prey(engine, ChallengeIcon.MOUNTAIN, self)
            


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

    def _on_hunt_success(self, engine: GameEngine, effort: int, card: Card | None) -> None:
        """Hunt test success: add progress equal to effort"""
        msg = self.add_progress(effort)
        engine.add_message(msg)

    def get_challenge_handlers(self) -> dict[ChallengeIcon, Callable[[GameEngine], bool]] | None:
        """Returns challenge symbol effects for this card"""
        return {
            ChallengeIcon.MOUNTAIN: self._mountain_effect
        }

    def _mountain_effect(self, engine: GameEngine) -> bool:
        """Mountain effect: discard 1 progress"""
        self_display_id = get_display_id(engine.state.all_cards_in_play(), self)
        if self.progress > 0:
            engine.add_message(f"Challenge (Mountain) on {self_display_id}: discards 1 progress to fatigue you.")
            engine.add_message(self.remove_progress(1)[1])
            curr_presence = self.get_current_presence()
            if curr_presence is not None:
                engine.fatigue_ranger(engine.state.ranger, curr_presence)
            return True
        else:
            engine.add_message(f"Challenge: (Mountain) on {self_display_id}: (no progress to discard; no fatigue).")
            return False
