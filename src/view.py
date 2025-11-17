from __future__ import annotations
from typing import Optional, TYPE_CHECKING, Any
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


def render_card_detail(card: Card, engine: GameEngine, displayed_ids: set[str], index: int | None = None, display_id: str | None = None, indent_level: int = 0) -> None:
    """Render a single card with full details in multi-line format, including attachments

    Args:
        card: The card to render
        engine: GameEngine for looking up attached cards within state and referencing Constant Abilities
        displayed_ids: Set of card IDs already displayed (to prevent duplicates)
        index: Optional numeric index to display before card name
        display_id: Optional display ID to use instead of card title
        indent_level: Indentation level for nested attachments (0 = no indent)
    """
    # Skip if already displayed
    if card.id in displayed_ids:
        return

    # Mark this card as displayed
    displayed_ids.add(card.id)

    # Calculate indentation
    indent = "   " * indent_level

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
        print(f"{indent}{index}. {card_name} {type_line}" + is_exhausted)
    else:
        print(f"{indent}{card_name} {type_line}" + is_exhausted)

    # Art description if present and enabled
    if _show_art_descriptions and card.art_description:
        terminal_width = shutil.get_terminal_size(fallback=(120, 24)).columns
        max_art_width = terminal_width - 6 - len(indent)
        if len(card.art_description) > max_art_width:
            wrapped_lines = textwrap.wrap(card.art_description, width=max_art_width)
            for line in wrapped_lines:
                if line == wrapped_lines[0]:
                    print(f"{indent}   {{Art: {line}")
                elif line == wrapped_lines[len(wrapped_lines)-1]:
                    print(f"{indent}   {line}}}")
                else:
                    print(f"{indent}   {line}")
        else:
            print(f"{indent}   {{Art: {card.art_description}}}")

    # Cost/Icons line for ranger cards
    if card.energy_cost is not None or card.approach_icons:
        parts : list[str]= []
        if card.energy_cost is not None and card.aspect:
            parts.append(f"Cost: {card.energy_cost} {card.aspect.value}")
        if card.approach_icons:
            icons_str = ", ".join(f"{k.value}+{v}" for k, v in card.approach_icons.items() if v)
            parts.append(f"Approach Icons: {icons_str}")
        if parts:
            print(f"{indent}   {' | '.join(parts)}")

    # State line for path cards
    if card.presence is not None or card.progress_threshold is not None or card.harm_threshold is not None or card.has_unique_tokens():
        parts = []
        if card.has_unique_tokens():
            token_types = card.unique_tokens.keys()
            for token_type in token_types:
                parts.append(f"{token_type.capitalize()} tokens: {card.get_unique_token_count(token_type)}")

        if card.presence is not None:
            if card.presence == card.get_current_presence(engine):
                parts.append(f"Presence: {card.get_current_presence(engine)}")
            else:
                parts.append(f"Printed Presence: {card.presence}; Current Presence: {card.get_current_presence(engine)}")
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
            print(f"{indent}   {' | '.join(parts)}")

    # Rules text
    if card.abilities_text:
        # Get terminal width, default to 120 if unable to detect
        terminal_width = shutil.get_terminal_size(fallback=(120, 24)).columns
        max_ability_width = terminal_width - 6 - len(indent)  # Account for indentation

        for ability in card.abilities_text:
            # Word wrap long abilities instead of truncating
            if len(ability) > max_ability_width:
                wrapped_lines = textwrap.wrap(ability, width=max_ability_width)
                for line in wrapped_lines:
                    print(f"{indent}   {line}")
            else:
                print(f"{indent}   {ability}")

    # Render attachments recursively
    if card.attached_card_ids:
        print(f"{indent}   ATTACHMENTS:")
        all_cards = engine.state.all_cards_in_play()
        for attached_id in card.attached_card_ids:
            attached_card = engine.state.get_card_by_id(attached_id)
            if attached_card:
                attached_display_id = get_display_id(all_cards, attached_card)
                render_card_detail(attached_card, engine, displayed_ids,
                                 display_id=attached_display_id, indent_level=indent_level + 1)


