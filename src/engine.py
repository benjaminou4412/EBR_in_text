from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Optional, Tuple
from .models import GameState, Action, CommitDecision, RangerState, Card
from .challenge import draw_challenge


@dataclass
class ChallengeOutcome:
    modifier: int
    symbol: str
    effort: int
    success: bool


class GameEngine:
    def __init__(self, state: GameState, challenge_drawer: Callable[[], Tuple[int, str]] = draw_challenge):
        self.state = state
        self.draw_challenge = challenge_drawer
        # challenge symbol effects dispatch (entity-id + symbol -> callable)
        self.symbol_handlers = {}

    def register_symbol_handler(self, key: Tuple[str, str], fn: Callable[[GameState], None]):
        self.symbol_handlers[key] = fn

    def commit_icons(self, ranger: RangerState, approach: str, decision: CommitDecision) -> Tuple[int, list[int]]:
        total = 0
        valid_indices = []
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
        # Spend energy requirement
        r = self.state.ranger
        if r.energy.get(action.aspect, 0) < 1:
            raise RuntimeError(f"Insufficient energy for {action.aspect}")
        r.energy[action.aspect] -= 1

        base_icons, committed = self.commit_icons(r, action.approach, decision)
        mod, symbol = self.draw_challenge()
        effort = max(0, base_icons + mod)
        difficulty = action.difficulty_fn(self.state, target_id)
        success = effort >= difficulty

        if success:
            action.on_success(self.state, effort, target_id)
        else:
            if action.on_fail:
                action.on_fail(self.state, target_id)

        # Handle symbol effects (registered externally)
        for e in self.state.entities:
            handler = self.symbol_handlers.get((e.id, symbol))
            if handler:
                handler(self.state)

        # Discard committed cards last
        self.discard_committed(r, committed)
        return ChallengeOutcome(modifier=mod, symbol=symbol, effort=effort, success=success)

