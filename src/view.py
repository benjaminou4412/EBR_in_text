from __future__ import annotations
from typing import Optional, TYPE_CHECKING
import shutil
import textwrap
from .models import (
    GameState, Action, CommitDecision, Aspect, Approach, CardType, Area, Card
)
from .utils import get_display_id

if TYPE_CHECKING:
    from .engine import GameEngine

# Global config for display options
_show_art_descriptions = False

def set_show_art_descriptions(show: bool) -> None:
    """Configure whether to display card art descriptions"""
    global _show_art_descriptions
    _show_art_descriptions = show


def render_card_detail(card: Card, index: int | None = None, display_id: str | None = None) -> None:
    """Render a single card with full details in multi-line format"""
    # Use display_id if provided, otherwise just use title
    card_name = display_id if display_id else card.title

    # Build card type string
    type_strs : list[str]= []
    for ct in [CardType.MOMENT, CardType.GEAR, CardType.ATTACHMENT, CardType.ATTRIBUTE,
               CardType.BEING, CardType.FEATURE, CardType.WEATHER, CardType.LOCATION,
               CardType.MISSION, CardType.ROLE]:
        if ct in card.card_types:
            type_strs.append(ct.value)

    traits_str = ", ".join(card.traits) if card.traits else ""
    type_line = f"[{' | '.join(type_strs)}]"
    if traits_str:
        type_line += f" ({traits_str})"

    # Header line with index if provided
    is_exhausted: str = ""
    if card.is_exhausted():
        is_exhausted = " (EXHAUSTED)"

    if index is not None:
        print(f"{index}. {card_name} {type_line}" + is_exhausted)
    else:
        print(f"{card_name} {type_line}" + is_exhausted)

    # Art description if present and enabled
    if _show_art_descriptions and card.art_description:
        terminal_width = shutil.get_terminal_size(fallback=(120, 24)).columns
        max_art_width = terminal_width - 6
        if len(card.art_description) > max_art_width:
            wrapped_lines = textwrap.wrap(card.art_description, width=max_art_width)
            for line in wrapped_lines:
                if line == wrapped_lines[0]:
                    print(f"   {{Art: {line}")
                elif line == wrapped_lines[len(wrapped_lines)-1]:
                    print(f"   {line}}}")
                else:
                    print(f"   {line}")
        else:
            print(f"   {{Art: {card.art_description}}}")

    # Cost/Icons line for ranger cards
    if card.energy_cost is not None or card.approach_icons:
        parts : list[str]= []
        if card.energy_cost is not None and card.aspect:
            parts.append(f"Cost: {card.energy_cost} {card.aspect.value}")
        if card.approach_icons:
            icons_str = ", ".join(f"{k.value}+{v}" for k, v in card.approach_icons.items() if v)
            parts.append(f"Approach Icons: {icons_str}")
        if parts:
            print(f"   {' | '.join(parts)}")

    # State line for path cards
    if card.presence is not None or card.progress_threshold is not None or card.harm_threshold is not None:
        parts = []
        if card.presence is not None:
            if card.presence == card.get_current_presence():
                parts.append(f"Presence: {card.get_current_presence()}")
            else:
                parts.append(f"Printed Presence: {card.presence}; Current Presence: {card.get_current_presence()}")
        if card.progress_threshold is not None:
            #normal numeric threshold value
            parts.append(f"Progress: {card.progress}/{card.get_progress_threshold()}")
        elif card.progress_clears_by_ranger_tokens:
            parts.append(f"Progress: {card.progress}; clears by Ranger Token(s).")
        elif not card.progress_forbidden:
            parts.append(f"Progress: {card.progress}; no Progress threshold.")
        else:
            parts.append(f"Cannot put Progress on this card.")


        if card.harm_threshold is not None:
            #normal numeric threshold value
            parts.append(f"Harm: {card.harm}/{card.get_harm_threshold()}")
        elif card.harm_clears_by_ranger_tokens:
            parts.append(f"Harm: {card.harm}; clears by Ranger Token(s).")
        elif not card.harm_forbidden:
            parts.append(f"Harm: {card.harm}; no Harm Threshold.")
        else:
            parts.append(f"Cannot put Harm on this card.")
        if parts:
            print(f"   {' | '.join(parts)}")

    # Rules text
    if card.abilities_text:
        # Get terminal width, default to 120 if unable to detect
        terminal_width = shutil.get_terminal_size(fallback=(120, 24)).columns
        max_ability_width = terminal_width - 6  # Account for "   " indentation

        for ability in card.abilities_text:
            # Word wrap long abilities instead of truncating
            if len(ability) > max_ability_width:
                wrapped_lines = textwrap.wrap(ability, width=max_ability_width)
                for line in wrapped_lines:
                    print(f"   {line}")
            else:
                print(f"   {ability}")


