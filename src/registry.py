from __future__ import annotations
from .models import GameState, Action, Aspect, Approach, CardType, Card
from .engine import GameEngine


def provide_common_tests(state: GameState) -> list[Action]:
    """Provide the four common tests available to all rangers"""
    actions: list[Action] = []

    # Traverse: FIT + [Exploration], target Feature or Location, diff X=presence
    def traverse_success(e: GameEngine, eff: int, card: Card | None) -> None:
        if card and CardType.FEATURE in card.card_types:
            msg = card.add_progress(eff)
            e.add_message(msg)

    def traverse_fail(e: GameEngine, eff: int, card: Card | None) -> None:  # noqa: ARG001
        e.state.ranger.injury += 1

    def get_traverse_difficulty(s: GameState, card: Card | None) -> int:
        if card:
            presence = card.get_current_presence()
            return max(1, presence if presence is not None else 1)
        return 1

    actions.append(
        Action(
            id="common-traverse",
            name="Traverse (FIT + Exploration) [X=presence]",
            aspect=Aspect.FIT,
            approach=Approach.EXPLORATION,
            verb="Traverse",
            target_provider=lambda s: s.features_in_play(),
            difficulty_fn=get_traverse_difficulty,
            on_success=traverse_success,
            on_fail=traverse_fail,
            source_id="common",
            source_title="Common Test",
        )
    )

    # Connect: SPI + [Connection], target Being, diff X=presence
    def connect_success(e: GameEngine, eff: int, card: Card | None) -> None:
        if card and CardType.BEING in card.card_types:
            msg = card.add_progress(eff)
            e.add_message(msg)

    def get_connect_difficulty(s: GameState, card: Card | None) -> int:
        if card:
            presence = card.get_current_presence()
            return max(1, presence if presence is not None else 1)
        return 1

    actions.append(
        Action(
            id="common-connect",
            name="Connect (SPI + Connection) [X=presence]",
            aspect=Aspect.SPI,
            approach=Approach.CONNECTION,
            verb="Connect",
            target_provider=lambda s: s.beings_in_play(),
            difficulty_fn=get_connect_difficulty,
            on_success=connect_success,
            source_id="common",
            source_title="Common Test",
        )
    )

    # Avoid: AWA + [Conflict], target Being, diff X=presence; on success exhaust
    def avoid_success(e: GameEngine, _eff: int, card: Card | None) -> None:  # noqa: ARG001
        if card:
            e.add_message(card.exhaust())
        else:
            raise RuntimeError("Card not found!")

    def get_avoid_difficulty(s: GameState, card: Card | None) -> int:
        if card:
            presence = card.get_current_presence()
            return max(1, presence if presence is not None else 1)
        return 1

    actions.append(
        Action(
            id="common-avoid",
            name="Avoid (AWA + Conflict) [X=presence]",
            aspect=Aspect.AWA,
            approach=Approach.CONFLICT,
            verb="Avoid",
            target_provider=lambda s: s.beings_in_play(),
            difficulty_fn=get_avoid_difficulty,
            on_success=avoid_success,
            source_id="common",
            source_title="Common Test",
        )
    )

    # Remember: FOC + [Reason], no target, diff 1
    actions.append(
        Action(
            id="common-remember",
            name="Remember (FOC + Reason) [1]",
            aspect=Aspect.FOC,
            approach=Approach.REASON,
            verb="Remember",
            target_provider=None,
            difficulty_fn=lambda _s, _t: 1,
            on_success=lambda e, eff, _t: None,  # No deck manipulation yet; placeholder
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

