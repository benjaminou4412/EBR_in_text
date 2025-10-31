
import os
import random
import argparse
from src.models import (
    Card, RangerState, GameState, Action, Aspect, Approach, Area, CardType
)
from src.engine import GameEngine
from src.registry import provide_common_tests, provide_card_tests, provide_exhaust_abilities
from src.view import (
    render_state, choose_action, choose_action_target, choose_commit,
    choose_target, display_and_clear_messages, choose_response, set_show_art_descriptions,
    choose_order
)
from src.decks import build_woods_path_deck
from src.cards import (
    OvergrownThicket, SunberryBramble, SitkaDoe, WalkWithMe, ADearFriend,
    ProwlingWolhund, SitkaBuck, CalypsaRangerMentor, PeerlessPathfinder,
    CausticMulcher, BoulderField
)


def pick_demo_cards() -> list[Card]:


    walk_with_me_0 : Card = WalkWithMe()
    a_dear_friend_0 : Card= ADearFriend()
    exploration_dummies : list[Card] = []
    for _ in range(2):
        exploration_dummies.append(Card(title="Demo Explore +1", approach_icons={Approach.EXPLORATION: 1}))
    conflict_dummies : list[Card]  = []
    for _ in range(2):
        conflict_dummies.append(Card(title="Demo Conflict +1", approach_icons={Approach.CONFLICT: 1}))
    reason_dummies : list[Card]  = []
    for _ in range(2):
        reason_dummies.append(Card(title="Demo Reason +1", approach_icons={Approach.REASON: 1}))
    connection_dummies : list[Card]  = []
    for _ in range(2):
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
    ranger_fatigue = pick_demo_cards()[0:5]

    #add Boulder Field
    location = BoulderField()

    # Add Midday Sun (Weather)
    weather = Card(
        id="midday-sun-01",
        title="Midday Sun",
        card_types={CardType.WEATHER},
        starting_area=Area.SURROUNDINGS,
    )
    #Add Caustic Mulcher
    mulcher = CausticMulcher()
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

    # Add Calypsa
    calypsa = CalypsaRangerMentor()

    

    role_card = PeerlessPathfinder()

    ranger = RangerState(name="Demo Ranger", hand=[], aspects={Aspect.AWA: 99, Aspect.FIT: 99, Aspect.SPI: 99, Aspect.FOC: 99}, deck=ranger_deck, fatigue_stack=ranger_fatigue)
    # Build a simple path deck from woods, excluding the ones already in play
    deck = build_woods_path_deck()
    surroundings : list[Card] = [weather, location]
    along_the_way : list[Card] = [wol_0, buck_0, bramble, mulcher]
    within_reach : list[Card] = [thicket, calypsa, doe]
    player_area : list[Card] = [role_card]
    current_areas : dict[Area,list[Card]]= {Area.SURROUNDINGS : surroundings, Area.ALONG_THE_WAY : along_the_way, Area.WITHIN_REACH : within_reach, Area.PLAYER_AREA : player_area}
    state = GameState(ranger=ranger, role_card=role_card, location=location, areas=current_areas, round_number=1, path_deck=deck)
    # Note: Cards drawn to hand - listeners will be registered when engine is created
    for _ in range(5):
        _, _, _ = state.ranger.draw_card()  # Draw cards during setup
        # Note: enters_hand() will be called during reconstruct_listeners()
    return state


