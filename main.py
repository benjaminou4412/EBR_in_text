import json
import os
import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Callable


# Minimal data structures for this MVP
@dataclass
class ApproachIcons:
    # counts per approach type, e.g., {"Exploration": 1}
    counts: Dict[str, int] = field(default_factory=dict)

    def get(self, approach: str) -> int:
        return self.counts.get(approach, 0)


@dataclass
class Card:
    id: str
    title: str
    card_type: str
    rules_texts: List[str] = field(default_factory=list)
    approach: ApproachIcons = field(default_factory=ApproachIcons)


@dataclass
class Entity:
    id: str
    title: str
    entity_type: str  # Feature | Being | Weather
    presence: int = 1
    progress_threshold: int = -1
    harm_threshold: int = -1
    area: str = "within_reach"  # within_reach | along_the_way | player_area | global
    exhausted: bool = False
    progress: int = 0
    harm: int = 0
    # Weather tokens (simple demo: only clouds)
    clouds: int = 0

    def add_progress(self, amount: int) -> None:
        amt = max(0, amount)
        self.progress = max(0, self.progress + amt)

    def add_harm(self, amount: int) -> None:
        amt = max(0, amount)
        self.harm = max(0, self.harm + amt)

    def clear_if_threshold(self) -> Optional[str]:
        if self.progress_threshold != -1 and self.progress >= self.progress_threshold:
            return "progress"
        if self.harm_threshold != -1 and self.harm >= self.harm_threshold:
            return "harm"
        return None


@dataclass
class RangerState:
    name: str
    hand: List[Card] = field(default_factory=list)
    energy: Dict[str, int] = field(default_factory=lambda: {"AWA": 0, "FIT": 0, "SPI": 0, "FOC": 0})
    injury: int = 0


@dataclass
class GameState:
    ranger: RangerState
    entities: List[Entity]


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def to_card(raw: dict) -> Card:
    approach_counts: Dict[str, int] = {}
    for a in raw.get("approach_icons", []) or []:
        approach = a.get("approach")
        count = a.get("count", 0)
        if approach:
            approach_counts[approach] = approach_counts.get(approach, 0) + int(count)

    rules_texts: List[str] = []
    for r in raw.get("rules", []) or []:
        txt = r.get("text")
        if txt:
            rules_texts.append(txt)

    return Card(
        id=raw.get("id", ""),
        title=raw.get("title", "Untitled"),
        card_type=raw.get("card_type", ""),
        rules_texts=rules_texts,
        approach=ApproachIcons(approach_counts),
    )


def pick_demo_cards(base_dir: str) -> Tuple[Entity, List[Card]]:
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
    hand_cards: List[Card] = []
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


def draw_challenge() -> Tuple[int, str]:
    # Distribution from Learn-to-Play summary (24 cards):
    # +1 x6, 0 x10, -1 x7, -2 x1
    modifiers = [
        *([+1] * 6),
        *([0] * 10),
        *([-1] * 7),
        *([-2] * 1),
    ]
    mod = random.choice(modifiers)
    symbol = random.choice(["sun", "mountain", "crest"])  # uniform as per request
    return mod, symbol


def clear_screen():
    # Basic clear that works on Windows terminals
    os.system("cls" if os.name == "nt" else "clear")


def show_state(state: GameState):
    ranger = state.ranger
    print("=== Earthborne Rangers - Minimal Demo ===")
    print(f"Ranger: {ranger.name} | Energy AWA {ranger.energy['AWA']} | FIT {ranger.energy['FIT']} | SPI {ranger.energy['SPI']} | FOC {ranger.energy['FOC']} | Injury {ranger.injury}")
    print("Hand (approach icons):")
    for idx, c in enumerate(ranger.hand, start=1):
        parts = []
        for a in ["Conflict", "Exploration", "Reason", "Connection"]:
            v = c.approach.get(a)
            if v:
                parts.append(f"{a[:3]}+{v}")
        parts = ", ".join(parts) if parts else "-"
        print(f" {idx}. {c.title} [{parts}]")

    print("\nIn Play:")
    for e in state.entities:
        if e.entity_type == "Feature":
            print(f" - Feature: {e.title} prog {e.progress}/{e.progress_threshold} pres {e.presence} area {e.area}")
        elif e.entity_type == "Being":
            ex = "exhausted" if e.exhausted else "ready"
            print(f" - Being: {e.title} prog {e.progress}/{e.progress_threshold} pres {e.presence} ({ex}) area {e.area}")
        elif e.entity_type == "Weather":
            print(f" - Weather: {e.title} clouds {e.clouds}")
    print("")


