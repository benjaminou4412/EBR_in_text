from __future__ import annotations
from .models import GameState, Action, ActionTarget, Aspect, Approach, CardType
from .engine import GameEngine


def _targets_by_type(state: GameState, card_type: CardType) -> list[ActionTarget]:
    out: list[ActionTarget] = []
    for zone in state.zones.values():
        for card in zone:
            if card_type in card.card_types:
                out.append(ActionTarget(id=card.id, title=card.title))
    return out

def provide_common_tests(state: GameState) -> list[Action]:
    actions: list[Action] = []

    #todo: actually have it target locations, not just features
    # Traverse: FIT + [Exploration], target Feature or Location, diff X=presence
    actions.append(
        Action(
            id="common-traverse",
            name="Traverse (FIT + Exploration) [X=presence]",
            aspect=Aspect.FIT,
            approach=Approach.EXPLORATION,
            verb="Traverse",
            target_provider=lambda s: _targets_by_type(s, CardType.FEATURE),
            difficulty_fn=lambda s, tid: max(1, getattr(s.get_card_by_id(tid), 'presence', 1)),
            on_success=lambda s, eff, tid: s.get_card_by_id(tid).add_progress(eff) if CardType.FEATURE in s.get_card_by_id(tid).card_types else None, #type:ignore
            on_fail=lambda s, _tid: setattr(s.ranger, "injury", s.ranger.injury + 1),
            source_id="common",
            source_title="Common Test",
        )
    )

    # Connect: SPI + [Connection], target Being, diff X
    actions.append(
        Action(
            id="common-connect",
            name="Connect (SPI + Connection) [X=presence]",
            aspect=Aspect.SPI,
            approach=Approach.CONNECTION,
            verb="Connect",
            target_provider=lambda s: _targets_by_type(s, CardType.BEING),
            difficulty_fn=lambda s, tid: max(1, getattr(s.get_card_by_id(tid), 'presence', 1)),
            on_success=lambda s, eff, tid: s.get_card_by_id(tid).add_progress(eff) if CardType.BEING in s.get_card_by_id(tid).card_types else None, #type:ignore
            source_id="common",
            source_title="Common Test",
        )
    )

    # Avoid: AWA + [Conflict], target Being, diff X; on success exhaust
    actions.append(
        Action(
            id="common-avoid",
            name="Avoid (AWA + Conflict) [X=presence]",
            aspect=Aspect.AWA,
            approach=Approach.CONFLICT,
            verb="Avoid",
            target_provider=lambda s: _targets_by_type(s, CardType.BEING),
            difficulty_fn=lambda s, tid: max(1, getattr(s.get_card_by_id(tid), 'presence', 1)),
            on_success=lambda s, _eff, tid: setattr(s.get_card_by_id(tid), 'exhausted', True),
            source_id="common",
            source_title="Common Test",
        )
    )

    # Remember: FOC + [Reason], no target, diff 1.
    actions.append(
        Action(
            id="common-remember",
            name="Remember (FOC + Reason) [1]",
            aspect=Aspect.FOC,
            approach=Approach.REASON,
            verb="Remember",
            target_provider=None,
            difficulty_fn=lambda _s, _t: 1,
            on_success=lambda s, eff, _t: None,  # No deck yet; placeholder
            source_id="common",
            source_title="Common Test",
        )
    )

    return actions


def provide_card_tests(state: GameState) -> list[Action]:
    """Scan all cards in play and collect tests they provide"""
    actions: list[Action] = []
    for card in state.all_cards_in_play():
        tests = card.get_tests()
        if tests is not None:
            actions.extend(tests)
    return actions


def register_card_symbol_effects(engine: GameEngine, state: GameState) -> None:
    """Scan all cards in play and register their symbol handlers"""
    for card in state.all_cards_in_play():
        symbols = card.get_symbol_handlers()
        if symbols is not None:
            for symbol, handler in symbols.items():
                engine.register_symbol_handler((card.id, symbol), handler)

