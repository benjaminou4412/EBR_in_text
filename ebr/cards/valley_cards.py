"""
Valley set card implementations
"""
from typing import Callable

from ebr.models import EventListener


from ..models import *
from ..json_loader import load_card_fields #type:ignore
from ..engine import GameEngine

class CalypsaRangerMentor(Card):
    def __init__(self):
        # Load all common PathCard fields from JSON
        super().__init__(**load_card_fields("Calypsa, Ranger Mentor", "Valley")) #type:ignore
        self.keywords = {Keyword.FRIENDLY}
        self.art_description = "A mature woman with determined eyes, wearing a form-fitting " \
        "suit of what almost looks like padded armor, a hooded cloak, a backpack, and a " \
        "Ranger Badge. The suit is clearly thick enough to offer substantial protection, but her " \
        "body's musclature and strength is apparent beneath its surface, with muscled arms and a " \
        "broad chest. She carries a simple walking stick shaped like a shepherd's crook, " \
        "reinforced by a wrapping around the grip point and what might be bone ornamentation along its hook."


    def get_challenge_handlers(self) -> dict[ChallengeIcon, Callable[[GameEngine], bool]] | None:
        """Returns challenge symbol effects for this card"""
        return {
            ChallengeIcon.MOUNTAIN: self._mountain_effect,
            ChallengeIcon.CREST: self._crest_effect
        }
            

    def _mountain_effect(self, engine: GameEngine) -> bool:
        """Mountain effect: Add 1[progress] to a path card as Calypsa lends you a hand."""
        path_cards: list[Card] = engine.state.path_cards_in_play() #never empty because Calypsa herself is always a valid target
        engine.add_message(f"Challenge (Mountain) on {self.title}: Calypsa lends you a hand. Choose a path card to add 1 progress to:")
        target: Card = engine.card_chooser(engine,path_cards)
        msg = target.add_progress(1)
        engine.add_message(msg)
        return True

    def _crest_effect(self, engine: GameEngine) -> bool:
        """If there is an active predator, exhaust it. »» Add [harm] to this being equal to that predator's presence."""
        return self.harm_from_predator(engine, ChallengeIcon.CREST, self)
    

class QuisiVosRascal(Card):
    def __init__(self):
        # Load all common PathCard fields from JSON
        super().__init__(**load_card_fields("Quisi Vos, Rascal", "Valley")) #type:ignore
        self.keywords = {Keyword.FATIGUING, Keyword.FRIENDLY, Keyword.PERSISTENT}
        self.art_description = "A young girl with a bright smile frolics among several butterfly-like " \
        "beings, her right arm bouncing happily and her left arm outstretched towards one of the beings, " \
        "her wide eyes fixed on it with awe. She wears a simple green cloak with some reinforcement around " \
        "the shoulders, a lightly striped scarf, and a brown shoulder bag. One of the beings is perched on her " \
        "left index finger, which is actually part of an entirely mechanical prosthetic left hand. The palm and " \
        "each finger float detached from the prosthetic wrist, seemingly held in coordination by some kind of magnetic " \
        "force-field technology."
        

    def get_listeners(self) -> list[EventListener] | None:
        listeners = super().get_listeners()
        return listeners
    
    def get_challenge_handlers(self) -> dict[ChallengeIcon, Callable[[GameEngine], bool]] | None:
        """Returns challenge symbol effects for this card"""
        return {
            ChallengeIcon.SUN: self._sun_effect,
            ChallengeIcon.CREST: self._crest_effect
        }
            

    def _sun_effect(self, engine: GameEngine) -> bool:
        """Sun effect: Discard either 1 progress or 1 token from a flora, insect, or gear."""
        # Find valid targets: flora, insect, or gear with at least one token (progress or unique)
        targets: list[Card] = [target for target in engine.state.all_cards_in_play()
                   if (target.has_trait("Flora") or target.has_trait("Insect") or target.has_type(CardType.GEAR))
                   and (target.progress > 0 or target.has_any_unique_tokens())]
        if targets:
            engine.add_message(f"Challenge (Sun) on {self.title}: Quisi discards a token from a flora, insect, or gear. Choose one:")
            target = engine.card_chooser(engine, targets)

            # Build list of token removal options
            options: list[str] = []
            if target.progress > 0:
                options.append("progress")

            # Add each unique token type that has at least 1 token
            for token_type, count in target.unique_tokens.items():
                if count > 0:
                    options.append(token_type)

            # Let player choose which token type to discard
            if len(options) > 1:
                chosen_token = engine.option_chooser(engine, options,
                                                     f"Choose which token type to discard from {target.title}:")
            else:
                chosen_token = options[0]

            # Remove the chosen token type
            if chosen_token == "progress":
                _removed, msg = target.remove_progress(1)
                engine.add_message(msg)
            else:
                _removed = target.remove_unique_tokens(engine, chosen_token, 1)
            return True
        else:
            engine.add_message(f"Challenge (Sun) on {self.title}: (no valid targets)")
            return False

    def _crest_effect(self, engine: GameEngine) -> bool:
        """If there is an active predator, exhaust it. »» Add [harm] to this being equal to that predator's presence."""
        return self.harm_from_predator(engine, ChallengeIcon.CREST, self)
    
