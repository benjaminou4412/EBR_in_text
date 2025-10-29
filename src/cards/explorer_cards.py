"""
Explorer card implementations
"""
from ..models import Card, EventListener, EventType, TimingType, Aspect, Action
from ..engine import GameEngine
from ..json_loader import load_card_fields #type:ignore

class PeerlessPathfinder(Card):
    def __init__(self):
        super().__init__(**load_card_fields("Peerless Pathfinder", "Explorer")) #type:ignore
        self.art_description = "A dark-skinned ranger squints off into the distance, shielding his eyes " \
        "from a late afternoon sun with his left arm. He carries a walking stick carved from a gnarled branch " \
        "with his other arm, and three sharp throwing spears jut out of his backpack, atop which a device " \
        "which may be a collapsed Orlin Hiking Stave is strapped. He wears a thick cap with earmuffs that " \
        "hides all his hair, and heavy-duty goggles are strapped above the cap's brim. His cloak is reinforced " \
        "with metal around his shoulders."
    
    def get_exhaust_abilities(self) -> list[Action] | None:
        """Exhaust: Move ranger token to feature, that feature fatigues you"""
        return [
            Action(
                id=f"exhaust-{self.id}",
                name="Peerless Pathfinder",
                verb="",
                aspect="",
                approach="",
                is_test=False,
                is_exhaust=True,
                target_provider=lambda state: state.features_in_play(),
                on_success=self._move_token_to_feature,
                source_id=self.id,
                source_title=self.title,
            )
        ]
    
    def _move_token_to_feature(self, engine: GameEngine, effort: int, target: Card | None) -> None:
        """Handler for the exhaust ability"""
        if target is None:
            engine.add_message("No target selected for ranger token movement.")
            return

        # Exhaust this role card as the cost
        engine.add_message(self.exhaust())

        # Move ranger token to the target feature
        engine.move_ranger_token_to_card(target)

        # Target feature fatigues you
        presence = target.get_current_presence()
        if presence is not None and presence > 0:
            engine.fatigue_ranger(engine.state.ranger, presence)

class WalkWithMe(Card):
    def __init__(self):
        # Load all common RangerCard fields from JSON
        super().__init__(**load_card_fields("Walk With Me", "Explorer")) #type:ignore
        self.art_description = "A detailed sketch of a canine in a snowy, hilly clearing. The canine looks " \
        "back, and in the distance you see the small figures of the rest of its pack just exiting a copse " \
        "of snow-topped firs."

    def enters_hand(self, engine: GameEngine) -> EventListener | None:
        """Override to add listener. Call super() to show art description."""
        super().enters_hand(engine)
        return EventListener(EventType.TEST_SUCCEED, self.play, self.id, TimingType.AFTER, "Traverse")

    def play(self, engine: GameEngine, effort: int) -> None:
        """
        Effect: Add progress to a Being equal to the resulting effort of the Traverse test
        """
        targets_list = engine.state.beings_in_play()
        if not targets_list:
            engine.add_message("No Beings in play; Walk With Me cannot be played.")
            return
        decision = engine.response_decider(engine, "You succeeded at a Traverse test. Will you play Walk With Me for 1 SPI?")
        if decision:
            success, error = engine.state.ranger.spend_energy(1, Aspect.SPI)
            if success:
                engine.add_message(f"Please choose a Being to add {effort} [Progress] to.")
                target = engine.card_chooser(engine, targets_list)
                # Move Walk With Me to discard and clean up listener
                engine.discard_from_hand(self)
                msg = target.add_progress(effort)
                engine.add_message(f"Played Walk With Me: {msg}")
            elif error:
                engine.add_message(error)
