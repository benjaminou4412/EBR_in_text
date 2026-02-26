"""
Conciliator card implementations
"""
from ebr.engine import GameEngine
from ebr.models import Area, EventListener
from ..models import GameState, Card, EventType, TimingType
from ..json_loader import load_card_fields #type:ignore


class ADearFriend(Card):
    def __init__(self):
        # Load all common RangerCard fields from JSON
        super().__init__(**load_card_fields("A Dear Friend", "Conciliator")) #type:ignore
        self.art_description = "Two figures stand facing the horizon, with an arm each on each other's backs. " \
        "The figure on the right is fully colored and detailed, with slick black hair tied in a bushy ponytail, goggles, " \
        "a red-orange billowing cloak, and their gloved hand pointing out into the distance. The figure on the left, " \
        "along with the background landscape, are rendered as greyscale sketches. The figure on the left has goggles, a bladed staff, " \
        "and a shoulder bag, each also a greyscale sketch."
    
    def get_play_targets(self, state: GameState) -> list[Card] | None:
        return [card for card in (state.path_deck + state.path_discard) if card.has_trait("human")]

    def enters_play(self, engine: GameEngine, area: Area, action_target: Card | None = None) -> None:
        """Search the path deck and discard for a human and put them into play with this card attached."""
        super().enters_play(engine, area, action_target) #sets up art desc., flavor text, listeners
        if action_target in engine.state.path_deck:
            engine.state.path_deck.remove(action_target)
        elif action_target in engine.state.path_discard:
            engine.state.path_discard.remove(action_target)
        else:
            raise RuntimeError(f"Target for A Dear Friend not found in path deck or discard!")
        engine.draw_path_card(action_target, None)

    def get_listeners(self) -> list[EventListener] | None:
        listener = EventListener(event_type=EventType.CLEAR,
                                 active=lambda _e, cleared: cleared.id == self.attached_to_id if cleared is not None else False,
                                 effect_fn=self._move_attachee_human_progress,
                                 source_card_id=self.id,
                                 timing_type=TimingType.WHEN,
                                 test_type=None)
        return [listener]

    def _move_attachee_human_progress(self, eng: GameEngine, progress: int) -> int:
        """Response: When the attached human is cleared, move the progress that were on it to
        any number of other beings, divided as you choose."""
        #using what's usually the effort parameter to represent the amount of progress that was on the Human
        progress_remaining: int = progress
        while progress_remaining > 0:
            eng.add_message(f"Pick a being to add progress to:")
            target: Card = eng.card_chooser(eng, [card for card in eng.state.beings_in_play() if card.id != self.attached_to_id])
            amount = eng.amount_chooser(eng, 0, progress_remaining, f"You have {progress_remaining} progress remaining. How much of it will you add to {target.title}?")
            eng.add_message(target.add_progress(amount))
            progress_remaining -= amount
        return 0