def render_state(state: GameState, phase_header: str = "") -> None:
    """Render the current game state with optional phase header"""
    r = state.ranger

    # Phase header if provided
    if phase_header:
        print(f"=== {phase_header} ===")

    # Areas
    all_cards = state.all_cards_in_play()
    for area in [Area.SURROUNDINGS, Area.ALONG_THE_WAY, Area.WITHIN_REACH, Area.PLAYER_AREA]:
        print(f"\n--- {area.value} ---")
        cards = state.areas.get(area, [])
        if cards:
            for card in cards:
                display_id = get_display_id(all_cards, card)
                render_card_detail(card, display_id=display_id)
        else:
            print("[No cards currently in this area]")

    print("")
    # Ranger status line
    ranger_token_card = state.get_card_by_id(r.ranger_token_location)
    if ranger_token_card is None:
        raise RuntimeError(f"Ranger token should always be on a card!")
    ranger_token_id = get_display_id(all_cards, ranger_token_card)
    print(f"Ranger: {r.name} | Energy AWA {r.energy[Aspect.AWA]} FIT {r.energy[Aspect.FIT]} SPI {r.energy[Aspect.SPI]} FOC {r.energy[Aspect.FOC]} | Injury {r.injury}")
    print(f"Remaining deck size: {len(r.deck)} | Discard pile size: {len(r.discard)} | Fatigue stack size: {len(r.fatigue_pile)} | Ranger Token Location: {ranger_token_id}")

    # Discard pile contents (top to bottom)
    if r.discard:
        terminal_width = shutil.get_terminal_size(fallback=(120, 24)).columns
        discard_titles = [card.title for card in r.discard]
        discard_str = ", ".join(discard_titles)
        print("Discard pile (top to bottom): ", end="")
        # Word wrap the discard pile listing
        if len(discard_str) + 30 > terminal_width:  # 30 is length of label
            wrapped = textwrap.wrap(discard_str, width=terminal_width - 4)
            print(wrapped[0])
            for line in wrapped[1:]:
                print(f"    {line}")
        else:
            print(discard_str)

    # Hand
    print("\n--- Hand ---")
    if r.hand:
        for i, card in enumerate(r.hand, start=1):
            render_card_detail(card, index=i)
    else:
        print("[Empty hand]")


def choose_action(actions: list[Action], state: GameState, engine: GameEngine) -> Optional[Action]:
    """Prompt player to choose from available actions"""
    display_and_clear_messages(engine)

    if not actions:
        print("No actions available.")
        return None
    print("\nChoose an action:")

    all_cards = state.all_cards_in_play()

    for i, a in enumerate(actions, start=1):
        # Use verb for condensed display
        if a.source_id and a.source_id != "common":
            # Card-based action - find the card and get display ID
            card = state.get_card_by_id(a.source_id)
            if a.is_test:
                approach = a.approach
                aspect = a.aspect
                if not isinstance(approach, Approach) or not isinstance(aspect, Aspect):
                    raise RuntimeError(f"A test should always have an approach and aspect!")
                if card:
                    display_name = get_display_id(all_cards, card)
                    
                    display = f"[Test] {aspect.value} + [{approach.value}]: {a.verb} ({display_name})"
                else:
                    display = f"[Test] {aspect.value} + [{approach.value}]: {a.verb} ({a.source_title})"
            elif a.is_exhaust:
                display = f"[Exhaust] ({a.source_title})"
            else:
                raise RuntimeError(f"All actions right now should be Test or Exhaust!")
        elif a.verb and a.source_title:
            #Common tests
            approach = a.approach
            aspect = a.aspect
            if not isinstance(approach, Approach) or not isinstance(aspect, Aspect):
                raise RuntimeError(f"A test should always have an approach and aspect!")
            display = f"[Test] {aspect.value} + [{approach.value}]: {a.verb} ({a.source_title})"
        else:
            # Fallback to full name
            display = a.name
        print(f" {i}. {display}")

    raw = input("> ").strip().casefold()
    if raw in ("q", "quit"):
        return None
    if not raw:
        print("Please choose a valid action.")
        return None
    try:
        idx = int(raw) - 1
        return actions[idx]
    except Exception:
        print("Invalid input. Please enter a number.")
        return None


