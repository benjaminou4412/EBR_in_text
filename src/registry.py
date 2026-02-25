from __future__ import annotations
from .models import GameState, Action, Aspect, Approach, CardType, Card
from .engine import GameEngine


def provide_common_tests(state: GameState) -> list[Action]:
    """Provide the four common tests available to all rangers"""
    actions: list[Action] = []

    # Traverse: FIT + [Exploration], target Feature or Location, diff X=presence
    def traverse_success(e: GameEngine, eff: int, card: Card | None) -> None:
        if card and (card.has_type(CardType.FEATURE) or card.has_type(CardType.LOCATION)):
            msg = card.add_progress(eff)
            e.add_message(msg)

    def traverse_fail(e: GameEngine, eff: int, card: Card | None) -> None: 
        e.state.ranger.injure(e)

    def get_traverse_difficulty(e: GameEngine, card: Card | None) -> int:
        if card:
            presence = card.get_current_presence(e)
            return max(1, presence if presence is not None else 1)
        return 1

    actions.append(
        Action(
            id="common-traverse",
            name="Traverse (FIT + Exploration) [X=presence]",
            aspect=Aspect.FIT,
            approach=Approach.EXPLORATION,
            verb="Traverse",
            target_provider=lambda s: s.features_in_play() + [s.location],
            difficulty_fn=get_traverse_difficulty,
            on_success=traverse_success,
            on_fail=traverse_fail,
            source_id="common",
            source_title="Common Test",
        )
    )

    # Connect: SPI + [Connection], target Being, diff X=presence
    def connect_success(e: GameEngine, eff: int, card: Card | None) -> None:
        if card and card.has_type(CardType.BEING):
            msg = card.add_progress(eff)
            e.add_message(msg)

    def get_connect_difficulty(e: GameEngine, card: Card | None) -> int:
        if card:
            presence = card.get_current_presence(e)
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

    def get_avoid_difficulty(e: GameEngine, card: Card | None) -> int:
        if card:
            presence = card.get_current_presence(e)
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

    # Avoid: FOC + [Reason], no target, diff 1; on success scout ranger deck equal to effort, then draw
    def remember_success(e: GameEngine, eff: int, _card: Card | None) -> None:  # noqa: ARG001
        deck = e.state.ranger.deck
        e.scout_cards(deck, eff)
        card, day_ended = e.state.ranger.draw_card(e)
        if card is None:
            if day_ended:
                e.day_has_ended = True
                return
            else:
                raise RuntimeError(f"Day should end when deck is empty!")

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
            on_success=remember_success, 
            source_id="common",
            source_title="Common Test",
        )
    )


    return actions


def provide_card_tests(engine: GameEngine) -> list[Action]:
    """Scan all cards in play and collect tests they provide, taking into account Obstacles"""
    actions: list[Action] = []
    all_cards_except_past_obstacle = engine.filter_by_obstacles(engine.state.all_cards_in_play())
    if all_cards_except_past_obstacle is None:
        return []
    for card in all_cards_except_past_obstacle:
        tests = card.get_tests()
        if tests is not None:
            actions.extend(tests)
    return actions

def provide_exhaust_abilities(state: GameState) -> list[Action]:
    """Scan all cards in play and collect Exhaust abilities from non-exhausted ones"""
    actions: list[Action] = []
    for card in state.all_cards_in_play():
        if card.is_ready():
            exhaust_abilities = card.get_exhaust_abilities()
            if exhaust_abilities is not None:
                actions.extend(exhaust_abilities)
    return actions

def filter_tests_by_targets(tests: list[Action], state: GameState) -> list[Action]:
    """
    Filter tests to only include those that can be initiated.

    - If target_provider is None: test requires no target, always included
    - If target_provider returns empty list: test needs target but has none, excluded
    - If target_provider returns non-empty list: test has valid targets, included
    """
    filtered: list[Action] = []
    for test in tests:
        if not test.is_test:
            # Not a test, include it
            filtered.append(test)
            continue

        if test.target_provider is None:
            # Test requires no target (like Remember)
            filtered.append(test)
        else:
            # Test requires target - check if any exist
            targets = test.target_provider(state)
            if targets and len(targets) > 0:
                filtered.append(test)
            # If targets is empty, exclude this test

    return filtered


def provide_play_options(engine: GameEngine) -> list[Action]:
    """Provide play actions for non-response moments and other playable cards in hand.
    Filters by can_be_played() to only show cards the player can afford and have valid targets for."""
    actions: list[Action] = []
    for card in engine.state.ranger.hand:
        # Check if card can be played (energy + targets)
        if not card.can_be_played(engine):
            continue

        # Get the play action
        play_action = card.get_play_action()
        if play_action is not None:
            actions.append(play_action)
    return actions

def get_search_test(source_card: Card, verb: str) -> Action:
    """Many cards have a similar test (albeit with varying verbs) with the effect 
    "scout path cards equal to your effort, then draw 1 path card. This helper
    function provides that test to those cards"""
    return Action(
        id=source_card.id + "-search-test",
        name=source_card.title + " Search Test",
        aspect=Aspect.AWA,
        approach=Approach.CONNECTION,
        is_test=True,
        verb=verb,
        target_provider=lambda _s: [source_card],
        on_success=_search_test_success,
        source_id=source_card.id,
        source_title=source_card.title
    )

def _search_test_success(engine: GameEngine, effort: int, _target: Card | None) -> None:
    """Scout path cards equal to your effort, then draw 1 path card"""
    deck = engine.state.path_deck
    engine.scout_cards(deck, effort)
    engine.draw_path_card(None, None)
