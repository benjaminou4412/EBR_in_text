from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Optional, cast
from .models import GameState, Action, CommitDecision, RangerState, Card, Entity
from .challenge import draw_challenge


@dataclass
class ChallengeOutcome:
    base_effort: int
    modifier: int
    difficulty: int
    symbol: str
    resulting_effort: int
    success: bool
    cleared: list[Entity] = field(default_factory=lambda: cast(list[Entity], [])) 


class GameEngine:
    def __init__(self, state: GameState, challenge_drawer: Callable[[], tuple[int, str]] = draw_challenge):
        self.state = state
        self.draw_challenge = challenge_drawer
        # challenge symbol effects dispatch (entity-id + symbol -> callable)
        self.symbol_handlers: dict[tuple[str, str], Callable[[GameState], None]] = {}

    def register_symbol_handler(self, key: tuple[str, str], fn: Callable[[GameState], None]):
        self.symbol_handlers[key] = fn

    def commit_icons(self, ranger: RangerState, approach: str, decision: CommitDecision) -> tuple[int, list[int]]:
        total = decision.energy
        valid_indices : list[int] = []
        for idx in decision.hand_indices:
            if not (0 <= idx < len(ranger.hand)):
                continue
            c: Card = ranger.hand[idx]
            val = c.approach.get(approach)
            if val:
                total += val
                valid_indices.append(idx)
        return total, valid_indices

    def discard_committed(self, ranger: RangerState, committed_indices: list[int]) -> None:
        for i in sorted(committed_indices, reverse=True):
            del ranger.hand[i]

    def perform_action(self, action: Action, decision: CommitDecision, target_id: Optional[str]) -> ChallengeOutcome:
        # Non-test actions (e.g., Rest) skip challenge + energy
        if not action.is_test:
            action.on_success(self.state, 0, target_id)
            return ChallengeOutcome(difficulty=0, base_effort=0, modifier=0, symbol="", resulting_effort=0, success=True, cleared=[])

        r = self.state.ranger
        if r.energy.get(action.aspect, 0) < decision.energy:
            raise RuntimeError(f"Insufficient energy for {action.aspect}")
        r.energy[action.aspect] -= decision.energy

        base_effort, committed = self.commit_icons(r, action.approach, decision)
        mod, symbol = self.draw_challenge()
        effort = max(0, base_effort + mod)
        difficulty = action.difficulty_fn(self.state, target_id)
        success = effort >= difficulty

        if success:
            action.on_success(self.state, effort, target_id)
        else:
            if action.on_fail:
                action.on_fail(self.state, target_id)

        cleared : list[Entity]= []
        cleared.extend(self.check_and_process_clears())
        # Handle symbol effects (registered externally)
        for e in self.state.entities:
            handler = self.symbol_handlers.get((e.id, symbol))
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
    
    #check all in-play entities' clear thresholds and moves them to discard when thresholds are met
    #return list of cleared entities to display
    def check_and_process_clears(self) -> list[Entity]:
        to_clear : list[Entity]= []
        remaining : list[Entity] = []
        
        for entity in self.state.entities:
            clear_type = entity.clear_if_threshold()
            if clear_type == "progress":
                #todo: check for clear-by-progress entry
                to_clear.append(entity)
            elif clear_type == "harm":
                #todo: check for clear-by-harm entry
                to_clear.append(entity)
            else:
                remaining.append(entity)
        self.state.entities = remaining
        self.state.path_discard.extend(to_clear)
        return to_clear

    # Round/Phase helpers
    def phase1_draw_paths(self, count: int = 1):
        for _ in range(count):
            if not self.state.path_deck:
                break
            card = self.state.path_deck.pop(0)
            self.state.entities.append(card)

    def phase4_refresh(self):
        # Ready exhausted entities
        for e in self.state.entities:
            e.exhausted = False
        # Future: weather refresh hooks
