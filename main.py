
import os
from src.models import Card, RangerState, GameState, Action, Aspect, Symbol, Approach, Zone, CardType
from src.engine import GameEngine
from src.registry import provide_common_tests, provide_card_tests
from src.view import render_state, choose_action, choose_target, choose_commit
from src.decks import build_woods_path_deck
from src.cards import OvergrownThicket, WalkWithMe, ADearFriend


def pick_demo_cards() -> list[Card]:
    

    walk_with_me_0 = WalkWithMe()
    walk_with_me_1 = WalkWithMe()
    a_dear_friend_0 = ADearFriend()
    a_dear_friend_1 = ADearFriend()
    exploration_dummy = Card(id="demo-explore-1", title="Demo Explore +1", approach_icons={Approach.EXPLORATION: 1})
    reason_dummy = Card(id="demo-reason-1", title="Demo Reason +1", approach_icons={Approach.REASON: 1})
    conflict_dummy = Card(id="demo-conflict-1", title="Demo Conflict +1", approach_icons={Approach.CONFLICT: 1})

    return [walk_with_me_0, walk_with_me_1, a_dear_friend_0, a_dear_friend_1, exploration_dummy, reason_dummy, conflict_dummy]


def clear_screen() -> None:
    # Basic clear that works on Windows terminals
    os.system("cls" if os.name == "nt" else "clear")


def show_state(state: GameState) -> None:
    # Backward-compat wrapper to the view module
    render_state(state)


def register_symbol_effects(eng: GameEngine, state:GameState) -> None:
    # Overgrown Thicket: Mountain discards 1 progress
    def mountain_thicket(in_state: GameState) -> None:
        thicket = next(x for x in in_state.all_cards_in_play() if x.title == "Overgrown Thicket")
        if CardType.FEATURE in thicket.card_types:
            if thicket.progress > 0:
                thicket.progress = max(0, thicket.progress - 1)
                print(f"Challenge: Mountain on {thicket.title} discards 1 progress (now {thicket.progress}).")
            else:
                print(f"Challenge: Mountain on {thicket.title} (no progress to discard).")

    for card in state.all_cards_in_play():
        if card.title == "Overgrown Thicket":
            eng.register_symbol_handler((card.id, Symbol.MOUNTAIN), mountain_thicket)
    


def build_demo_state() -> GameState:
    hand = pick_demo_cards()

    #Add Overgrown Thicket
    thicket = OvergrownThicket()

    # Add Sunberry Bramble (Feature)
    bramble = Card(
        id="sunberry-bramble-01",
        title="Sunberry Bramble",
        card_types={CardType.PATH, CardType.FEATURE},
        presence=1,
        progress_threshold=3,
        harm_threshold=2,
        starting_area=Zone.WITHIN_REACH,
    )

    # Add Sitka Doe (Being)
    doe = Card(
        id="sitka-doe-01",
        title="Sitka Doe",
        card_types={CardType.PATH, CardType.BEING},
        presence=1,
        progress_threshold=4,
        harm_threshold=2,
        starting_area=Zone.WITHIN_REACH,
    )

    # Add Midday Sun (Weather)
    weather = Card(
        id="midday-sun-01",
        title="Midday Sun",
        card_types={CardType.WEATHER},
        starting_area=Zone.SURROUNDINGS,
    )

    ranger = RangerState(name="Demo Ranger", hand=hand, energy={Aspect.AWA: 99, Aspect.FIT: 99, Aspect.SPI: 99, Aspect.FOC: 99})
    # Build a simple path deck from woods, excluding the ones already in play
    deck = build_woods_path_deck()
    surroundings : list[Card] = [weather]
    along_the_way : list[Card] = []
    within_reach : list[Card] = [thicket, bramble, doe]
    player_area : list[Card] = []
    current_zones : dict[Zone,list[Card]]= {Zone.SURROUNDINGS : surroundings, Zone.ALONG_THE_WAY : along_the_way, Zone.WITHIN_REACH : within_reach, Zone.PLAYER_AREA : player_area}
    state = GameState(ranger=ranger, zones=current_zones, round_number=1, path_deck=deck)
    return state


def menu_and_run(engine: GameEngine) -> None:
    while True:
        # Phase 1: Draw path cards
        clear_screen()
        print(f"Round {engine.state.round_number} — Phase 1: Draw Paths")
        engine.phase1_draw_paths(count=1)
        show_state(engine.state)
        input("Enter to proceed to Phase 2...")

        # Phase 2: Actions until Rest
        while True:
            clear_screen()
            print(f"Round {engine.state.round_number} — Phase 2: Actions")
            show_state(engine.state)

            # derive actions
            actions = provide_card_tests(engine.state) + provide_common_tests(engine.state)
            # add system Rest action
            actions.append(Action(
                id="system-rest",
                name="Rest (end actions)",
                aspect="",
                approach="",
                is_test=False,
                on_success=lambda s, _e, _t: None,
            ))
            act = choose_action(actions)
            if not act:
                # treat as cancel to end the run
                return

            if act.id == "system-rest":
                break

            target_id = choose_target(engine.state, act)
            decision = choose_commit(act, len(engine.state.ranger.hand)) if act.is_test else None

            try:
                outcome = engine.perform_action(act, decision or __import__('src.models', fromlist=['CommitDecision']).CommitDecision([]), target_id)
            except RuntimeError as e:
                print(str(e))
                input("Enter to continue...")
                continue

            if act.is_test:
                print("")
                print(f"Total effort committed: {outcome.base_effort}")
                print(f"Test difficulty: {outcome.difficulty}")
                print(f"Challenge draw: {outcome.modifier:+d}, symbol [{outcome.symbol.upper()}]")
                print(f"Resulting effort: {outcome.base_effort} + ({outcome.modifier:d}) = {outcome.resulting_effort}")
                if outcome.success:
                    print(f"{outcome.resulting_effort} >= {outcome.difficulty}")
                    print(f"Test succeeded!")
                else:
                    print(f"{outcome.resulting_effort} < {outcome.difficulty}")
                    print(f"Test failed!")
                for cleared_card in outcome.cleared:
                    print(f"{cleared_card.title} cleared!")
                input("Enter to continue...")

        # Phase 3: Travel (skipped)
        clear_screen()
        print(f"Round {engine.state.round_number} — Phase 3: Travel (skipped)")
        show_state(engine.state)
        input("Enter to proceed to Phase 4...")

        # Phase 4: Refresh
        clear_screen()
        print(f"Round {engine.state.round_number} — Phase 4: Refresh")
        engine.phase4_refresh()
        show_state(engine.state)
        input("Enter to start next round...")

        engine.state.round_number += 1


def main() -> None:
    state = build_demo_state()
    engine = GameEngine(state)
    register_symbol_effects(engine, state)
    menu_and_run(engine)


if __name__ == "__main__":
    main()
