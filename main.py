import json
import os
from typing import Any
from src.models import Card, ApproachIcons, Entity, RangerState, GameState, Action
from src.engine import GameEngine
from src.registry import provide_common_tests, provide_card_tests
from src.view import render_state, choose_action, choose_target, choose_commit
from src.decks import build_woods_path_deck


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def to_card(raw: dict[str, Any]) -> Card: 
    approach_counts: dict[str, int] = {}
    for a in raw.get("approach_icons", []) or []: # type: ignore
        approach = a.get("approach") # type: ignore
        count = a.get("count", 0) # type: ignore
        if approach:
            approach_counts[approach] = approach_counts.get(approach, 0) + int(count) # type: ignore

    rules_texts: list[str] = []
    for r in raw.get("rules", []) or []: # type: ignore
        txt = r.get("text") # type: ignore
        if txt:
            rules_texts.append(txt) # type: ignore

    return Card(
        id=raw.get("id", ""),
        title=raw.get("title", "Untitled"),
        card_type=raw.get("card_type", ""),
        rules_texts=rules_texts,
        approach=ApproachIcons(approach_counts),
    )


def pick_demo_cards(base_dir: str) -> tuple[Entity, list[Card]]:
    # Load Overgrown Thicket feature
    woods = load_json(os.path.join(base_dir, "reference JSON", "Path Sets", "Terrain sets", "woods.json"))
    overgrown_raw = next(x for x in woods if x.get("id") == "woods-011-overgrown-thicket")

    # Interpret progress_threshold: handle strings like "2R" -> 2 (solo simplification)
    raw_threshold = overgrown_raw.get("progress_threshold", 0)
    if isinstance(raw_threshold, int):
        threshold = raw_threshold
    else:
        # extract leading integer; default to 2 for this demo if missing
        digits = "".join(ch for ch in str(raw_threshold) if ch.isdigit())
        threshold = int(digits) if digits else 2

    feature = Entity(
        id=overgrown_raw["id"],
        title=overgrown_raw["title"],
        entity_type="Feature",
        presence=int(overgrown_raw.get("presence", 1) or 1),
        progress_threshold=threshold,
        harm_threshold=int((overgrown_raw.get("harm_threshold", -1) or -1)),
        area="along_the_way",
    )

    # Load a small mixed hand with different approaches
    explorer_cards = load_json(os.path.join(base_dir, "reference JSON", "Ranger Cards", "explorer_cards.json"))
    personality_cards = load_json(os.path.join(base_dir, "reference JSON", "Ranger Cards", "personality_cards.json"))
    traveler_cards = load_json(os.path.join(base_dir, "reference JSON", "Ranger Cards", "traveler_cards.json"))
    wanted_ids = {
        "explorer-03-a-leaf-in-the-breeze",
        "explorer-13-breathe-into-it",  # conflict + connection icons
    }
    hand_cards: list[Card] = []
    for raw in explorer_cards:
        if raw.get("id") in wanted_ids:
            hand_cards.append(to_card(raw))

    # Add Reason and Connection icons from Personality set
    for raw in personality_cards:
        if raw.get("id") in {"personality-01-insightful", "personality-05-passionate"}:
            hand_cards.append(to_card(raw))

    # Add a simple Conflict icon from Traveler (Trail Mix)
    for raw in traveler_cards:
        if raw.get("id") == "traveler-04-trail-mix":
            hand_cards.append(to_card(raw))

    # Fallback: if something broke, create a dummy Exploration 1 card
    if not hand_cards:
        hand_cards = [
            Card(id="demo-explore-1", title="Demo Explore +1", card_type="moment", approach=ApproachIcons({"Exploration": 1})),
            Card(id="demo-explore-1b", title="Demo Explore +1b", card_type="moment", approach=ApproachIcons({"Exploration": 1})),
        ]

    return feature, hand_cards


def clear_screen() -> None:
    # Basic clear that works on Windows terminals
    os.system("cls" if os.name == "nt" else "clear")


def show_state(state: GameState) -> None:
    # Backward-compat wrapper to the view module
    render_state(state)


def register_symbol_effects(eng: GameEngine) -> None:
    # Overgrown Thicket: Mountain discards 1 progress
    def mountain_thicket(state: GameState) -> None:
        e = next(x for x in state.entities if x.id == "woods-011-overgrown-thicket")
        if e.progress > 0:
            e.progress = max(0, e.progress - 1)
            print(f"Challenge: Mountain on {e.title} discards 1 progress (now {e.progress}).")
        else:
            print(f"Challenge: Mountain on {e.title} (no progress to discard).")

    eng.register_symbol_handler(("woods-011-overgrown-thicket", "mountain"), mountain_thicket)


def build_demo_state(base_dir: str) -> GameState:
    feature, hand = pick_demo_cards(base_dir)

    # Add Sunberry Bramble (Feature)
    woods = load_json(os.path.join(base_dir, "reference JSON", "Path Sets", "Terrain sets", "woods.json"))
    bramble_raw = next(x for x in woods if x.get("id") == "woods-009-sunberry-bramble")
    bramble = Entity(
        id=bramble_raw["id"],
        title=bramble_raw["title"],
        entity_type="Feature",
        presence=int(bramble_raw.get("presence", 1) or 1),
        progress_threshold=int(bramble_raw.get("progress_threshold", 3) or 3),
        harm_threshold=int(bramble_raw.get("harm_threshold", 2) or 2),
        area="within_reach",
    )

    # Add Sitka Doe (Being)
    doe_raw = next(x for x in woods if x.get("id") == "woods-007-sitka-doe")
    doe = Entity(
        id=doe_raw["id"],
        title=doe_raw["title"],
        entity_type="Being",
        presence=int(doe_raw.get("presence", 1) or 1),
        progress_threshold=int(doe_raw.get("progress_threshold", 4) or 4),
        harm_threshold=int(doe_raw.get("harm_threshold", 2) or 2),
        area="within_reach",
    )

    # Add Midday Sun (Weather)
    weather_cards = load_json(os.path.join(base_dir, "reference JSON", "weather.json"))
    midsun_raw : dict[str, Any] = next(x for x in weather_cards if x.get("id") == "weather-002-midday-sun")
    weather = Entity(
        id=midsun_raw["id"],
        title=midsun_raw["title"],
        entity_type="Weather",
        presence=0,
        clouds=int((midsun_raw.get("enters_play_with", {}) or {}).get("amount", 0)), #type: ignore
        area="global",
    )

    ranger = RangerState(name="Demo Ranger", hand=hand, energy={"AWA": 3, "FIT": 2, "SPI": 2, "FOC": 1})
    # Build a simple path deck from woods, excluding the ones already in play
    exclude = {feature.id, bramble.id, doe.id}
    deck = build_woods_path_deck(base_dir, exclude_ids=exclude)
    state = GameState(ranger=ranger, entities=[feature, bramble, doe, weather], round_number=1, path_deck=deck)
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
    base_dir = os.getcwd()
    state = build_demo_state(base_dir)
    engine = GameEngine(state)
    register_symbol_effects(engine)
    menu_and_run(engine)


if __name__ == "__main__":
    main()
