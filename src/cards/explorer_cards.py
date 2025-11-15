"""
Explorer card implementations
"""
from ..models import Card, EventListener, EventType, TimingType, Action, GameState
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

class BoundarySensor(Card):
    def __init__(self):
        # Load all common RangerCard fields from JSON
        super().__init__(**load_card_fields("Boundary Sensor", "Explorer")) #type:ignore
        self.art_description = "A gloved hand grips the lower half of a roughly cylindrical handheld device, " \
        "about 8 inches in length. The gripped portion is only barely visible through the hand's fingers, and " \
        "appears to be a simple grip point of smooth black material, perhaps rubber. The upper portion extends " \
        "up through the hand's thumb and index finger wrapped around it, and consists of intricate metal parts " \
        "and lights, with some exposed circuitry showing through. Topping the device is a transluscent red half-dome " \
        "through which a gathering of what may be miniature antennae is darkly visible."

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
        def trigger_play_prompt(eng: GameEngine, effort: int) -> None:
            self.play_prompt(eng, effort, "You succeeded at a Traverse test.")
        return [EventListener(EventType.TEST_SUCCEED,
                            trigger_play_prompt,
                            self.id, TimingType.AFTER, "Traverse")]

    def get_play_targets(self, state: GameState) -> list[Card]:
        """Returns valid beings to add progress to"""
        return state.beings_in_play()

    def get_play_action(self) -> Action | None:
        """
        Effect: Add progress to a Being equal to the resulting effort of the Traverse test.
        Called by play_prompt() after user confirms and energy is paid.
        Targets are guaranteed to exist by play_prompt().
        """
        return Action(id=f"{self.id}_play_action",
                      name=f"Play {self.title}",
                      aspect="",
                      approach="",
                      is_test=False,
                      target_provider=self.get_play_targets,
                      on_success=self._play_action_effect,
                      source_id=self.id,
                      source_title=self.title
                      )
        
        
    def _play_action_effect(self, engine: GameEngine, effort: int, target: Card | None) -> None:
        targets_list = self.get_play_targets(engine.state)
        engine.add_message(f"Please choose a Being to add {effort} [Progress] to.")
        if targets_list:
            target = engine.card_chooser(engine, targets_list)
            engine.add_message(target.add_progress(effort))
        else:
            raise RuntimeError(f"Targets should exist past play_prompt!")
        
    
