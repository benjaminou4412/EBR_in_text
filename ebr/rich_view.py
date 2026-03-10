"""Rich TUI dashboard view for Earthborne Rangers.

Drop-in replacement for view.py's exported functions.  render_state draws a
persistent dashboard; all choose_* functions delegate to the text-mode
implementations since text input works fine below the dashboard.

The key enhancement: view.py's display_and_clear_messages is monkey-patched so
that every choose_* function (which calls display_and_clear_messages at the top)
re-renders the dashboard when there are new messages, keeping them in the
Messages panel rather than printing them as plaintext below the dashboard.
"""
from __future__ import annotations
from typing import Optional, Any, TYPE_CHECKING

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from .models import (
    GameState, Action, CommitDecision, Aspect, Approach, CardType, Area, Card
)
from .utils import get_display_id

# Import the text view module for monkey-patching and delegation
from . import view as _text_view

# Re-export input functions from the text view unchanged
from .view import (  # noqa: F401
    format_action_line,
    choose_action_target,
    choose_commit,
    choose_target,
    choose_targets,
    choose_response,
    choose_order,
    choose_option,
    choose_amount,
    set_show_art_descriptions,
)

if TYPE_CHECKING:
    from .engine import GameEngine

console = Console()

# Track the last phase header so re-renders from display_and_clear_messages
# can reproduce the full dashboard.
_last_phase_header: str = ""


# ---------------------------------------------------------------------------
# Card rendering helpers
# ---------------------------------------------------------------------------

def _card_type_str(card: Card) -> str:
    """Short bracketed type string like [Being] or [Feature | Path]."""
    parts: list[str] = []
    for ct in [CardType.MOMENT, CardType.GEAR, CardType.ATTACHMENT, CardType.ATTRIBUTE,
               CardType.BEING, CardType.FEATURE, CardType.WEATHER, CardType.LOCATION,
               CardType.MISSION, CardType.ROLE]:
        if ct in card.card_types:
            parts.append(ct.value)
    return f"[{' | '.join(parts)}]" if parts else ""


def _card_summary(card: Card, engine: GameEngine, displayed_ids: set[str],
                  indent: int = 0) -> list[str]:
    """Return compact multi-line summary strings for a card (and its attachments)."""
    if card.id in displayed_ids:
        return []
    displayed_ids.add(card.id)

    pad = "  " * indent
    lines: list[str] = []

    # Title line
    all_cards = engine.state.all_cards_in_play()
    name = get_display_id(all_cards, card)
    type_str = _card_type_str(card)
    traits = f" ({', '.join(card.traits)})" if card.traits else ""
    exhausted = " [dim](EXHAUSTED)[/dim]" if card.is_exhausted() else ""
    lines.append(f"{pad}[bold]{name}[/bold] {type_str}{traits}{exhausted}")

    # Keywords
    if card.keywords:
        kw_str = ", ".join(k.value for k in card.keywords)
        lines.append(f"{pad}  {kw_str}")

    # Stats line (presence / progress / harm / tokens)
    stats: list[str] = []
    if card.has_unique_tokens():
        for tok, cnt in card.unique_tokens.items():
            if cnt > 0:
                stats.append(f"{tok.capitalize()}: {cnt}")
    if card.presence is not None:
        cur_pres = card.get_current_presence(engine)
        if cur_pres != card.presence:
            stats.append(f"Pres: {cur_pres} (base {card.presence})")
        else:
            stats.append(f"Pres: {card.presence}")
    if card.progress_threshold is not None:
        stats.append(f"Prog: {card.progress}/{card.get_progress_threshold()}")
    elif card.progress_clears_by_ranger_tokens:
        stats.append(f"Prog: {card.progress}/RT")
    elif card.progress > 0:
        stats.append(f"Prog: {card.progress}")
    if card.harm_threshold is not None:
        stats.append(f"Harm: {card.harm}/{card.get_harm_threshold()}")
    elif card.harm_clears_by_ranger_tokens:
        stats.append(f"Harm: {card.harm}/RT")
    elif card.harm > 0:
        stats.append(f"Harm: {card.harm}")
    if stats:
        lines.append(f"{pad}  {' | '.join(stats)}")

    # Cost / icons (ranger cards)
    cost_parts: list[str] = []
    if card.energy_cost is not None and card.aspect:
        cost_parts.append(f"Cost: {card.energy_cost} {card.aspect.value}")
    if card.approach_icons:
        icons = ", ".join(f"{k.value}+{v}" for k, v in card.approach_icons.items() if v)
        cost_parts.append(icons)
    if cost_parts:
        lines.append(f"{pad}  {' | '.join(cost_parts)}")

    # Attachments
    if card.attached_card_ids:
        for att_id in card.attached_card_ids:
            att = engine.state.get_card_by_id(att_id)
            if att:
                lines.extend(_card_summary(att, engine, displayed_ids, indent + 1))

    return lines


def _build_area_panel(area: Area, cards: list[Card], engine: GameEngine,
                      displayed_ids: set[str]) -> Panel:
    """Build a Rich Panel for one play area."""
    body_lines: list[str] = []
    for card in cards:
        if card.attached_to_id is not None:
            continue  # rendered under parent
        body_lines.extend(_card_summary(card, engine, displayed_ids))
        body_lines.append("")  # blank between cards

    if not body_lines:
        body_lines = ["[dim](empty)[/dim]"]

    # Strip trailing blank
    while body_lines and body_lines[-1] == "":
        body_lines.pop()

    content = Text.from_markup("\n".join(body_lines))
    return Panel(content, title=f"[bold]{area.value}[/bold]", border_style="cyan",
                 expand=True)


