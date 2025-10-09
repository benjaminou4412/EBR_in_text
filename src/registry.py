from __future__ import annotations
from .models import GameState, Action, ActionTarget, Aspect, Approach, FeatureCard, Card, BeingCard, FeatureCard


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
            difficulty_fn=lambda s, tid: max(1, next(c.presence for c in s.features_in_play if c.id == tid)),
            on_success=lambda s, eff, tid: next(c for c in s.features_in_play if c.id == tid).add_progress(eff),
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
            target_provider=lambda s: _targets_by_type(s, "Being"),
            difficulty_fn=lambda s, tid: max(1, next(e.presence for e in s.entities if e.id == tid)),
            on_success=lambda s, eff, tid: next(e for e in s.entities if e.id == tid).add_progress(eff),
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
            target_provider=lambda s: _targets_by_type(s, "Being"),
            difficulty_fn=lambda s, tid: max(1, next(e.presence for e in s.entities if e.id == tid)),
            on_success=lambda s, _eff, tid: setattr(next(e for e in s.entities if e.id == tid), "exhausted", True),
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
    for e in state.entities:
        if e.id == "woods-011-overgrown-thicket":
            actions.append(
                Action(
                    id=f"test-{e.id}",
                    name=f"{e.title} (AWA + Exploration)",
                    aspect=Aspect.AWA,
                    approach=Approach.EXPLORATION,
                    target_provider=None,
                    difficulty_fn=lambda _s, _t: 1,
                    on_success=lambda s, eff, _t, eid=e.id: next(x for x in s.entities if x.id == eid).add_progress(eff),
                    source_id=e.id,
                    source_title=e.title,
                )
            )

        if e.id == "woods-009-sunberry-bramble":
            actions.append(
                Action(
                    id=f"test-{e.id}",
                    name=f"{e.title} (AWA + Reason) [2]",
                    aspect=Aspect.AWA,
                    approach=Approach.REASON,
                    target_provider=None,
                    difficulty_fn=lambda _s, _t: 2,
                    on_success=lambda s, _eff, _t, eid=e.id: next(x for x in s.entities if x.id == eid).add_harm(1),
                    on_fail=lambda s, _t: None,  # Fatigue not modeled
                    source_id=e.id,
                    source_title=e.title,
                )
            )

        if e.id == "woods-007-sitka-doe":
            actions.append(
                Action(
                    id=f"test-{e.id}",
                    name=f"{e.title} (SPI + Conflict) [X=presence]",
                    aspect=Aspect.SPI,
                    approach=Approach.CONFLICT,
                    target_provider=None,
                    difficulty_fn=lambda _s, _t, pres=e.presence: max(1, pres),
                    on_success=lambda s, _eff, _t, eid=e.id: setattr(next(x for x in s.entities if x.id == eid), "area", "along_the_way"),
                    source_id=e.id,
                    source_title=e.title,
                )
            )

        if e.id == "weather-002-midday-sun":
            actions.append(
                Action(
                    id=f"test-{e.id}",
                    name=f"{e.title} (FOC + Reason)",
                    aspect=Aspect.FOC,
                    approach=Approach.REASON,
                    target_provider=None,
                    difficulty_fn=lambda _s, _t: 1,
                    on_success=lambda s, _eff, _t, eid=e.id: setattr(next(x for x in s.entities if x.id == eid), "clouds", next(x for x in s.entities if x.id == eid).clouds + 1),
                    source_id=e.id,
                    source_title=e.title,
                )
            )

    return actions

