from __future__ import annotations
from .models import GameState, Action, ActionTarget, Aspect, Approach, BeingCard, FeatureCard, Zone


def _targets_by_type(state: GameState, card_type: type) -> list[ActionTarget]:
    out: list[ActionTarget] = []
    for zone in state.zones.values():
        for card in zone:
            if isinstance(card, card_type):
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
            target_provider=lambda s: _targets_by_type(s, FeatureCard),
            difficulty_fn=lambda s, tid: max(1, getattr(s.get_card_by_id(tid), 'presence', 1)),
            on_success=lambda s, eff, tid: s.get_card_by_id(tid).add_progress(eff) if isinstance(s.get_card_by_id(tid), FeatureCard) else None, #type:ignore
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
            target_provider=lambda s: _targets_by_type(s, BeingCard),
            difficulty_fn=lambda s, tid: max(1, getattr(s.get_card_by_id(tid), 'presence', 1)),
            on_success=lambda s, eff, tid: s.get_card_by_id(tid).add_progress(eff) if isinstance(s.get_card_by_id(tid), BeingCard) else None, #type:ignore
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
            target_provider=lambda s: _targets_by_type(s, BeingCard),
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
            target_provider=None,
            difficulty_fn=lambda _s, _t: 1,
            on_success=lambda s, eff, _t: None,  # No deck yet; placeholder
            source_id="common",
            source_title="Common Test",
        )
    )

    return actions


def provide_card_tests(state: GameState) -> list[Action]:
    actions: list[Action] = []
    # Overgrown Thicket (AWA + Exploration): add progress equal to effort
    for card in state.all_cards_in_play():
        if card.title == "Overgrown Thicket":
            actions.append(
                Action(
                    id=f"test-{card.id}",
                    name=f"{card.title} (AWA + Exploration)",
                    aspect=Aspect.AWA,
                    approach=Approach.EXPLORATION,
                    target_provider=None,
                    difficulty_fn=lambda _s, _t: 1,
                    on_success=lambda s, eff, _t, eid=card.id: (c.add_progress(eff) if (c := s.get_card_by_id(eid)) and hasattr(c, 'add_progress') else None), #type:ignore
                    source_id=card.id,
                    source_title=card.title,
                )
            )

        if card.title == "Sunberry Bramble":
            actions.append(
                Action(
                    id=f"test-{card.id}",
                    name=f"{card.title} (AWA + Reason) [2]",
                    aspect=Aspect.AWA,
                    approach=Approach.REASON,
                    target_provider=None,
                    difficulty_fn=lambda _s, _t: 2,
                    on_success=lambda s, _eff, _t, eid=card.id: (c.add_harm(1) if (c := s.get_card_by_id(eid)) and hasattr(c, 'add_harm') else None), #type:ignore
                    on_fail=lambda s, _t: None,  # Fatigue not modeled
                    source_id=card.id,
                    source_title=card.title,
                )
            )

        if card.title == "Sitka Doe":
            actions.append(
                Action(
                    id=f"test-{card.id}",
                    name=f"{card.title} (SPI + Conflict) [X=presence]",
                    aspect=Aspect.SPI,
                    approach=Approach.CONFLICT,
                    target_provider=None,
                    difficulty_fn=lambda _s, _t: 1,
                    on_success=lambda s, _eff, _t, eid=card.id: (setattr(c, "area", Zone.ALONG_THE_WAY) if (c := s.get_card_by_id(eid)) else None),
                    source_id=card.id,
                    source_title=card.title,
                )
            )

    return actions