def menu_and_run(engine: GameEngine) -> None:
    # Print welcome header once
    print("=== Earthborne Rangers - Demo ===")
    print("Welcome to the demo! Press Enter to begin...")
    input()
    display_and_clear_messages(engine)
    print("Press enter to continue to Phase 1...")
    input()

    while True:
        # Phase 1: Draw path cards
        clear_screen()
        engine.phase1_draw_paths(count=1)
        render_state(engine, phase_header=f"Round {engine.state.round_number} — Phase 1: Draw Path Cards")
        print("")
        print("--- Event log ---")
        display_and_clear_messages(engine)
        input("Press Enter to proceed to Phase 2...")

        # Phase 2: Actions until Rest
        while True:
            clear_screen()
            render_state(engine, phase_header=f"Round {engine.state.round_number} — Phase 2: Ranger Turns")

            print("")

            print("--- Event log and choices ---")

            # derive actions
            actions = (provide_card_tests(engine)
            + provide_common_tests(engine.state)
            + provide_exhaust_abilities(engine.state))
            # add system Rest action
            actions.append(Action(
                id="system-rest",
                name="[Rest] (end actions)",
                verb="Rest",
                aspect="",
                approach="",
                is_test=False,
                on_success=lambda s, _e, _t: None,
            ))
            # add system End Day action
            actions.append(Action(
                id="system-end-day",
                name="END DAY",
                verb="END DAY",
                aspect="",
                approach="",
                is_test=False,
                on_success=lambda s, _e, _t: None,
            ))

            # Keep prompting until we get a valid action
            act = None
            while not act:
                act = choose_action(actions, engine.state, engine)
                if act is not None and act.id == "system-end-day":
                    yes = engine.response_decider(engine, "Are you sure?")
                    if yes:
                        engine.end_day()
                        display_and_clear_messages(engine)
                        print("\nThe day has ended. Demo complete!")
                        input("Press Enter to exit...")
                        return
                    else:
                        act = None

            if act.id == "system-rest":
                engine.resolve_fatiguing_keyword()
                print("\nYou rest and end your turn.")
                input("Press Enter to proceed to Phase 3...")
                break

            
            #TODO: Handle Exhaust actions and Play actions, which are not tests (so they should break before we hit test logic)
            target_id = choose_action_target(engine.state, act, engine)
            decision = None
            if act.is_test:
                engine.initiate_test(act, engine.state, target_id)
                decision = choose_commit(act, len(engine.state.ranger.hand), engine.state, engine) if act.is_test else None
                try:
                    engine.perform_test(act, decision or __import__('src.models', fromlist=['CommitDecision']).CommitDecision([]), target_id)
                except RuntimeError as e:
                    print(str(e))
                    input("There was a runtime error! Press Enter to continue...")
                    continue
            elif act.is_exhaust: #currently only non-test action at this point is Exhaust abilities
                target_card = engine.state.get_card_by_id(target_id)
                act.on_success(engine, 0, target_card)
            else:
                raise RuntimeError(f"Unknown action type: {act.id}")

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

        # Phase 3: Travel
        clear_screen()
        render_state(engine, phase_header=f"Round {engine.state.round_number} — Phase 3: Travel")
        print("")
        print("--- Event log ---")
        camped = engine.phase3_travel()
        display_and_clear_messages(engine)

        # Check if day ended during Phase 3
        if engine.day_has_ended:
            if camped:
                print("\nThe day has ended by camping. Demo complete!")
                input("Press Enter to exit...")
                return
            else:
                print("\nThe day has ended without camping. Demo complete!")
                input("Press Enter to exit...")
                return

        input("Press Enter to proceed to Phase 4...")

        # Phase 4: Refresh
        clear_screen()
        engine.phase4_refresh()
        render_state(engine, phase_header=f"Round {engine.state.round_number} — Phase 4: Refresh")
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
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Earthborne Rangers text-based game demo")
    parser.add_argument(
        "--show-art",
        action="store_true",
        help="Display card art descriptions during gameplay"
    )
    args = parser.parse_args()

    # Configure display options
    set_show_art_descriptions(args.show_art)

    #state = build_demo_state()
    ranger_deck = pick_demo_cards()
    ranger_fatigue = pick_demo_cards()[0:5]
    ranger = RangerState(name="Demo Ranger", hand=[], aspects={Aspect.AWA: 99, Aspect.FIT: 99, Aspect.SPI: 99, Aspect.FOC: 99}, deck=ranger_deck, fatigue_stack=ranger_fatigue)
    role_card = PeerlessPathfinder()
    state = GameState(ranger=ranger, role_card=role_card)
    engine = GameEngine(state, card_chooser=choose_target, response_decider=choose_response, order_decider=choose_order)
    engine.add_message(f"===BEGIN SETUP===")
    engine.add_message(f"Step 1: Set up player area (skipped)")
    #TODO: simulate ranger setup
    engine.add_message(f"Step 2: Draw starting hand")
    for _ in range(5):
        card, msg, _ = state.ranger.draw_card()  # Draw cards during setup
        if card is not None:
            engine.add_message(msg)
            card.enters_hand(engine)
        else:
            raise RuntimeError(f"Deck should not run out during setup!")
    
    engine.add_message(f"Step 3: Elect lead Ranger (skipped)")
    engine.add_message(f"Step 4: Shuffle challenge deck (skipped)")
    #TODO: trigger stuff that cares about challenge deck being shuffled
    #or well, whatever method eventually gets called here should trigger that

    engine.arrival_setup(start_of_day=True)
    menu_and_run(engine)


if __name__ == "__main__":
    main()