def _build_hand_panel(engine: GameEngine) -> Panel:
    """Build a Rich Panel for the ranger's hand."""
    r = engine.state.ranger
    lines: list[str] = []
    if r.hand:
        displayed = set()
        for i, card in enumerate(r.hand, 1):
            card_lines = _card_summary(card, engine, displayed)
            if card_lines:
                # Prepend index to first line
                first = card_lines[0]
                card_lines[0] = f"{i}. {first}"
                lines.extend(card_lines)
                lines.append("")
    else:
        lines.append("[dim](empty hand)[/dim]")

    while lines and lines[-1] == "":
        lines.pop()

    content = Text.from_markup("\n".join(lines))
    return Panel(content, title="[bold]Hand[/bold]", border_style="green", expand=True)


def _build_status_line(engine: GameEngine) -> str:
    """One-line ranger status string."""
    r = engine.state.ranger
    all_cards = engine.state.all_cards_in_play()
    rt_card = engine.state.get_card_by_id(r.ranger_token_location)
    rt_name = get_display_id(all_cards, rt_card) if rt_card else "?"

    return (
        f"[bold]Energy[/bold] AWA {r.energy[Aspect.AWA]}  FIT {r.energy[Aspect.FIT]}  "
        f"SPI {r.energy[Aspect.SPI]}  FOC {r.energy[Aspect.FOC]}  | "
        f"Injury {r.injury}  | Deck {len(r.deck)}  Discard {len(r.discard)}  "
        f"Fatigue {len(r.fatigue_stack)}  | Token: {rt_name}"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_pending_messages: list[str] = []


def display_and_clear_messages(engine: GameEngine) -> None:
    """Drain engine messages into the pending buffer.

    If new messages were found, re-render the full dashboard so they appear
    inside the Messages panel rather than as plaintext below the dashboard.
    """
    has_new = False
    for event in engine.get_messages():
        _pending_messages.append(event.message)
        has_new = True
    engine.clear_messages()
    if has_new:
        render_state(engine, _last_phase_header)


def _build_messages_panel() -> Panel:
    """Build a Rich Panel showing accumulated messages since last render."""
    if _pending_messages:
        content = Text("\n".join(_pending_messages))
    else:
        content = Text("(no recent messages)", style="dim")
    return Panel(content, title="[bold]Event Log[/bold]", border_style="yellow",
                 expand=True)


def render_state(engine: GameEngine, phase_header: str = "") -> None:
    """Clear screen and draw the Rich dashboard."""
    global _last_phase_header
    _last_phase_header = phase_header or _last_phase_header

    # Drain any un-flushed engine messages into the buffer before rendering
    for event in engine.get_messages():
        _pending_messages.append(event.message)
    engine.clear_messages()

    console.clear()

    # --- Header ---
    if phase_header:
        console.print(Panel(Text.from_markup(f"[bold]{phase_header}[/bold]"),
                            box=box.HEAVY, style="bright_white"))

    # --- Status bar ---
    console.print(Text.from_markup(_build_status_line(engine)))
    console.print()

    # --- 4-area columns via a Table ---
    displayed_ids: set[str] = set()
    area_grid = Table(box=box.SIMPLE, expand=True, show_header=False, padding=0)
    area_grid.add_column(ratio=1)
    area_grid.add_column(ratio=1)
    area_grid.add_column(ratio=1)
    area_grid.add_column(ratio=1)

    panels = []
    for area in [Area.SURROUNDINGS, Area.ALONG_THE_WAY, Area.WITHIN_REACH, Area.PLAYER_AREA]:
        cards = engine.state.areas.get(area, [])
        panels.append(_build_area_panel(area, cards, engine, displayed_ids))

    area_grid.add_row(*panels)
    console.print(area_grid)

    # --- Bottom row: Hand (left) | Messages (right) ---
    bottom_grid = Table(box=box.SIMPLE, expand=True, show_header=False, padding=0)
    bottom_grid.add_column(ratio=1)
    bottom_grid.add_column(ratio=1)
    bottom_grid.add_row(_build_hand_panel(engine), _build_messages_panel())
    console.print(bottom_grid)

    # Clear the message buffer now that it's been rendered
    _pending_messages.clear()


def choose_action(actions: list[Action], state: GameState, engine: GameEngine) -> Optional[Action]:
    """Rich-mode choose_action: render dashboard with actions in the Event Log."""
    # Buffer any pending engine messages
    for event in engine.get_messages():
        _pending_messages.append(event.message)
    engine.clear_messages()

    if not actions:
        _pending_messages.append("No actions available.")
        render_state(engine, _last_phase_header)
        return None

    # Inject the action list into the message buffer so it appears in the panel
    _pending_messages.append("\nChoose an action:")
    for i, a in enumerate(actions, start=1):
        _pending_messages.append(format_action_line(a, i, state))

    render_state(engine, _last_phase_header)

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


# ---------------------------------------------------------------------------
# Monkey-patch view.py so that ALL its choose_* functions (which call
# display_and_clear_messages at the top) use our re-rendering version.
# This module is only imported when --graphics-mode is active.
# ---------------------------------------------------------------------------
_text_view.display_and_clear_messages = display_and_clear_messages
