
import os
from src.models import Card, RangerState, GameState, Action, Aspect, Approach, Zone, CardType
from src.engine import GameEngine
from src.registry import provide_common_tests, provide_card_tests
from src.view import render_state, choose_action, choose_action_target, choose_commit, choose_target, display_and_clear_messages, initiate_test, choose_response
from src.decks import build_woods_path_deck
from src.cards import OvergrownThicket, SunberryBramble, SitkaDoe, WalkWithMe, ADearFriend, ProwlingWolhund, SitkaBuck


def pick_demo_cards() -> list[Card]:


    walk_with_me_0 = WalkWithMe()
    a_dear_friend_0 = ADearFriend()
    exploration_dummy = Card(id="demo-explore-1", title="Demo Explore +1", approach_icons={Approach.EXPLORATION: 1})
    reason_dummy = Card(id="demo-reason-1", title="Demo Reason +1", approach_icons={Approach.REASON: 1})
    conflict_dummy = Card(id="demo-conflict-1", title="Demo Conflict +1", approach_icons={Approach.CONFLICT: 1})

    return [walk_with_me_0, a_dear_friend_0, exploration_dummy, reason_dummy, conflict_dummy]


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

    ranger = RangerState(name="Demo Ranger", hand=[], energy={Aspect.AWA: 99, Aspect.FIT: 99, Aspect.SPI: 99, Aspect.FOC: 99}, deck=ranger_deck)
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
        state.ranger.draw_card()
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
            act = choose_action(actions, engine.state, engine)
            if not act:
                # treat as cancel to end the run
                return

            if act.id == "system-rest":
                print("\nYou rest and end your turn.")
                input("Press Enter to proceed to Phase 3...")
                break

            target_id = choose_action_target(engine.state, act, engine)
            initiate_test(act, engine.state, target_id)
            decision = choose_commit(act, len(engine.state.ranger.hand), engine.state, engine) if act.is_test else None

            try:
                engine.perform_action(act, decision or __import__('src.models', fromlist=['CommitDecision']).CommitDecision([]), target_id)
            except RuntimeError as e:
                print(str(e))
                input("There was a runtime error! Press Enter to continue...")
                continue

            display_and_clear_messages(engine)
            input("Action performed. Press Enter to continue...")

        # Phase 3: Travel (skipped)
        clear_screen()
        render_state(engine.state, phase_header=f"Round {engine.state.round_number} — Phase 3: Travel (skipped)")
        input("Press Enter to proceed to Phase 4...")

        # Phase 4: Refresh
        clear_screen()
        engine.phase4_refresh()
        render_state(engine.state, phase_header=f"Round {engine.state.round_number} — Phase 4: Refresh")
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
