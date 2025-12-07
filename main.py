
import os
import random
import argparse
from src.models import (
    Card, RangerState, GameState, Action, Aspect, Approach, Area, CardType,
    DayEndException
)
from src.engine import GameEngine
from src.registry import provide_common_tests, provide_card_tests, provide_exhaust_abilities, provide_play_options, filter_tests_by_targets
from src.view import (
    render_state, choose_action, choose_action_target, choose_commit,
    choose_target, display_and_clear_messages, choose_response, set_show_art_descriptions,
    choose_order, choose_option, choose_amount
)
from src.decks import build_woods_path_deck
from src.cards import (
    OvergrownThicket, SunberryBramble, SitkaDoe, WalkWithMe, ADearFriend,
    ProwlingWolhund, SitkaBuck, CalypsaRangerMentor, PeerlessPathfinder,
    CausticMulcher, BoulderField, QuisiVosRascal, BoundarySensor, AffordedByNature,
    CradledbytheEarth, HyPimpotChef
)


def pick_demo_cards() -> list[Card]:


    walk_with_me_0 : Card = WalkWithMe()
    a_dear_friend_0 : Card= ADearFriend()
    boundary_sensor_0: Card = BoundarySensor()
    cradled_by_earth_0: Card = CradledbytheEarth()
    afforded_by_nature_0: Card = AffordedByNature()
    exploration_dummies : list[Card] = []
    for _ in range(5):
        exploration_dummies.append(Card(title="Demo Explore +1", card_types={CardType.ATTRIBUTE}, approach_icons={Approach.EXPLORATION: 1}))
    conflict_dummies : list[Card]  = []
    for _ in range(5):
        conflict_dummies.append(Card(title="Demo Conflict +1", card_types={CardType.ATTRIBUTE}, approach_icons={Approach.CONFLICT: 1}))
    reason_dummies : list[Card]  = []
    for _ in range(5):
        reason_dummies.append(Card(title="Demo Reason +1", card_types={CardType.ATTRIBUTE}, approach_icons={Approach.REASON: 1}))
    connection_dummies : list[Card]  = []
    for _ in range(5):
        connection_dummies.append(Card(title="Demo Connection +1", card_types={CardType.ATTRIBUTE}, approach_icons={Approach.CONNECTION: 1}))

    deck = exploration_dummies + conflict_dummies + reason_dummies + connection_dummies
    random.shuffle(deck)
    top_deck: list[Card] = [walk_with_me_0, a_dear_friend_0, boundary_sensor_0, afforded_by_nature_0, cradled_by_earth_0]

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
    return state


def run_game_loop(engine: GameEngine, with_ui: bool = True) -> None:
    """
    Core game loop that can run with or without UI.

    Args:
        engine: The game engine to run
        with_ui: If True, displays UI and waits for input. If False, runs autonomously using engine's decision functions.
    """
    if with_ui:
        # Print welcome header once
        print("====== Earthborne Rangers - Demo ======")
        print("Welcome to the demo! Press Enter to begin...")
        input()
        display_and_clear_messages(engine)
        print("Press enter to continue to Phase 1...")
        input()

    while True:
        # Phase 1: Draw path cards
        if with_ui:
            clear_screen()
        engine.phase1_draw_paths(count=1)
        if with_ui:
            render_state(engine, phase_header=f"Round {engine.state.round_number} — Phase 1: Draw Path Cards")
            print("")
            print("==== Event log ====")
            display_and_clear_messages(engine)
            input("Press Enter to proceed to Phase 2...")

        # Phase 2: Actions until Rest
        while True:
            if with_ui:
                clear_screen()
                render_state(engine, phase_header=f"Round {engine.state.round_number} — Phase 2: Ranger Turns")
                print("")
                print("==== Event log and choices ====")

            # derive actions
            all_tests = provide_card_tests(engine) + provide_common_tests(engine.state)
            filtered_tests = filter_tests_by_targets(all_tests, engine.state)
            actions = (filtered_tests
            + provide_exhaust_abilities(engine.state)
            + provide_play_options(engine))  # Filters by can_be_played()

            # add system Discard Gear action
            actions.append(Action(
                id="system-discard-gear",
                name="[Discard Gear]",
                verb="Discard Gear",
                aspect="",
                approach="",
                is_test=False,
                on_success=lambda s, _e, _t: None,
            ))
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
                if with_ui:
                    act = choose_action(actions, engine.state, engine)
                else:
                    # In non-UI mode, use engine's decision functions
                    act = engine.card_chooser(engine, actions) if actions else None

                if act is not None and act.id == "system-end-day":
                    yes = engine.response_decider(engine, "Are you sure?")
                    if yes:
                        engine.end_day()
                        if with_ui:
                            display_and_clear_messages(engine)
                            print("\nThe day has ended. Demo complete!")
                            input("Press Enter to exit...")
                        return
                    else:
                        act = None

            if act.id == "system-discard-gear":
                # Get all gear in Player Area
                gear_in_play = [c for c in engine.state.areas[Area.PLAYER_AREA] if c.has_type(CardType.GEAR)]
                if not gear_in_play:
                    engine.add_message("No gear in play to discard.")
                    act = None
                    continue

                # Prompt to choose gear
                to_discard = engine.card_chooser(engine, gear_in_play)
                to_discard.discard_from_play(engine)
                engine.add_message(f"Discarded {to_discard.title}.")
                if with_ui:
                    display_and_clear_messages(engine)
                    input("Press Enter to continue...")
                act = None
                continue

            if act.id == "system-rest":
                engine.resolve_fatiguing_keyword()
                if with_ui:
                    display_and_clear_messages(engine)
                    print("\nYou rest and end your turn.")
                    input("Press Enter to proceed to Phase 3...")
                break



            target_id = choose_action_target(engine.state, act, engine)
            decision = None
            if act.is_test:
                engine.initiate_test(act, engine.state, target_id)
                decision = choose_commit(act, len(engine.state.ranger.hand), engine.state, engine) if act.is_test else None
                try:
                    engine.perform_test(act, decision or __import__('src.models', fromlist=['CommitDecision']).CommitDecision([]), target_id)
                except RuntimeError as e:
                    if with_ui:
                        print(str(e))
                        input("There was a runtime error! Press Enter to continue...")
                    continue
            elif act.is_exhaust or act.is_play:
                target_card = engine.state.get_card_by_id(target_id)
                act.on_success(engine, 0, target_card)
            else:
                raise RuntimeError(f"Unknown action type: {act.id}")

            engine.check_and_process_clears()
            if with_ui:
                display_and_clear_messages(engine)

            # Check if day ended during action (e.g., fatigue from empty deck)
            if engine.day_has_ended:
                if with_ui:
                    print("\nThe day has ended. Demo complete!")
                    input("Press Enter to exit...")
                return

            if with_ui:
                input("Action performed. Press Enter to continue...")

        # Check if day ended during Phase 2
        if engine.day_has_ended:
            if with_ui:
                print("\nThe day has ended. Demo complete!")
                input("Press Enter to exit...")
            return

        # Phase 3: Travel
        if with_ui:
            clear_screen()
            render_state(engine, phase_header=f"Round {engine.state.round_number} — Phase 3: Travel")
            print("")
            print("==== Event log ====")
        camped = engine.phase3_travel()
        if with_ui:
            display_and_clear_messages(engine)

        # Check if day ended during Phase 3
        if engine.day_has_ended:
            if with_ui:
                if camped:
                    print("\nThe day has ended by camping. Demo complete!")
                    input("Press Enter to exit...")
                else:
                    print("\nThe day has ended without camping. Demo complete!")
                    input("Press Enter to exit...")
            return

        if with_ui:
            input("Press Enter to proceed to Phase 4...")

        # Phase 4: Refresh
        if with_ui:
            clear_screen()
        engine.phase4_refresh()
        if with_ui:
            render_state(engine, phase_header=f"Round {engine.state.round_number} — Phase 4: Refresh")
            print("")
            print("==== Event log ====")
            display_and_clear_messages(engine)

        # Check if day ended during Phase 4 (e.g., drawing from empty deck)
        if engine.day_has_ended:
            if with_ui:
                print("\nThe day has ended. Demo complete!")
                input("Press Enter to exit...")
            return

        if with_ui:
            input("Press Enter to start next round...")

        engine.state.round_number += 1


