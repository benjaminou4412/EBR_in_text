from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Optional, cast
from .models import GameState, Action, CommitDecision, RangerState, Card, RangerCard, PathCard, Symbol, Aspect, Approach, Zone
from .challenge import draw_challenge


@dataclass
class ChallengeOutcome:
    base_effort: int
    modifier: int
    difficulty: int
    symbol: Symbol
    resulting_effort: int
    success: bool
    cleared: list[Card] = field(default_factory=lambda: cast(list[Card], [])) 


class GameEngine:
    def __init__(self, state: GameState, challenge_drawer: Callable[[], tuple[int, Symbol]] = draw_challenge):
        self.state = state
        self.draw_challenge = challenge_drawer
        # challenge symbol effects dispatch (entity-id + symbol -> callable)
        self.symbol_handlers: dict[tuple[str, Symbol], Callable[[GameState], None]] = {}

    def register_symbol_handler(self, key: tuple[str, Symbol], fn: Callable[[GameState], None]):
        self.symbol_handlers[key] = fn

    def commit_icons(self, ranger: RangerState, approach: Approach, decision: CommitDecision) -> tuple[int, list[int]]:
        total = decision.energy
        valid_indices : list[int] = []
        for idx in decision.hand_indices:
            if not (0 <= idx < len(ranger.hand)):
                continue
            c: RangerCard = ranger.hand[idx]
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

        base_effort, committed = self.commit_icons(r, approach, decision)
        mod, symbol = self.draw_challenge()
        effort = max(0, base_effort + mod)
        difficulty = action.difficulty_fn(self.state, target_id)
        success = effort >= difficulty

        if success:
            action.on_success(self.state, effort, target_id)
        else:
            if action.on_fail:
                action.on_fail(self.state, target_id)

        cleared : list[Card]= []
        cleared.extend(self.check_and_process_clears())

        # Handle symbol effects (registered externally)

        challenge_zones : list[Zone] = [
            Zone.SURROUNDINGS,     # Weather, Location, Mission
            Zone.ALONG_THE_WAY,    # TODO: player chooses order
            Zone.WITHIN_REACH,     # TODO: player chooses order
            Zone.PLAYER_AREA,      # TODO: player chooses order
        ]

        for zone in challenge_zones:
            for card in self.state.zones[zone]:
                if not card.exhausted:
                    handler = self.symbol_handlers.get((card.id, symbol))
                    if handler:
                        handler(self.state)

        cleared.extend(self.check_and_process_clears())
        # Discard committed cards last
        self.discard_committed(r, committed)
        return ChallengeOutcome(
            difficulty=difficulty, 
            base_effort=base_effort, 
            modifier=mod, symbol=symbol, 
            resulting_effort=effort, 
            success=success,
            cleared=cleared
        )
    
    #check all in-play cards' clear thresholds and moves them to discard when thresholds are met
    #return list of cleared entities to display
    def check_and_process_clears(self) -> list[PathCard]:
        to_clear : list[PathCard]= []
        
        for zone in self.state.zones:
            remaining : list[Card] = []
            for card in self.state.zones[zone]:
                if isinstance(card, PathCard):
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
            self.state.zones[card.area].append(card)


    def phase4_refresh(self):
        # Ready exhausted entities
        for zone in self.state.zones:
            for card in self.state.zones[zone]:
                card.exhausted = False
        # Future: refresh ability hooks