def prompt_commit(ranger: RangerState, approach_required: str) -> List[int]:
    while True:
        raw = input(f"Commit cards for [{approach_required}] (comma-separated, blank=none): ").strip()
        if raw == "":
            return []
        try:
            picks = [int(x) for x in raw.split(",") if x.strip()]
            if not all(1 <= p <= len(ranger.hand) for p in picks):
                raise ValueError
            # dedupe while preserving order
            seen = set()
            result = []
            for p in picks:
                if p not in seen:
                    result.append(p)
                    seen.add(p)
            return result
        except ValueError:
            print("Invalid input. Please enter numbers like: 1,2")


def commit_icons_from_picks(ranger: RangerState, picks: List[int], approach_required: str) -> Tuple[int, List[int]]:
    total = 0
    valid_indices: List[int] = []
    for p in picks:
        c = ranger.hand[p - 1]
        val = c.approach.get(approach_required)
        if val:
            total += val
            valid_indices.append(p)
    return total, valid_indices


def discard_committed(ranger: RangerState, indices: List[int]) -> None:
    if not indices:
        return
    for i in sorted([p - 1 for p in indices], reverse=True):
        del ranger.hand[i]


class GameEngine:
    def __init__(self, state: GameState, challenge_drawer: Callable[[], Tuple[int, str]] = draw_challenge):
        self.state = state
        self.draw = challenge_drawer

    def resolve_challenge_symbol(self, symbol: str) -> None:
        # Minimal hook: implement Overgrown Thicket mountain effect
        for e in self.state.entities:
            for_rule = (e.id, e.title, e.entity_type)
            if symbol == "mountain" and e.id == "woods-011-overgrown-thicket":
                if e.progress > 0:
                    e.progress = max(0, e.progress - 1)
                    print(f"Challenge: Mountain on {e.title} discards 1 progress (now {e.progress}).")
                else:
                    print(f"Challenge: Mountain on {e.title} (no progress to discard).")
            else:
                # For now, only log for visibility
                pass

    def perform_test(self, aspect: str, approach: str, difficulty: int, on_success: Callable[[int], None], on_fail: Optional[Callable[[], None]] = None) -> None:
        r = self.state.ranger
        if r.energy.get(aspect, 0) < 1:
            print(f"You need at least 1 {aspect} energy to attempt this test.")
            return

        picks = prompt_commit(r, approach)
        base_icons, valid_indices = commit_icons_from_picks(r, picks, approach)
        mod, symbol = self.draw()
        final_effort = max(0, base_icons + mod)

        # Spend energy
        r.energy[aspect] -= 1

        print("")
        print(f"Committed {approach} icons: {base_icons}")
        print(f"Challenge draw: modifier {mod:+d}, symbol [{symbol.upper()}]")
        print(f"Final effort: {final_effort} vs difficulty {difficulty}")

        success = final_effort >= difficulty
        if success:
            on_success(final_effort)
            print("Success.")
        else:
            if on_fail:
                on_fail()
            print("Failed.")

        discard_committed(r, valid_indices)

        # Resolve challenge effects
        self.resolve_challenge_symbol(symbol)


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
    midsun_raw = next(x for x in weather_cards if x.get("id") == "weather-002-midday-sun")
    weather = Entity(
        id=midsun_raw["id"],
        title=midsun_raw["title"],
        entity_type="Weather",
        presence=0,
        clouds=int((midsun_raw.get("enters_play_with", {}) or {}).get("amount", 0)),
        area="global",
    )

    ranger = RangerState(name="Demo Ranger", hand=hand, energy={"AWA": 3, "FIT": 2, "SPI": 2, "FOC": 1})
    state = GameState(ranger=ranger, entities=[feature, bramble, doe, weather])
    return state


