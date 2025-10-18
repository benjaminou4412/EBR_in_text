"""
Utility functions shared across modules
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Card


def get_display_id(cards_in_context: list[Card], card: Card) -> str:
    """
    Generate a display-friendly ID for a card based on context.

    If multiple cards share the same title, appends A, B, C, etc.
    Returns just the title if it's unique in context.
    """
    same_title = [c for c in cards_in_context if c.title == card.title]

    if len(same_title) <= 1:
        return card.title

    # Multiple cards with same title - add letter suffixes
    sorted_cards = sorted(same_title, key=lambda c: c.id)
    index = sorted_cards.index(card)
    letter = chr(65 + index)  # 65 is 'A' in ASCII
    return f"{card.title} {letter}"
