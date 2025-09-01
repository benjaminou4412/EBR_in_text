import json
import os
import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple


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
class FeatureState:
    id: str
    title: str
    progress_threshold: int
    current_progress: int = 0

    def add_progress(self, amount: int) -> None:
        self.current_progress = max(0, self.current_progress + max(0, amount))

    def is_cleared(self) -> bool:
        return self.current_progress >= self.progress_threshold


@dataclass
class RangerState:
    name: str
    hand: List[Card] = field(default_factory=list)


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


def pick_demo_cards(base_dir: str) -> Tuple[FeatureState, List[Card]]:
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

    feature = FeatureState(
        id=overgrown_raw["id"],
        title=overgrown_raw["title"],
        progress_threshold=threshold,
        current_progress=0,
    )

    # Load a couple Explorer moments that provide Exploration icons
    explorer_cards = load_json(os.path.join(base_dir, "reference JSON", "Ranger Cards", "explorer_cards.json"))
    wanted_ids = {
        "explorer-03-a-leaf-in-the-breeze",
        "explorer-05-share-in-the-valleys-secrets",
    }
    hand_cards: List[Card] = []
    for raw in explorer_cards:
        if raw.get("id") in wanted_ids:
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


def show_state(feature: FeatureState, ranger: RangerState):
    print("=== Earthborne Rangers - Minimal Demo ===")
    print(f"Feature: {feature.title} ({feature.id})")
    print(f" - Progress: {feature.current_progress}/{feature.progress_threshold}")
    # Avoid Unicode arrow for Windows terminals
    print(" - Test: AWA + [exploration] -> add progress equal to effort")
    print("")
    print(f"Ranger: {ranger.name}")
    print("Hand:")
    for idx, c in enumerate(ranger.hand, start=1):
        exp = c.approach.get("Exploration")
        icon_txt = f"Exploration +{exp}" if exp else "(no Exploration icons)"
        print(f" {idx}. {c.title} — {icon_txt}")
    print("")


def prompt_commit(ranger: RangerState) -> List[int]:
    while True:
        raw = input("Choose cards to commit by number (comma-separated, or blank for none): ").strip()
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


def main():
    base_dir = os.getcwd()
    feature, hand_cards = pick_demo_cards(base_dir)
    ranger = RangerState(name="Demo Ranger", hand=hand_cards)

    while True:
        clear_screen()
        show_state(feature, ranger)

        if feature.is_cleared():
            print(f"Cleared {feature.title}! (Reached threshold)")
            break

        picks = prompt_commit(ranger)
        committed_cards: List[Card] = [ranger.hand[i - 1] for i in picks]
        base_effort = sum(c.approach.get("Exploration") for c in committed_cards)

        mod, symbol = draw_challenge()
        final_effort = base_effort + mod
        if final_effort < 0:
            final_effort = 0

        print("")
        print(f"Committed Exploration icons: {base_effort}")
        print(f"Challenge draw: modifier {mod:+d}, symbol [{symbol.upper()}]")
        print(f"Final effort: {final_effort}")

        # Apply effect for Overgrown Thicket's test
        gained = final_effort
        feature.add_progress(gained)
        print(f"Added progress: {gained}. Now at {feature.current_progress}/{feature.progress_threshold}.")

        # Discard committed cards from hand (simple model)
        if committed_cards:
            # Remove by index descending to avoid reindex issues
            for i in sorted([p - 1 for p in picks], reverse=True):
                del ranger.hand[i]
            print("Committed cards discarded from hand.")

        # For the MVP, we won't implement challenge effect text resolution yet
        print("(Challenge effects for symbol not implemented in this demo.)")

        if not ranger.hand:
            print("Your hand is empty. You can still attempt with 0 icons.")

        cont = input("Press Enter to attempt again, or type q to quit: ").strip().lower()
        if cont == "q":
            break


if __name__ == "__main__":
    main()