def menu_and_run(engine: GameEngine) -> None:
    """Interactive UI wrapper around the game loop."""
    run_game_loop(engine, with_ui=True)


def start_new_day(campaign_tracker, role_card: Card) -> GameEngine:
    """
    Start a new day by creating a fresh GameState and GameEngine.

    Args:
        campaign_tracker: The campaign tracker with persistent state
        role_card: The ranger's role card

    Returns:
        A new GameEngine ready for the new day
    """
    # Create fresh game state for new day
    state = GameEngine.setup_new_day(campaign_tracker, role_card)

    # Build ranger deck (for now, use demo cards)
    state.ranger.deck = pick_demo_cards()

    # Create engine with decision functions
    engine = GameEngine(
        state,
        card_chooser=choose_target,
        response_decider=choose_response,
        order_decider=choose_order,
        option_chooser=choose_option,
        amount_chooser=choose_amount
    )

    # Perform day setup
    engine.add_message(f"=== DAY {campaign_tracker.day_number} BEGIN ===")
    engine.add_message(f"Step 1: Set up player area (skipped)")
    engine.add_message(f"Step 2: Draw starting hand")

    # Draw starting hand
    for _ in range(5):
        card, _ = state.ranger.draw_card(engine)
        if card is None:
            raise RuntimeError(f"Deck should not run out during setup!")

    engine.add_message(f"Step 3: Elect lead Ranger (only one ranger; automatically chosen)")
    engine.add_message(f"Step 4: Shuffle challenge deck")
    engine.state.challenge_deck.reshuffle()

    # Arrival setup
    engine.arrival_setup(start_of_day=True)

    return engine


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

    # Initialize campaign tracker for a new campaign
    from src.models import CampaignTracker
    campaign_tracker = CampaignTracker(
        day_number=1,
        ranger_name="Demo Ranger",
        ranger_aspects={Aspect.AWA: 99, Aspect.FIT: 99, Aspect.SPI: 99, Aspect.FOC: 99},
        current_location_id="Ancestor's Grove",
        current_terrain_type="Woods"
    )

    # Role card stays the same throughout campaign
    role_card = PeerlessPathfinder()

    # Day transition loop
    max_days = 30  # Limit for demo purposes
    for day in range(max_days):
        print(f"\n{'='*60}")
        print(f"Starting Day {campaign_tracker.day_number}")
        print(f"{'='*60}\n")

        # Start new day
        engine = start_new_day(campaign_tracker, role_card)

        # Force a demo card on top for testing
        engine.state.path_deck.insert(0, HyPimpotChef())

        # Run the day
        try:
            menu_and_run(engine)
        except DayEndException:
            # Day ended successfully
            print("\n" + "="*50)
            display_and_clear_messages(engine)
            print("="*50)
            print(f"\nDay {campaign_tracker.day_number - 1} complete!")

            # Check if we should continue to next day
            if day < max_days - 1:
                print(f"\nPress Enter to start Day {campaign_tracker.day_number}...")
                input()
            else:
                print(f"\nDemo complete after {max_days} days!")
                print("Thanks for playing!")
                break


if __name__ == "__main__":
    main()
