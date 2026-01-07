
import os
import random
import argparse
from pathlib import Path
from src.models import (
    Card, RangerState, GameState, Action, Aspect, Area, CardType,
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
from src.save_load import save_game, load_game
from src.cards import (
    OvergrownThicket, SunberryBramble, SitkaDoe, WalkWithMe, ADearFriend,
    ProwlingWolhund, SitkaBuck, CalypsaRangerMentor, PeerlessPathfinder,
    CausticMulcher, BoulderField, QuisiVosRascal, BoundarySensor, AffordedByNature,
    CradledbytheEarth, HyPimpotChef
)

# Default save directory
SAVE_DIR = Path("saves")


def pick_demo_cards() -> list[Card]:
    """Build a demo ranger deck using actual implemented cards."""
    # Top of deck - specific cards we want available early
    top_deck: list[Card] = [
        WalkWithMe(),
        ADearFriend(),
        BoundarySensor(),
        CradledbytheEarth(),
        AffordedByNature(),
    ]

    # Fill rest of deck with copies of Boundary Sensor (has Exploration icons)
    filler_cards: list[Card] = []
    for _ in range(20):
        filler_cards.append(BoundarySensor())

    random.shuffle(filler_cards)
    return top_deck + filler_cards


def clear_screen() -> None:
    # Basic clear that works on Windows terminals
    os.system("cls" if os.name == "nt" else "clear")


def show_title_screen() -> str:
    """
    Display the title screen and get user's choice.

    Returns:
        'new' - Start new campaign
        'load:<path>' - Load a saved game
        'quit' - Exit the game
    """
    while True:
        # Display title screen
        clear_screen()
        print("")
        print("=" * 50)
        print("        EARTHBORNE RANGERS")
        print("        Text-Based Adventure")
        print("=" * 50)
        print("")
        print("  1. New Campaign")
        print("  2. Load Saved Game")
        print("  3. Quit")
        print("")

        choice = input("> ").strip()

        if choice == "1":
            return 'new'

        elif choice == "2":
            # Load Game
            if not SAVE_DIR.exists():
                print("\nNo save directory found.")
                input("Press Enter to continue...")
                continue  # Re-display title

            saves = list(SAVE_DIR.glob("*.json"))
            if not saves:
                print("\nNo save files found.")
                input("Press Enter to continue...")
                continue  # Re-display title

            print("\nAvailable saves:")
            for i, save in enumerate(saves, 1):
                print(f" {i}. {save.name}")
            print(" 0. Back")

            try:
                idx = int(input("> ").strip())
                if idx == 0:
                    continue  # Back to title
                if 1 <= idx <= len(saves):
                    save_path = saves[idx - 1]
                    return f"load:{save_path}"
                else:
                    print("Invalid selection.")
            except ValueError:
                print("Invalid input.")

        elif choice == "3" or choice.lower() in ('q', 'quit'):
            return 'quit'

        else:
            print("Please enter 1, 2, or 3.")


def display_campaign_tracker(engine: GameEngine) -> None:
    """Display the campaign tracker information."""
    tracker = engine.state.campaign_tracker

    print("\n" + "=" * 50)
    print("           CAMPAIGN TRACKER")
    print("=" * 50)

    # Basic info
    print(f"\n  Day: {tracker.day_number}")
    print(f"  Location: {tracker.current_location_id}")
    print(f"  Terrain: {tracker.current_terrain_type}")

    # Ranger info
    print(f"\n  Ranger: {tracker.ranger_name}")

    # Active missions
    print("\n  Active Missions:")
    if tracker.active_missions:
        for mission in tracker.active_missions:
            bubbles = []
            if mission.left_bubble:
                bubbles.append("L")
            if mission.middle_bubble:
                bubbles.append("M")
            if mission.right_bubble:
                bubbles.append("R")
            bubble_str = f" [{'/'.join(bubbles)}]" if bubbles else ""
            print(f"    - {mission.name}{bubble_str}")
    else:
        print("    (none)")

    # Cleared missions
    print("\n  Cleared Missions:")
    if tracker.cleared_missions:
        for mission in tracker.cleared_missions:
            print(f"    - {mission.name}")
    else:
        print("    (none)")

    # Notable events
    print("\n  Notable Events:")
    if tracker.notable_events:
        for event in tracker.notable_events:
            print(f"    - {event}")
    else:
        print("    (none)")

    # Unlocked rewards
    print("\n  Unlocked Rewards:")
    if tracker.unlocked_rewards:
        for reward in tracker.unlocked_rewards:
            print(f"    - {reward}")
    else:
        print("    (none)")

    print("\n" + "=" * 50)
    input("Press Enter to continue...")


def handle_menu(engine: GameEngine) -> str:
    """
    Display the in-game menu and handle save/load/quit options.

    Returns:
        'continue' - Return to game
        'load' - A game was loaded (engine reference is stale)
        'quit' - Return to title screen
    """
    while True:
        print("\n===== MENU =====")
        print(" 1. Save Game")
        print(" 2. Load Game")
        print(" 3. Campaign Tracker")
        print(" 4. Return to Title")
        print(" 5. Back to Game")

        choice = input("> ").strip()

        if choice == "1":
            # Save Game
            SAVE_DIR.mkdir(parents=True, exist_ok=True)

            # Generate default filename
            day = engine.state.campaign_tracker.day_number
            round_num = engine.state.round_number
            default_name = f"day{day}_round{round_num}.json"

            print(f"\nEnter save name (default: {default_name}):")
            save_name = input("> ").strip()
            if not save_name:
                save_name = default_name
            if not save_name.endswith(".json"):
                save_name += ".json"

            save_path = SAVE_DIR / save_name
            try:
                save_game(engine, save_path)
                print(f"\nGame saved to: {save_path}")
                input("Press Enter to continue...")
            except Exception as e:
                print(f"\nError saving game: {e}")
                input("Press Enter to continue...")

        elif choice == "2":
            # Load Game
            if not SAVE_DIR.exists():
                print("\nNo save directory found.")
                input("Press Enter to continue...")
                continue

            saves = list(SAVE_DIR.glob("*.json"))
            if not saves:
                print("\nNo save files found.")
                input("Press Enter to continue...")
                continue

            print("\nAvailable saves:")
            for i, save in enumerate(saves, 1):
                print(f" {i}. {save.name}")
            print(" 0. Cancel")

            try:
                idx = int(input("> ").strip())
                if idx == 0:
                    continue
                if 1 <= idx <= len(saves):
                    save_path = saves[idx - 1]
                    print(f"\nLoading {save_path.name}...")
                    # Return 'load' to signal caller should load and restart
                    return f"load:{save_path}"
                else:
                    print("Invalid selection.")
            except ValueError:
                print("Invalid input.")

        elif choice == "3":
            # Campaign Tracker
            display_campaign_tracker(engine)

        elif choice == "4":
            # Return to Title
            confirm = input("\nReturn to title? Unsaved progress will be lost. (y/n): ").strip().lower()
            if confirm in ('y', 'yes'):
                return 'quit'

        elif choice == "5" or choice == "":
            # Back to Game
            return 'continue'

        else:
            print("Invalid choice.")





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


def _build_phase2_actions(engine: GameEngine) -> list[Action]:
    """Build the list of available actions during Phase 2."""
    all_tests = provide_card_tests(engine) + provide_common_tests(engine.state)
    filtered_tests = filter_tests_by_targets(all_tests, engine.state)
    actions = (filtered_tests
        + provide_exhaust_abilities(engine.state)
        + provide_play_options(engine))  # Filters by can_be_played()

    # Add system actions
    actions.append(Action(
        id="system-discard-gear",
        name="[Discard Gear]",
        verb="Discard Gear",
        aspect="",
        approach="",
        is_test=False,
        on_success=lambda s, _e, _t: None,
    ))
    actions.append(Action(
        id="system-rest",
        name="[Rest] (end actions)",
        verb="Rest",
        aspect="",
        approach="",
        is_test=False,
        on_success=lambda s, _e, _t: None,
    ))
    actions.append(Action(
        id="system-end-day",
        name="[End Day]",
        verb="END DAY",
        aspect="",
        approach="",
        is_test=False,
        on_success=lambda s, _e, _t: None,
    ))
    actions.append(Action(
        id="system-menu",
        name="[Menu] (save/load/quit)",
        verb="Menu",
        aspect="",
        approach="",
        is_test=False,
        on_success=lambda s, _e, _t: None,
    ))

    return actions


def _handle_phase2_action(engine: GameEngine, act: Action, with_ui: bool) -> str | None:
    """
    Handle a Phase 2 action. Returns a result string if the game loop should exit,
    or None to continue the action loop.
    """
    if act.id == "system-discard-gear":
        gear_in_play = [c for c in engine.state.areas[Area.PLAYER_AREA] if c.has_type(CardType.GEAR)]
        if not gear_in_play:
            engine.add_message("No gear in play to discard.")
            return None

        to_discard = engine.card_chooser(engine, gear_in_play)
        to_discard.discard_from_play(engine)
        engine.add_message(f"Discarded {to_discard.title}.")
        if with_ui:
            display_and_clear_messages(engine)
            input("Press Enter to continue...")
        return None

    if act.id == "system-rest":
        engine.resolve_fatiguing_keyword()
        if with_ui:
            display_and_clear_messages(engine)
            print("\nYou rest and end your turn.")
            input("Press Enter to proceed to Phase 3...")
        return 'rest'  # Signal to break out of Phase 2 loop

    # Handle test or play/exhaust actions
    target_id = choose_action_target(engine.state, act, engine)
    if act.is_test:
        engine.initiate_test(act, engine.state, target_id)
        decision = choose_commit(act, len(engine.state.ranger.hand), engine.state, engine)
        try:
            engine.perform_test(act, decision or __import__('src.models', fromlist=['CommitDecision']).CommitDecision([]), target_id)
        except RuntimeError as e:
            if with_ui:
                print(str(e))
                input("There was a runtime error! Press Enter to continue...")
            return None
    elif act.is_exhaust or act.is_play:
        target_card = engine.state.get_card_by_id(target_id)
        act.on_success(engine, 0, target_card)
    else:
        raise RuntimeError(f"Unknown action type: {act.id}")

    engine.check_and_process_clears()
    if with_ui:
        display_and_clear_messages(engine)

    if engine.day_has_ended:
        if with_ui:
            print("\nThe day has ended. Demo complete!")
            input("Press Enter to exit...")
        return 'normal'

    if with_ui:
        input("Action performed. Press Enter to continue...")

    return None


def run_game_loop(engine: GameEngine, with_ui: bool = True, resume_phase2: bool = False) -> str:
    """
    Core game loop that can run with or without UI.

    Args:
        engine: The game engine to run
        with_ui: If True, displays UI and waits for input. If False, runs autonomously using engine's decision functions.
        resume_phase2: If True, skip intro and Phase 1, resume directly into Phase 2 (for loaded saves)

    Returns:
        'normal' - Day ended normally
        'quit' - User chose to quit to title
        'load:<path>' - User chose to load a save file
    """
    # Track whether to skip Phase 1 on first iteration (for loaded saves)
    skip_phase1 = resume_phase2

    if resume_phase2:
        # Show loaded game header
        if with_ui:
            clear_screen()
            print(f"=== Loaded: Day {engine.state.campaign_tracker.day_number}, Round {engine.state.round_number} ===")
            render_state(engine, phase_header=f"Round {engine.state.round_number} — Phase 2: Ranger Turns (Resumed)")
            print("")
            input("Press Enter to continue...")
    else:
        # Show welcome for new games
        if with_ui:
            print("====== Earthborne Rangers - DAY 1 ======")
            display_and_clear_messages(engine)
            print("Press enter to continue to Phase 1...")
            input()

    while True:
        # Phase 1: Draw path cards (skip on first iteration if resuming)
        if not skip_phase1:
            if with_ui:
                clear_screen()
            engine.phase1_draw_paths(count=1)
            if with_ui:
                render_state(engine, phase_header=f"Day {engine.state.campaign_tracker.day_number} — Round {engine.state.round_number} — Phase 1: Draw Path Cards")
                print("")
                print("==== Event log ====")
                display_and_clear_messages(engine)
                input("Press Enter to proceed to Phase 2...")

        skip_phase1 = False  # Only skip once

        # Phase 2: Actions until Rest
        while True:
            if with_ui:
                clear_screen()
                render_state(engine, phase_header=f"Day {engine.state.campaign_tracker.day_number} — Round {engine.state.round_number} — Phase 2: Ranger Turns")
                print("")
                print("==== Event log and choices ====")

            actions = _build_phase2_actions(engine)

            # Keep prompting until we get a valid action
            act = None
            while not act:
                if with_ui:
                    act = choose_action(actions, engine.state, engine)
                else:
                    act = engine.card_chooser(engine, actions) if actions else None

                if act is not None and act.id == "system-end-day":
                    yes = engine.response_decider(engine, "Are you sure?")
                    if yes:
                        engine.end_day(False)
                        if with_ui:
                            display_and_clear_messages(engine)
                            input("Press Enter to exit...")
                        return 'normal'
                    else:
                        act = None

                if act is not None and act.id == "system-menu":
                    if with_ui:
                        menu_result = handle_menu(engine)
                        if menu_result == 'quit':
                            return 'quit'
                        elif menu_result.startswith('load:'):
                            return menu_result
                    act = None
                    continue

            # Handle the selected action
            result = _handle_phase2_action(engine, act, with_ui)
            if result == 'rest':
                break  # Exit Phase 2 loop
            elif result == 'normal':
                return 'normal'
            # result is None means continue action loop

        # Check if day ended during Phase 2
        if engine.day_has_ended:
            if with_ui:
                print("\nThe day has ended. Demo complete!")
                input("Press Enter to exit...")
            return 'normal'

        # Phase 3: Travel
        if with_ui:
            clear_screen()
            render_state(engine, phase_header=f"Day {engine.state.campaign_tracker.day_number} — Round {engine.state.round_number} — Phase 3: Travel")
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
            return 'normal'

        if with_ui:
            input("Press Enter to proceed to Phase 4...")

        # Phase 4: Refresh
        if with_ui:
            clear_screen()
        engine.phase4_refresh()
        if with_ui:
            render_state(engine, phase_header=f"Day {engine.state.campaign_tracker.day_number} — Round {engine.state.round_number} — Phase 4: Refresh")
            print("")
            print("==== Event log ====")
            display_and_clear_messages(engine)

        # Check if day ended during Phase 4 (e.g., drawing from empty deck)
        if engine.day_has_ended:
            if with_ui:
                print("\nThe day has ended. Demo complete!")
                input("Press Enter to exit...")
            return 'normal'

        if with_ui:
            input("Press Enter to start next round...")

        engine.state.round_number += 1


def menu_and_run(engine: GameEngine, resume_phase2: bool = False) -> str:
    """Interactive UI wrapper around the game loop.

    Args:
        engine: The game engine to run
        resume_phase2: If True, skip intro and Phase 1, resume directly into Phase 2 (for loaded saves)

    Returns:
        'normal' - Day ended normally
        'quit' - User chose to quit to title
        'load:<path>' - User chose to load a save file
    """
    return run_game_loop(engine, with_ui=True, resume_phase2=resume_phase2)


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
    if campaign_tracker.day_number == 1:
        engine.campaign_guide.resolve_entry_1(None, engine, None)
    else:
        engine.add_message(f"Step 1: Set up player area (skipped)")
        engine.add_message(f"Step 2: Draw starting hand")

        # Draw starting hand
        for _ in range(5):
            card, _ = state.ranger.draw_card(engine)
            if card is None:
                raise RuntimeError(f"Deck should not run out during setup!")
        #TODO: implement mulligan

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
    parser.add_argument(
        "--load",
        type=str,
        help="Load a saved game file directly (skip title screen)"
    )
    args = parser.parse_args()

    # Configure display options
    set_show_art_descriptions(args.show_art)

    # Check for command-line load argument
    load_path = args.load

    # Main game loop
    while True:
        # If no load path specified, show title screen
        if not load_path:
            title_choice = show_title_screen()

            if title_choice == 'quit':
                print("\nThanks for playing!")
                return
            elif title_choice == 'new':
                load_path = None  # Will start new campaign below
            elif title_choice.startswith('load:'):
                load_path = title_choice[5:]
            else:
                continue  # Unknown choice, show title again

        engine = None

        if load_path:
            # Load from save file
            try:
                print(f"Loading save: {load_path}")
                engine = load_game(load_path)
                # Set up UI decision functions
                engine.card_chooser = choose_target
                engine.response_decider = choose_response
                engine.order_decider = choose_order
                engine.option_chooser = choose_option
                engine.amount_chooser = choose_amount
                print("Game loaded successfully!")
                load_path = None  # Clear so we don't reload on next iteration
            except Exception as e:
                print(f"Error loading save: {e}")
                input("Press Enter to return to title...")
                load_path = None
                continue  # Back to title screen

        if engine is None:
            # Start a new campaign
            from src.models import CampaignTracker, Mission
            campaign_tracker = CampaignTracker(
                day_number=1,
                ranger_name="Demo Ranger",
                ranger_aspects={Aspect.AWA: 99, Aspect.FIT: 99, Aspect.SPI: 99, Aspect.FOC: 99},
                current_location_id="Lone Tree Station",
                current_terrain_type="Woods",
                active_missions=[]
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
                    result = menu_and_run(engine)
                    if result == 'quit':
                        # Return to title screen
                        load_path = None
                        break
                    elif result.startswith('load:'):
                        load_path = result[5:]
                        break
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
                        return
            else:
                # Loop completed without break - all days done
                return

            # Continue to next iteration (title screen or load)
            continue

        else:
            # Running from a loaded save - resume directly into Phase 2
            try:
                result = menu_and_run(engine, resume_phase2=True)
                if result == 'quit':
                    # Return to title screen
                    load_path = None
                    continue
                elif result.startswith('load:'):
                    load_path = result[5:]
                    continue
            except DayEndException:
                print("\n" + "="*50)
                display_and_clear_messages(engine)
                print("="*50)
                print(f"\nDay complete!")
                input("Press Enter to continue...")
                load_path = None  # Return to title
                continue


if __name__ == "__main__":
    main()
