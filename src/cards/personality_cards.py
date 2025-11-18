"""
Personality card implementations
"""
from src.engine import GameEngine
from ..models import Card, Action, EventListener, EventType, TimingType
from ..json_loader import load_card_fields #type:ignore


class Passionate(Card):
    def __init__(self):
        # Passionate is a Fitness attribute with 1 Connection icon
        super().__init__(**load_card_fields("Passionate", "Personality")) #type:ignore

    def on_committed(self, engine: GameEngine, action: Action) -> str | None:
        """
        Register an ephemeral listener that triggers after test success.
        Effect: After you succeed at a test in which you committed this attribute,
        you may suffer 1 fatigue to add it back into your hand.
        """
        # Create unique ID for this ephemeral listener
        listener_id = f"{self.id}-passionate-recovery"

        def on_test_succeed(eng: GameEngine, effort: int) -> int:
            """Prompt to recover the card by suffering fatigue"""
            # Check if player wants to recover the card
            if eng.response_decider(eng, f"Suffer 1 fatigue to return {self.title} to hand?"):
                # Suffer the fatigue
                eng.state.ranger.fatigue(eng, 1)

                # Move card from discard back to hand
                if self in eng.state.ranger.discard:
                    eng.state.ranger.discard.remove(self)
                    eng.state.ranger.hand.append(self)
                    eng.add_message(f"{self.title} returned to hand.")
                else:
                    eng.add_message(f"Warning: {self.title} not found in discard!")

            return 0  # Don't modify effort

        # Register the ephemeral listener
        listener = EventListener(
            event_type=EventType.TEST_SUCCEED,
            active=lambda eng, _c: True,  # Always active when test succeeds
            effect_fn=on_test_succeed,
            source_card_id=listener_id,
            timing_type=TimingType.AFTER,
            test_type=None  # Triggers for all test types
        )

        engine.register_listeners([listener])

        # Return the ID so it can be cleaned up
        return listener_id
