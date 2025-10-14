from __future__ import annotations
from typing import Optional
from .models import GameState, Action, CommitDecision, Aspect, CardType, Zone, Card
from .engine import ChallengeOutcome


def render_card_detail(card: Card, index: int | None = None) -> None:
    """Render a single card with full details in multi-line format"""
    # Build card type string
    type_strs : list[str]= []
    for ct in [CardType.MOMENT, CardType.GEAR, CardType.ATTACHMENT, CardType.ATTRIBUTE,
               CardType.BEING, CardType.FEATURE, CardType.WEATHER, CardType.LOCATION, CardType.MISSION]:
        if ct in card.card_types:
            type_strs.append(ct.value)

    traits_str = ", ".join(card.traits) if card.traits else ""
    type_line = f"[{' | '.join(type_strs)}]"
    if traits_str:
        type_line += f" ({traits_str})"

    # Header line with index if provided
    if index is not None:
        print(f"{index}. {card.title} {type_line}")
    else:
        print(f"{card.title} {type_line}")

    # Cost/Icons line for ranger cards
    if card.energy_cost is not None or card.approach_icons:
        parts : list[str]= []
        if card.energy_cost is not None and card.aspect:
            parts.append(f"Cost: {card.energy_cost} {card.aspect.value}")
        if card.approach_icons:
            icons_str = ", ".join(f"{k.value}+{v}" for k, v in card.approach_icons.items() if v)
            parts.append(f"Icons: {icons_str}")
        if parts:
            print(f"   {' | '.join(parts)}")

    # State line for path cards
    if card.presence is not None or card.progress_threshold is not None or card.harm_threshold is not None:
        parts = []
        if card.presence is not None:
            parts.append(f"Presence: {card.presence}")
        if card.progress_threshold is not None:
            parts.append(f"Progress: {card.progress}/{card.progress_threshold}")
        if card.harm_threshold is not None:
            parts.append(f"Harm: {card.harm}/{card.harm_threshold}")
        if card.exhausted:
            parts.append("(EXHAUSTED)")
        if parts:
            print(f"   {' | '.join(parts)}")

    # Rules text
    if card.abilities_text:
        for ability in card.abilities_text:
            # Truncate very long abilities for display
            if len(ability) > 100:
                ability = ability[:97] + "..."
            print(f"   {ability}")


def render_state(state: GameState, phase_header: str = "") -> None:
    """Render the current game state with optional phase header"""
    r = state.ranger

    # Phase header if provided
    if phase_header:
        print(f"=== {phase_header} ===")

    # Ranger status line
    print(f"Ranger: {r.name} | Energy AWA {r.energy[Aspect.AWA]} FIT {r.energy[Aspect.FIT]} SPI {r.energy[Aspect.SPI]} FOC {r.energy[Aspect.FOC]} | Injury {r.injury}")

    # Hand
    print("\n--- Hand ---")
    if r.hand:
        for i, card in enumerate(r.hand, start=1):
            render_card_detail(card, index=i)
    else:
        print("[Empty hand]")

    # Zones
    for zone in [Zone.SURROUNDINGS, Zone.ALONG_THE_WAY, Zone.WITHIN_REACH, Zone.PLAYER_AREA]:
        print(f"\n--- {zone.value} ---")
        cards = state.zones.get(zone, [])
        if cards:
            for card in cards:
                render_card_detail(card)
        else:
            print("[No cards currently in this zone]")

    print("")


def choose_action(actions: list[Action]) -> Optional[Action]:
    """Prompt player to choose from available actions"""
    if not actions:
        print("No actions available.")
        return None
    print("\nChoose an action:")
    for i, a in enumerate(actions, start=1):
        # Use verb for condensed display
        if a.verb and a.source_title:
            display = f"{a.verb} ({a.source_title})"
        elif a.verb:
            display = a.verb
        else:
            # Fallback to full name
            display = a.name
        print(f" {i}. {display}")

    raw = input("> ").strip().lower()
    if raw in ("q", "quit"):
        return None
    try:
        idx = int(raw) - 1
        return actions[idx]
    except Exception:
        return None


def choose_target(state: GameState, action: Action) -> Optional[str]:
    """Prompt player to choose a target for an action"""
    if not action.target_provider:
        return None
    targets = action.target_provider(state)
    if not targets:
        print("No valid targets.")
        return None
    print("Choose target:")
    for i, t in enumerate(targets, start=1):
        print(f" {i}. {t.title}")
    try:
        idx = int(input("> ").strip()) - 1
        return targets[idx].id
    except Exception:
        return None


def choose_commit(action: Action, hand_size: int) -> CommitDecision:
    """Prompt player to commit energy and cards for a test"""
    # Energy commitment
    energy = 1  # default
    raw_energy = input(f"Commit [{action.aspect}] energy (default 1): ").strip()
    if raw_energy:
        try:
            energy = int(raw_energy)
            if energy < 1:
                print(f"Invalid energy amount, using default (1)")
                energy = 1
        except ValueError:
            print(f"Invalid input '{raw_energy}', using default (1)")
            energy = 1

    # Card commitment
    raw = input(f"Commit cards for [{action.approach}] (comma-separated indices, blank=none): ").strip()
    hand_indices : list[int] = []
    if raw:
        try:
            picks = [int(x) - 1 for x in raw.split(",") if x.strip()]
            picks = [p for p in picks if 0 <= p < hand_size]
            # dedupe preserve order
            seen : set[int]= set()
            for p in picks:
                if p not in seen:
                    hand_indices.append(p)
                    seen.add(p)
        except ValueError:
            print("Invalid card indices, committing no cards")

    return CommitDecision(hand_indices=hand_indices, energy=energy)


def report_test_outcome(outcome: ChallengeOutcome) -> None:
    """Report the results of a test to the player"""
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

    if outcome.cleared:
        for cleared_card in outcome.cleared:
            print(f"{cleared_card.title} cleared!")

    input("Press Enter to continue...")