def choose_action_target(state: GameState, action: Action, engine: GameEngine) -> Optional[str]:
    """Prompt player to choose a target for an action"""
    display_and_clear_messages(engine)

    # Use engine to get valid targets (includes Obstacle filtering)
    targets = engine.get_valid_targets(action)

    if not targets:
        print("No valid targets.")
        return None
    elif len(targets)==1:
        print("Only 1 valid target; automatically chosen.")
        return targets[0].id
    print("Choose target:")

    all_cards = state.all_cards_in_play()

    for i, card in enumerate(targets, start=1):
        display_name = get_display_id(all_cards, card)
        print(f" {i}. {display_name}")

    try:
        idx = int(input("> ").strip()) - 1
        return targets[idx].id
    except Exception:
        return None
    
def choose_response(engine: GameEngine, prompt: str) -> bool:
    """Prompt a player on whether to activate a response ability or play a response card

    Args:
        engine: GameEngine for message display
        prompt: Custom prompt text describing the response opportunity

    Returns:
        True if player chooses to play the response, False otherwise
    """
    display_and_clear_messages(engine)
    print(prompt)

    while True:
        choice = input("(y/n): ").strip().casefold()

        if choice in ('y', 'yes'):
            return True
        elif choice in ('n', 'no'):
            return False
        else:
            print("Invalid input. Please enter 'y' or 'n'.")

def choose_target(engine: GameEngine, targets: list[Card]) -> Card:
    """Prompt player to choose from among several cards.

    Args:
        engine: GameEngine for context and message display
        targets: List of Card objects to choose from

    Returns:
        The chosen Card object
    """
    display_and_clear_messages(engine)

    if not targets:
        raise ValueError("Cannot choose from empty list of targets")

    if len(targets) == 1:
        # Only one option, auto-select
        return targets[0]

    # Display options with unique identifiers
    all_cards = engine.state.all_cards_in_play()

    while True:
        for i, card in enumerate(targets, start=1):
            display_name = get_display_id(all_cards, card)
            print(f" {i}. {display_name}")

        try:
            choice = input("> ").strip()
            if not choice:
                continue

            idx = int(choice) - 1
            if 0 <= idx < len(targets):
                return targets[idx]
            else:
                print(f"Please enter a number between 1 and {len(targets)}.")
        except ValueError:
            print("Invalid input. Please enter a number.")


def choose_commit(action: Action, hand_size: int, state: GameState, engine: GameEngine) -> CommitDecision:
    """Prompt player to commit energy and cards for a test"""
    display_and_clear_messages(engine)
    

    # Get display strings for aspect/approach
    aspect_str = action.aspect.value if isinstance(action.aspect, Aspect) else action.aspect
    approach_str = action.approach.value if isinstance(action.approach, Approach) else action.approach

    # Energy commitment
    energy = 1  # default
    raw_energy = input(f"Commit [{aspect_str}] energy (default and minimum 1): ").strip()
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
    raw = input(f"Commit cards for [{approach_str}] (comma-separated indices, blank=none): ").strip()
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


def display_and_clear_messages(engine: GameEngine) -> None:
    """Display and clear messages from the game engine"""
    for event in engine.get_messages():
        print(event.message)
    engine.clear_messages()