from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Optional
from .models import GameState, Action, CommitDecision, RangerState, Card, Symbol, Aspect, Approach, Zone, CardType, EventType, TimingType
from .challenge import draw_challenge


@dataclass
class ChallengeOutcome:
    base_effort: int
    modifier: int
    difficulty: int
    symbol: Symbol
    resulting_effort: int
    success: bool




class GameEngine:
    def __init__(self,
                  state: GameState,
                  challenge_drawer: Callable[[], tuple[int, Symbol]] = draw_challenge,
                  card_chooser: Callable[[GameState, list[Card]], Card] | None = None):
        self.state = state
        self.draw_challenge = challenge_drawer
        # challenge symbol effects dispatch (entity-id + symbol -> callable)
        self.symbol_handlers: dict[tuple[str, Symbol], Callable[[GameEngine], None]] = {}
        self.card_chooser = card_chooser if card_chooser is not None else self._default_chooser

    def _default_chooser(self, _state: GameState, choices: list[Card]) -> Card:  # noqa: ARG002
        """Placeholder default; tests should pass in more sophisticated choosers, runtime should prompt player"""
        return choices[0]


    def register_symbol_handler(self, key: tuple[str, Symbol], fn: Callable[[GameEngine], None]):
        self.symbol_handlers[key] = fn

    def refresh_symbol_handlers(self) -> None:
        """Refresh symbol handlers to match currently active cards"""
        self.symbol_handlers.clear()
        for card in self.state.all_cards_in_play():
            handlers = card.get_symbol_handlers()
            if handlers:
                for symbol, handler in handlers.items():
                    self.register_symbol_handler((card.id, symbol), handler)

    def commit_icons(self, ranger: RangerState, approach: Approach, decision: CommitDecision) -> tuple[int, list[int]]:
        total = decision.energy
        valid_indices : list[int] = []
        for idx in decision.hand_indices:
            if not (0 <= idx < len(ranger.hand)):
                continue
            c: Card = ranger.hand[idx]
            num_icons = c.approach_icons.get(approach, 0)
            if num_icons:
                total += num_icons
                valid_indices.append(idx)
        return total, valid_indices

    def discard_committed(self, ranger: RangerState, committed_indices: list[int]) -> None:
        for i in sorted(committed_indices, reverse=True):
            del ranger.hand[i]

    def perform_action(self, action: Action, decision: CommitDecision, target_id: Optional[str]) -> ChallengeOutcome:
        # Non-test actions (e.g., Rest) skip challenge + energy
        if not action.is_test:
            action.on_success(self.state, 0, target_id)
            return ChallengeOutcome(difficulty=0, base_effort=0, modifier=0, symbol=Symbol.SUN, resulting_effort=0, success=True)

        r = self.state.ranger

        # At this point, action.aspect/approach are guaranteed to be enums (not str) since is_test=True
        aspect = action.aspect if isinstance(action.aspect, Aspect) else Aspect.AWA  # type guard
        approach = action.approach if isinstance(action.approach, Approach) else Approach.EXPLORATION  # type guard
        if r.energy.get(aspect, 0) < decision.energy:
            raise RuntimeError(f"Insufficient energy for {aspect}")
        r.energy[aspect] -= decision.energy

        # Step 2: Commit effort in the form of energy tokens and approach icons. TODO: Commit effort from other sources.

        base_effort, committed = self.commit_icons(r, approach, decision)

        # Discard committed cards immediately after committing
        self.discard_committed(r, committed)

        # Step 3: Apply modifiers. TODO: Take into account modifiers from non-challenge-card sources.

        mod, symbol = self.draw_challenge()
        effort = max(0, base_effort + mod)
        difficulty = action.difficulty_fn(self.state, target_id)
        self.state.add_message(f"Step 3: Draw a challenge card and apply modifiers.")
        self.state.add_message(f"You drew: [{aspect.value}]{mod:+d}, symbol [{symbol.upper()}]")



        # Step 4: Determine success or failure and apply results. TODO: notify "after you succeed/fail" listeners
        self.state.add_message(f"Step 4: Determine success or failure and apply results.")
        self.state.add_message(f"Total effort committed: {base_effort}")
        self.state.add_message(f"Test difficulty: {difficulty}")
        success = effort >= difficulty

        if success:
            self.state.add_message(f"Result: {base_effort} + ({mod:d}) = {effort} >= {difficulty}")
            self.state.add_message(f"Test succeeded!")
            action.on_success(self.state, effort, target_id)
            for listener in self.state.listeners:
                if listener.event_type == EventType.TEST_SUCCEED and listener.timing_type == TimingType.AFTER:
                    if action.verb is not None and listener.test_type is not None:
                        if action.verb.lower() == listener.test_type.lower():
                            listener.effect_fn(self.state)

        else:
            self.state.add_message(f"Result: {base_effort} + ({mod:d}) = {effort} < {difficulty}")
            self.state.add_message(f"Test failed!")
            if action.on_fail:
                action.on_fail(self.state, target_id)

        cleared : list[Card]= []
        cleared.extend(self.check_and_process_clears())

        for cleared_card in cleared:
            self.state.add_message(f"{cleared_card.title} cleared!")

        cleared.clear()
        # Step 5:  Resolve Challenge effects (dynamically from active cards)
        self.state.add_message(f"Step 5: Resolve [{symbol.upper()}] challenge effects, if any.")
        challenge_zones : list[Zone] = [
            Zone.SURROUNDINGS,     # Weather, Location, Mission
            Zone.ALONG_THE_WAY,    # TODO: player chooses order
            Zone.WITHIN_REACH,     # TODO: player chooses order
            Zone.PLAYER_AREA,      # TODO: player chooses order
        ]

        nonzero_challenges = False
        for zone in challenge_zones:
            for card in self.state.zones[zone]:
                if not card.exhausted:
                    # Get handlers directly from the card (always current)
                    handlers = card.get_symbol_handlers()
                    if handlers and symbol in handlers:
                        nonzero_challenges = True
                        handlers[symbol](self)
        if not nonzero_challenges:
            self.state.add_message("No challenge effects resolved.")
        cleared.extend(self.check_and_process_clears())

        for cleared_card in cleared:
            self.state.add_message(f"{cleared_card.title} cleared!")

        return ChallengeOutcome(
            difficulty=difficulty, 
            base_effort=base_effort, 
            modifier=mod, symbol=symbol, 
            resulting_effort=effort, 
            success=success
        )

        
    
    #check all in-play cards' clear thresholds and moves them to discard when thresholds are met
    #return list of cleared entities to display
    def check_and_process_clears(self) -> list[Card]:
        to_clear : list[Card]= []
        
        for zone in self.state.zones:
            remaining : list[Card] = []
            for card in self.state.zones[zone]:
                if CardType.PATH in card.card_types:
                    clear_type = card.clear_if_threshold()
                    if clear_type == "progress":
                        #todo: check for clear-by-progress entry
                        to_clear.append(card)
                    elif clear_type == "harm":
                        #todo: check for clear-by-harm entry
                        to_clear.append(card)
                    else:
                        remaining.append(card)
                else:
                    remaining.append(card)
            self.state.zones[zone] = remaining
        self.state.path_discard.extend(to_clear)
        return to_clear

    # Round/Phase helpers
    def phase1_draw_paths(self, count: int = 1):
        for _ in range(count):
            if not self.state.path_deck:
                break
            card = self.state.path_deck.pop(0)
            if card.starting_area is not None:
                self.state.zones[card.starting_area].append(card)
            else:
                raise ValueError("Path card drawn is missing a starting area.")


    def phase4_refresh(self):
        # Ready exhausted entities
        for zone in self.state.zones:
            for card in self.state.zones[zone]:
                card.exhausted = False
        # Future: refresh ability hooks