def render_state(engine: GameEngine, phase_header: str = "") -> None:
    """Render the current game state with optional phase header"""
    r = engine.state.ranger

    # Phase header if provided
    if phase_header:
        print(f"=== {phase_header} ===")

    # Track displayed card IDs to prevent duplicate rendering of attachments
    displayed_ids: set[str] = set()

    # Areas
    all_cards = engine.state.all_cards_in_play()
    for area in [Area.SURROUNDINGS, Area.ALONG_THE_WAY, Area.WITHIN_REACH, Area.PLAYER_AREA]:
        print(f"\n--- {area.value} ---")
        cards = engine.state.areas.get(area, [])
        if cards:
            for card in cards:
                # Only render cards that aren't attached to something else
                # (attachments will be rendered under their parent)
                if card.attached_to_id is None:
                    display_id = get_display_id(all_cards, card)
                    render_card_detail(card, engine, displayed_ids, display_id=display_id)
        else:
            print("[No cards currently in this area]")

    print("")
    # Ranger status line
    ranger_token_card = engine.state.get_card_by_id(r.ranger_token_location)
    if ranger_token_card is None:
        raise RuntimeError(f"Ranger token should always be on a card!")
    ranger_token_id = get_display_id(all_cards, ranger_token_card)
    print(f"Ranger: {r.name} | Energy AWA {r.energy[Aspect.AWA]} FIT {r.energy[Aspect.FIT]} SPI {r.energy[Aspect.SPI]} FOC {r.energy[Aspect.FOC]} | Injury {r.injury}")
    print(f"Remaining deck size: {len(r.deck)} | Discard pile size: {len(r.discard)} | Fatigue stack size: {len(r.fatigue_stack)} | Ranger Token Location: {ranger_token_id}")

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
        # Create a separate displayed_ids set for hand (cards in hand can't be attachments to in-play cards)
        hand_displayed_ids: set[str] = set()
        for i, card in enumerate(r.hand, start=1):
            render_card_detail(card, engine, hand_displayed_ids, index=i)
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
            if card:
                display_name = get_display_id(all_cards, card)
            else:
                display_name = a.source_title
            if a.is_test:
                approach = a.approach
                aspect = a.aspect
                if not isinstance(approach, Approach) or not isinstance(aspect, Aspect):
                    raise RuntimeError(f"A test should always have an approach and aspect!")
                if card:
                    display = f"[Test] {aspect.value} + [{approach.value}]: {a.verb} ({display_name})"
                else:
                    display = f"[Test] {aspect.value} + [{approach.value}]: {a.verb} ({a.source_title})"
            elif a.is_exhaust:
                display = f"[Exhaust] ({display_name})"
            elif a.is_play:
                # Show energy cost for play actions
                if card:
                    cost = card.get_current_energy_cost()
                    aspect = card.aspect
                    if cost is not None and cost > 0 and aspect:
                        display = f"[Play] ({display_name}) - {cost} {aspect.value}"
                    else:
                        display = f"[Play] ({display_name})"
                else:
                    display = f"[Play] ({display_name})"
            else:
                raise RuntimeError(f"All actions right now should be Test, Exhaust, or Play!")
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
        return None
    elif len(targets)==1:
        print(f"Only 1 valid target ({targets[0].title}); automatically chosen.")
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


def choose_order(engine: GameEngine, items: list[Any], prompt: str) -> list[Any]:
    """Prompt player to arrange items in a specific order.

    This is a generic ordering function that can handle any list of items (Cards, EventListeners, etc.).
    The player selects items one at a time to build the ordered list.

    Args:
        engine: GameEngine for context and message display
        items: List of items to order (can be Cards, EventListeners, or any other objects)
        prompt: Description of what's being ordered and why

    Returns:
        The items rearranged in the player's chosen order
    """
    display_and_clear_messages(engine)

    if not items:
        return []

    if len(items) == 1:
        # Only one item, no need to order
        return items

    print(f"\n{prompt}")
    print("Select items in the order you want them (first selected = first to resolve):")

    # Make a working copy we can remove from
    remaining = list(items)
    ordered: list[Any] = []

    all_cards = engine.state.all_cards_in_play()

    while remaining:
        print(f"\nRemaining items ({len(remaining)}):")

        # Display items with appropriate formatting based on type
        from .models import Card, EventListener
        for i, item in enumerate(remaining, start=1):
            if isinstance(item, Card):
                display_name = get_display_id(all_cards, item)
                print(f" {i}. {display_name}")
            elif isinstance(item, EventListener):
                # For listeners, show source card name and event type
                source_card = engine.state.get_card_by_id(item.source_card_id)
                if source_card:
                    source_name = get_display_id(all_cards, source_card)
                    print(f" {i}. {source_name} - {item.event_type.value} ({item.timing_type.value})")
                else:
                    print(f" {i}. {item.event_type.value} listener ({item.timing_type.value})")
            else:
                # Generic fallback - try to display title or string representation
                if hasattr(item, 'title'):
                    print(f" {i}. {item.title}")
                elif hasattr(item, 'name'):
                    print(f" {i}. {item.name}")
                else:
                    print(f" {i}. {str(item)}")

        try:
            choice = input(f"Choose item #{len(ordered) + 1} (or 'done' if finished): ").strip()

            if choice.lower() == 'done':
                # If player says done but items remain, confirm
                if len(remaining) > 0:
                    print(f"Warning: {len(remaining)} items remain unordered.")
                    confirm = input("Add remaining items in current order? (y/n): ").strip().lower()
                    if confirm in ('y', 'yes'):
                        ordered.extend(remaining)
                        break
                    else:
                        continue
                else:
                    break

            if not choice:
                continue

            idx = int(choice) - 1
            if 0 <= idx < len(remaining):
                selected = remaining.pop(idx)
                ordered.append(selected)
                print(f"✓ Added to position {len(ordered)}")
            else:
                print(f"Please enter a number between 1 and {len(remaining)}.")
        except ValueError:
            print("Invalid input. Please enter a number or 'done'.")

    print(f"\n✓ Order finalized: {len(ordered)} items")
    return ordered


def choose_option(engine: GameEngine, options: list[str], prompt: str | None = None) -> str:
    """Prompt player to choose from among several string options.

    This is a generic choice function for situations where the player needs to select
    from text descriptions rather than Card objects (e.g., choosing between different
    token types to discard).

    Args:
        engine: GameEngine for context and message display
        options: List of string descriptions to choose from
        prompt: Optional context message to display before options

    Returns:
        The chosen string option
    """
    display_and_clear_messages(engine)

    if not options:
        raise ValueError("Cannot choose from empty list of options")

    if len(options) == 1:
        # Only one option, auto-select
        return options[0]

    if prompt:
        print(f"\n{prompt}")

    while True:
        for i, option in enumerate(options, start=1):
            print(f" {i}. {option}")

        try:
            choice = input("> ").strip()
            if not choice:
                continue

            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx]
            else:
                print(f"Please enter a number between 1 and {len(options)}.")
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