def menu_and_run(engine: GameEngine) -> None:
    while True:
        clear_screen()
        show_state(engine.state)

        # Quick checks for clear
        for e in engine.state.entities:
            cleared = e.clear_if_threshold()
            if cleared == "progress":
                print(f"Cleared by progress: {e.title}")
            elif cleared == "harm":
                print(f"Cleared by harm: {e.title}")

        print("Choose an action:")
        print(" 1) Test: Overgrown Thicket (AWA + Exploration) -> add progress equal to effort")
        print(" 2) Test: Sunberry Bramble (AWA + Reason) [2]: add 1 harm on success")
        print(" 3) Test: Sitka Doe (SPI + Conflict) [X=presence]: move along the way on success")
        print(" 4) Test: Midday Sun (FOC + Reason): add 1 cloud on success")
        print(" 5) Common: Traverse (FIT + Exploration) target Feature [X]")
        print(" 6) Common: Connect (SPI + Connection) target Being [X]")
        print(" 7) Common: Avoid (AWA + Conflict) target Being [X]")
        print(" 8) Common: Remember (FOC + Reason) [1]")
        print(" q) Quit")

        choice = input("> ").strip().lower()
        if choice == "q":
            break

        try:
            choice_i = int(choice)
        except ValueError:
            continue

        ents = {e.id: e for e in engine.state.entities}
        # Map entities
        thicket = next(e for e in engine.state.entities if e.id == "woods-011-overgrown-thicket")
        bramble = ents.get("woods-009-sunberry-bramble")
        doe = ents.get("woods-007-sitka-doe")
        midsun = ents.get("weather-002-midday-sun")

        if choice_i == 1:
            engine.perform_test(
                aspect="AWA",
                approach="Exploration",
                difficulty=1,
                on_success=lambda effort: thicket.add_progress(effort),
            )
        elif choice_i == 2:
            engine.perform_test(
                aspect="AWA",
                approach="Reason",
                difficulty=2,
                on_success=lambda effort: bramble.add_harm(1),
                on_fail=lambda: print("Bramble would fatigue you on fail (not modeled)."),
            )
        elif choice_i == 3:
            engine.perform_test(
                aspect="SPI",
                approach="Conflict",
                difficulty=max(1, doe.presence),
                on_success=lambda effort: setattr(doe, "area", "along_the_way"),
            )
        elif choice_i == 4:
            engine.perform_test(
                aspect="FOC",
                approach="Reason",
                difficulty=1,
                on_success=lambda effort: setattr(midsun, "clouds", midsun.clouds + 1),
            )
        elif choice_i in (5, 6, 7):
            # Pick a target entity by index among valid types
            if choice_i == 5:
                targets = [e for e in engine.state.entities if e.entity_type == "Feature"]
                aspect, approach = "FIT", "Exploration"
                verb = "Traverse"
            elif choice_i == 6:
                targets = [e for e in engine.state.entities if e.entity_type == "Being"]
                aspect, approach = "SPI", "Connection"
                verb = "Connect"
            else:
                targets = [e for e in engine.state.entities if e.entity_type == "Being"]
                aspect, approach = "AWA", "Conflict"
                verb = "Avoid"

            if not targets:
                print("No valid targets.")
                input("Enter to continue...")
                continue

            print(f"Choose target for {verb}:")
            for i, t in enumerate(targets, start=1):
                print(f" {i}. {t.title} (presence {t.presence})")
            try:
                t_i = int(input("> ").strip()) - 1
                target = targets[t_i]
            except Exception:
                continue

            X = max(1, target.presence)
            if choice_i == 5:
                engine.perform_test(
                    aspect=aspect,
                    approach=approach,
                    difficulty=X,
                    on_success=lambda effort, tgt=target: tgt.add_progress(effort),
                    on_fail=lambda: setattr(engine.state.ranger, "injury", engine.state.ranger.injury + 1),
                )
            elif choice_i == 6:
                engine.perform_test(
                    aspect=aspect,
                    approach=approach,
                    difficulty=X,
                    on_success=lambda effort, tgt=target: tgt.add_progress(effort),
                )
            else:
                engine.perform_test(
                    aspect=aspect,
                    approach=approach,
                    difficulty=X,
                    on_success=lambda effort, tgt=target: setattr(tgt, "exhausted", True),
                )
        elif choice_i == 8:
            # Remember common test
            engine.perform_test(
                aspect="FOC",
                approach="Reason",
                difficulty=1,
                on_success=lambda effort: print(f"Scouted {effort} ranger cards, drew 1 (demo)."),
            )
        else:
            continue

        input("Enter to continue...")


def main():
    base_dir = os.getcwd()
    state = build_demo_state(base_dir)
    engine = GameEngine(state)
    menu_and_run(engine)


if __name__ == "__main__":
    main()
