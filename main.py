
import os
import random
from src.models import Card, RangerState, GameState, Action, Aspect, Approach, Zone, CardType
from src.engine import GameEngine
from src.registry import provide_common_tests, provide_card_tests
from src.view import render_state, choose_action, choose_action_target, choose_commit, choose_target, display_and_clear_messages, choose_response
from src.decks import build_woods_path_deck
from src.cards import OvergrownThicket, SunberryBramble, SitkaDoe, WalkWithMe, ADearFriend, ProwlingWolhund, SitkaBuck


def pick_demo_cards() -> list[Card]:


    walk_with_me_0 : Card = WalkWithMe()
    a_dear_friend_0 : Card= ADearFriend()
    exploration_dummies : list[Card] = []
    for _ in range(5):
        exploration_dummies.append(Card(title="Demo Explore +1", approach_icons={Approach.EXPLORATION: 1}))
    conflict_dummies : list[Card]  = []
    for _ in range(5):
        conflict_dummies.append(Card(title="Demo Conflict +1", approach_icons={Approach.CONFLICT: 1}))
    reason_dummies : list[Card]  = []
    for _ in range(5):
        reason_dummies.append(Card(title="Demo Reason +1", approach_icons={Approach.REASON: 1}))
    connection_dummies : list[Card]  = []
    for _ in range(5):
        connection_dummies.append(Card(title="Demo Connection +1", approach_icons={Approach.CONNECTION: 1}))

    deck = exploration_dummies + conflict_dummies + reason_dummies + connection_dummies
    random.shuffle(deck)
    top_deck: list[Card] = [walk_with_me_0, a_dear_friend_0]

    return top_deck + deck


def clear_screen() -> None:
    # Basic clear that works on Windows terminals
    os.system("cls" if os.name == "nt" else "clear")





def build_demo_state() -> GameState:
    ranger_deck = pick_demo_cards()

    #Add Overgrown Thicket
    thicket = OvergrownThicket()

    # Add Sunberry Bramble 
    bramble = SunberryBramble()

    # Add Sitka Doe
    doe = SitkaDoe()

    # Add two Sitka Buck
    buck_0 = SitkaBuck()
    #buck_1 = SitkaBuck()

    # Add two Prowling Wolhunds
    wol_0 = ProwlingWolhund()
    #wol_1 = ProwlingWolhund()

    # Add Midday Sun (Weather)
    weather = Card(
        id="midday-sun-01",
        title="Midday Sun",
        card_types={CardType.WEATHER},
        starting_area=Zone.SURROUNDINGS,
    )

    ranger = RangerState(name="Demo Ranger", hand=[], aspects={Aspect.AWA: 99, Aspect.FIT: 99, Aspect.SPI: 99, Aspect.FOC: 99}, deck=ranger_deck)
    # Build a simple path deck from woods, excluding the ones already in play
    deck = build_woods_path_deck()
    surroundings : list[Card] = [weather]
    along_the_way : list[Card] = [wol_0, buck_0]
    within_reach : list[Card] = [thicket, bramble, doe]
    player_area : list[Card] = []
    current_zones : dict[Zone,list[Card]]= {Zone.SURROUNDINGS : surroundings, Zone.ALONG_THE_WAY : along_the_way, Zone.WITHIN_REACH : within_reach, Zone.PLAYER_AREA : player_area}
    state = GameState(ranger=ranger, zones=current_zones, round_number=1, path_deck=deck)
    # Note: Cards drawn to hand - listeners will be registered when engine is created
    for _ in range(5):
        _, _, _ = state.ranger.draw_card()  # Ignore return values during setup
    return state


def menu_and_run(engine: GameEngine) -> None:
    # Print welcome header once
    print("=== Earthborne Rangers - Demo ===")
    print("Welcome to the demo! Press Enter to begin...")
    input()

    while True:
        # Phase 1: Draw path cards
        clear_screen()
        engine.phase1_draw_paths(count=1)
        render_state(engine.state, phase_header=f"Round {engine.state.round_number} — Phase 1: Draw Paths")
        print("")
        print("--- Event log ---")
        display_and_clear_messages(engine)
        input("Press Enter to proceed to Phase 2...")

        # Phase 2: Actions until Rest
        while True:
            clear_screen()
            render_state(engine.state, phase_header=f"Round {engine.state.round_number} — Phase 2: Actions")

            print("")

            print("--- Event log and choices ---")

            # derive actions
            actions = provide_card_tests(engine.state) + provide_common_tests(engine.state)
            # add system Rest action
            actions.append(Action(
                id="system-rest",
                name="Rest (end actions)",
                verb="Rest",
                aspect="",
                approach="",
                is_test=False,
                on_success=lambda s, _e, _t: None,
            ))
            # add system End Day action
            actions.append(Action(
                id="system-end-day",
                name="End the day",
                verb="End the day",
                aspect="",
                approach="",
                is_test=False,
                on_success=lambda s, _e, _t: None,
            ))

            # Keep prompting until we get a valid action
            act = None
            while not act:
                act = choose_action(actions, engine.state, engine)

            if act.id == "system-rest":
                print("\nYou rest and end your turn.")
                input("Press Enter to proceed to Phase 3...")
                break

            if act.id == "system-end-day":
                engine.end_day()
                display_and_clear_messages(engine)
                print("\nThe day has ended. Demo complete!")
                input("Press Enter to exit...")
                return
            #TODO: Handle Exhaust actions and Play actions, which are not tests (so they should break before we hit test logic)
            target_id = choose_action_target(engine.state, act, engine)
            engine.initiate_test(act, engine.state, target_id)
            decision = choose_commit(act, len(engine.state.ranger.hand), engine.state, engine) if act.is_test else None

            try:
                engine.perform_action(act, decision or __import__('src.models', fromlist=['CommitDecision']).CommitDecision([]), target_id)
            except RuntimeError as e:
                print(str(e))
                input("There was a runtime error! Press Enter to continue...")
                continue

            display_and_clear_messages(engine)

            # Check if day ended during action (e.g., fatigue from empty deck)
            if engine.day_has_ended:
                print("\nThe day has ended. Demo complete!")
                input("Press Enter to exit...")
                return

            input("Action performed. Press Enter to continue...")

        # Check if day ended during Phase 2
        if engine.day_has_ended:
            print("\nThe day has ended. Demo complete!")
            input("Press Enter to exit...")
            return

        # Phase 3: Travel (skipped)
        clear_screen()
        render_state(engine.state, phase_header=f"Round {engine.state.round_number} — Phase 3: Travel (skipped)")
        print("")
        print("--- Event log ---")
        display_and_clear_messages(engine)

        # Check if day ended during Phase 3
        if engine.day_has_ended:
            print("\nThe day has ended. Demo complete!")
            input("Press Enter to exit...")
            return

        input("Press Enter to proceed to Phase 4...")

        # Phase 4: Refresh
        clear_screen()
        engine.phase4_refresh()
        render_state(engine.state, phase_header=f"Round {engine.state.round_number} — Phase 4: Refresh")
        print("")
        print("--- Event log ---")
        display_and_clear_messages(engine)

        # Check if day ended during Phase 4 (e.g., drawing from empty deck)
        if engine.day_has_ended:
            print("\nThe day has ended. Demo complete!")
            input("Press Enter to exit...")
            return

        input("Press Enter to start next round...")

        engine.state.round_number += 1


def main() -> None:
    state = build_demo_state()
    engine = GameEngine(state, card_chooser=choose_target, response_decider=choose_response)
    # Reconstruct listeners from cards in hand
    engine.reconstruct_listeners()
    menu_and_run(engine)


if __name__ == "__main__":
    main()