class TheFundamentalist(Card):
    def __init__(self):
        # Load all common PathCard fields from JSON
        super().__init__(**load_card_fields("The Fundamentalist", "Valley")) #type:ignore
        self.keywords = {Keyword.FRIENDLY}
        self.art_description = "A tensed-up man turns to look at you, his shoulders slightly hunched and his right arm " \
        "clenched upwards. His face is almost entirely obscured by a heavy-duty set of goggles over his eyes and nose and " \
        "the enormous collar of his coat covering his mouth, cheeks, and chin. He wears a wide-brimmed conical hat in teal, " \
        "the same color as his coat and gloves; you get the sense that barely any of his body is exposed to the elements. His " \
        "backpack is unusual, resembling a tiered miniature garden strapped to his back, rimmed by what could be earthenware " \
        "or stone. All sorts of plants sprout out into the open air; you count at least a dozen varieties, ranging from flowering " \
        "cacti to spindly mushrooms to leafy bushels and ferns."
        

    def get_constant_abilities(self) -> list[ConstantAbility] | None:
        """Reduce the presence of all other beings in the same area as the Fundamentalist by 1."""
        results: list[ConstantAbility] | None = super().get_constant_abilities()
        return [ConstantAbility(ConstantAbilityType.MODIFY_PRESENCE,
                                    source_card_id=self.id,
                                    condition_fn=lambda s, c: (c.has_type(CardType.BEING) 
                                                            and s.get_card_area_by_id(c.id) == s.get_card_area_by_id(self.id)
                                                            and c.id != self.id),
                                    modifier=ValueModifier(target="presence",
                                                        amount = -1,
                                                        source_id=self.id))] + (results if results is not None else [])
    
    def get_challenge_handlers(self) -> dict[ChallengeIcon, Callable[[GameEngine], bool]] | None:
        """Returns challenge symbol effects for this card"""
        return {
            ChallengeIcon.MOUNTAIN: self._mountain_effect,
            ChallengeIcon.CREST: self._crest_effect
        }
            

    def _mountain_effect(self, engine: GameEngine) -> bool:
        """If this being has 1 or more harm >> Remove 1 harm from this being"""
        if self.harm >= 1:
            engine.add_message(f"{self.title} has 1 or more harm, so he chews on an herb harvested from his backpack.")
            self.remove_harm(1)
            return True
        else:
            engine.add_message(f"Challenge (Mountain) on {self.title}: (no harm on The Fundamentalist)")
            return False

    def _crest_effect(self, engine: GameEngine) -> bool:
        """If there is an active predator, exhaust it. »» Add [harm] to this being equal to that predator's presence."""
        return self.harm_from_predator(engine, ChallengeIcon.CREST, self)