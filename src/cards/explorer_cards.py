"""
Explorer card implementations
"""
from ..models import Card, EventListener, EventType, TimingType, Action, GameState, Keyword
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
        presence = target.get_current_presence(engine)
        if presence is not None and presence > 0:
            engine.fatigue_ranger(engine.state.ranger, presence)

class ShareintheValleysSecrets(Card):
    def __init__(self):
        # Load all common RangerCard fields from JSON
        super().__init__(**load_card_fields("Share in the Valley's Secrets", "Explorer")) #type:ignore
        self.art_description = "A mostly-monochrome sketch depicting the silouetted figures of three rangers " \
        "traversing a series of raised pillars in an overgrown landscape. The leftmost figure is mid-leap from " \
        "on pillar to another, the middle figure seems poised to do the same, and the rightmost figure is carefully " \
        "lowering themselves across a drop between two closer pillars."

    def resolve_moment_effect(self, engine: GameEngine, effort: int, target: Card | None) -> None:
        """Exhaust each obstacle. Suffer fatigue equal to the number of obstacles exhausted this way."""
        num_exhausted = 0
        for card in engine.state.all_cards_in_play():
            if card.has_keyword(Keyword.OBSTACLE):
                if not card.is_exhausted():
                    engine.add_message(card.exhaust())
                    num_exhausted = num_exhausted + 1
        if num_exhausted > 0:
            engine.add_message(f"Exhausted {num_exhausted} obstacles. Applying that amount of fatigue...")
        engine.fatigue_ranger(engine.state.ranger, num_exhausted)
        

class BoundarySensor(Card):
    def __init__(self):
        # Load all common RangerCard fields from JSON
        super().__init__(**load_card_fields("Boundary Sensor", "Explorer")) #type:ignore
        self.art_description = "A gloved hand grips the lower half of a roughly cylindrical handheld device, " \
        "about 8 inches in length. The gripped portion is only barely visible through the hand's fingers, and " \
        "appears to be a simple grip point of smooth black material, perhaps rubber. The upper portion extends " \
        "out through the hand's thumb and index finger wrapped around the grip, and consists of intricate metal parts " \
        "and lights, with some exposed circuitry showing through. Topping the device is a transluscent red half-dome " \
        "through which a gathering miniature antennae is darkly visible."

    def get_listeners(self) -> list[EventListener] | None:
        return [EventListener(EventType.PERFORM_TEST,
                              lambda eng: self.exhaust_ability_active("sensor"),
                              self.trigger_exhaust_prompt,
                              self.id, TimingType.WHEN, "Traverse")]

    def trigger_exhaust_prompt(self, eng: GameEngine, effort: int) -> int:
        decision = self.exhaust_prompt(eng, "You may exhaust Boundary Sensor and spend 1 sensor " \
                                            "token off of it to commit 1 effort to this Traverse.")
        if decision:
            _amount, msg = self.remove_unique_tokens("sensor", 1)
            eng.add_message(msg)
            self.exhaust()
            return 1
        else:
            return 0
    


class WalkWithMe(Card):
    def __init__(self):
        # Load all common RangerCard fields from JSON
        super().__init__(**load_card_fields("Walk With Me", "Explorer")) #type:ignore
        self.art_description = "A detailed sketch of a canine in a snowy, hilly clearing. The canine looks " \
        "back, and in the distance you see the small figures of the rest of its pack just exiting a copse " \
        "of snow-topped firs."

    def enters_hand(self, engine: GameEngine) -> list[EventListener]:
        """Override to add listener. Call super() to show art description."""
        super().enters_hand(engine)
        listeners = self.get_listeners()
        if listeners is None:
            raise RuntimeError(f"Walk With Me should have a listener!")
        else:
            return listeners
    
    def get_listeners(self) -> list[EventListener] | None:
        def trigger_play_prompt(eng: GameEngine, effort: int) -> int:
            self.play_prompt(eng, effort, "You succeeded at a Traverse test.")
            return 0
        return [EventListener(EventType.TEST_SUCCEED,
                              lambda eng: self.can_be_played(eng),  # Check energy + targets
                              trigger_play_prompt,
                              self.id, TimingType.AFTER, "Traverse")]

    def get_play_targets(self, state: GameState) -> list[Card]:
        """Returns valid beings to add progress to"""
        return state.beings_in_play()
        
        
    def resolve_moment_effect(self, engine: GameEngine, effort: int, target: Card | None) -> None:
        """Response: After you succeed at a Traverse test, add progress to a being equal to your effort. 
        This is in addition to the test's standard effect."""
        if target:
            engine.add_message(target.add_progress(effort))
        else:
            raise RuntimeError(f"Targets should exist past play_prompt!")
        
    
