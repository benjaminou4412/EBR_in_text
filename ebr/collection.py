"""
Card Collection — tracks all path cards, their set membership, and checked-out status.

In the physical board game, each card is a single object that lives in a set box
(Valley, Woods, etc.). Cards are "checked out" into the path deck / play / discard
during a day, and returned to their set at day's end or when you travel.

The collection uses a factory pattern: each CardEntry holds a card class and
instantiates a fresh Card when checked out. This naturally handles state reset
(cards lose all mutable state when they return to the collection).

Persistent state across days (set transfers, removals) is stored on the
CampaignTracker as CollectionChange records and applied when rebuilding
the collection each day.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
import random

if TYPE_CHECKING:
    from .models import Card
    from .engine import GameEngine


@dataclass
class CardEntry:
    """A single card (or copy of a card) in the collection."""
    card_class: type          # The Card subclass to instantiate
    title: str                # Card title (for lookups)
    set_name: str             # Which set this belongs to ("Valley", "Woods", etc.)
    copy_index: int           # For multi-copy cards (0, 1, 2...)
    stable_id: str            # Stable identifier across instantiations
    checked_out: bool = False # True when in path deck / in play / in discard


@dataclass
class CollectionChange:
    """A permanent change to the collection, stored on CampaignTracker."""
    stable_id: str
    change_type: str              # "moved" or "removed"
    target_set: str | None = None # For "moved" changes
    description: str = ""         # Human-readable note, e.g. "Day 5: Tala moved to Tumbledown"


@dataclass
class CardCollection:
    """Tracks all path cards and their set membership."""
    entries: list[CardEntry] = field(default_factory=list)
    removed_ids: set[str] = field(default_factory=set)

    # --- Queries ---

    def get_available_in_set(self, set_name: str) -> list[CardEntry]:
        """Get entries that are available (not checked out, not removed) in a set."""
        return [e for e in self.entries
                if e.set_name == set_name
                and not e.checked_out
                and e.stable_id not in self.removed_ids]

    def get_all_in_set(self, set_name: str) -> list[CardEntry]:
        """Get all entries in a set (including checked out, excluding removed)."""
        return [e for e in self.entries
                if e.set_name == set_name
                and e.stable_id not in self.removed_ids]

    def get_entry_by_id(self, stable_id: str) -> CardEntry | None:
        """Find an entry by its stable ID."""
        for e in self.entries:
            if e.stable_id == stable_id:
                return e
        return None

    # --- Checkout / Checkin ---

    def checkout_entries(self, entries_to_checkout: list[CardEntry]) -> list['Card']:
        """Mark entries as checked out and return fresh Card instances."""
        cards = []
        for entry in entries_to_checkout:
            entry.checked_out = True
            card = entry.card_class()
            card.id = entry.stable_id
            cards.append(card)
        return cards

    def checkout_by_title(self, set_name: str, title: str) -> 'Card | None':
        """Check out a specific card by title from a set. Returns None if unavailable."""
        for entry in self.get_available_in_set(set_name):
            if entry.title == title:
                entry.checked_out = True
                card = entry.card_class()
                card.id = entry.stable_id
                return card
        return None

    def checkin_all(self, except_ids: set[str] | None = None) -> None:
        """Return all checked-out cards to the collection.

        Cards whose stable_id is in except_ids stay checked out
        (used for Persistent cards that remain in play after travel).
        """
        except_ids = except_ids or set()
        for entry in self.entries:
            if entry.checked_out and entry.stable_id not in except_ids:
                entry.checked_out = False

    # --- Permanent changes ---
    # These methods both update the in-memory collection AND record a
    # CollectionChange so the change persists across days.

    def move_to_set(self, stable_id: str, target_set: str,
                    changes: list['CollectionChange'], description: str = "") -> None:
        """Permanently move a card to a different set."""
        entry = self.get_entry_by_id(stable_id)
        if entry is not None:
            entry.set_name = target_set
            changes.append(CollectionChange(
                stable_id=stable_id,
                change_type="moved",
                target_set=target_set,
                description=description,
            ))

    def remove_from_collection(self, stable_id: str,
                               changes: list['CollectionChange'], description: str = "") -> None:
        """Permanently remove a card from the collection."""
        self.removed_ids.add(stable_id)
        changes.append(CollectionChange(
            stable_id=stable_id,
            change_type="removed",
            description=description,
        ))

    # --- Path deck assembly ---

    def build_path_deck(self, terrain_set: str, location: 'Card') -> list['Card']:
        """Build a path deck from terrain set + valley or pivotal cards.

        Terrain set: all available cards from the named terrain set.
        If the location is Pivotal: all available cards from the location's pivotal set.
        Otherwise: 3 random available Valley cards.
        """
        # Terrain cards (all available)
        terrain_entries = self.get_available_in_set(terrain_set)
        terrain_cards = self.checkout_entries(terrain_entries)

        # Location-specific or valley cards
        if location.has_trait("Pivotal"):
            loc_entries = self.get_available_in_set(location.title)
            loc_cards = self.checkout_entries(loc_entries)
        else:
            valley_entries = self.get_available_in_set("Valley")
            count = min(3, len(valley_entries))
            selected = random.sample(valley_entries, count)
            loc_cards = self.checkout_entries(selected)

        deck = terrain_cards + loc_cards
        random.shuffle(deck)
        return deck


def _make_stable_id(set_name: str, title: str, copy_index: int) -> str:
    """Generate a deterministic stable ID for a card entry."""
    safe = title.lower().replace(" ", "-").replace(",", "").replace("'", "")
    set_prefix = set_name.lower().replace(" ", "-")
    return f"{set_prefix}-{safe}-{copy_index}"


def build_default_collection() -> CardCollection:
    """Build a fresh collection with all implemented cards in their default sets.

    This is called at the start of each day. Permanent changes (set transfers,
    removals) are applied afterward from CampaignTracker.collection_changes.

    ┌─────────────────────────────────────────────────────────────┐
    │  TODO: WHEN YOU IMPLEMENT A NEW PATH CARD                   │
    │                                                             │
    │  1. Create the Card subclass in ebr/cards/                  │
    │  2. Export it from ebr/cards/__init__.py                    │
    │  3. Add an entry here in the appropriate set definition     │
    │     with the correct title and copy count                   │
    │  4. The title must match the JSON "title" field exactly     │
    └─────────────────────────────────────────────────────────────┘
    """
    # Lazy imports to avoid circular dependency
    from .cards import (ProwlingWolhund, SitkaBuck, SitkaDoe, CausticMulcher,
                        SunberryBramble, OvergrownThicket)
    from .cards import (CalypsaRangerMentor, QuisiVosRascal, TheFundamentalist,
                        TalaTheRedExile)
    from .cards import HyPimpotChef
    from .cards import CerberusianCyclone, BallLightning

    # (card_class, title, copy_count) tuples per set
    set_definitions: dict[str, list[tuple[type, str, int]]] = {
        "Woods": [
            (ProwlingWolhund,  "Prowling Wolhund",  3),
            (SitkaBuck,        "Sitka Buck",         3),
            (SitkaDoe,         "Sitka Doe",          1),
            (CausticMulcher,   "Caustic Mulcher",    1),
            (SunberryBramble,  "Sunberry Bramble",   2),
            (OvergrownThicket, "Overgrown Thicket",  2),
        ],
        "Valley": [
            (CalypsaRangerMentor, "Calypsa, Ranger Mentor", 1),
            (QuisiVosRascal,      "Quisi Vos, Rascal",      1),
            (TheFundamentalist,   "The Fundamentalist",      1),
            (TalaTheRedExile,     "Tala the Red, Exile",     1),
            # TODO: Add remaining Valley cards as they are implemented:
            # The Tenebrae, Ren Kobo (Merchant), Sil Belai (Artist),
            # Ranger Cache, Arcology Sinkhole, Oura Vos (Traveler),
            # Ben Amon (Swift Pilot), Umbra, Quiet, Ol' Bloody Clicker
        ],
        "Lone Tree Station": [
            (HyPimpotChef, "Hy Pimpot, Chef", 1),
            # TODO: Add remaining Lone Tree Station pivotal cards
        ],
        "General": [
            (CerberusianCyclone, "Cerberusian Cyclone", 1),
            (BallLightning,      "Ball Lightning",      1),
        ],
    }

    entries: list[CardEntry] = []
    for set_name, card_defs in set_definitions.items():
        for card_class, title, count in card_defs:
            for i in range(count):
                stable_id = _make_stable_id(set_name, title, i)
                entries.append(CardEntry(
                    card_class=card_class,
                    title=title,
                    set_name=set_name,
                    copy_index=i,
                    stable_id=stable_id,
                ))

    return CardCollection(entries=entries)


def build_collection_for_day(changes: list[CollectionChange]) -> CardCollection:
    """Build a collection for a new day, applying any permanent changes.

    Args:
        changes: List of CollectionChange records from CampaignTracker
    """
    collection = build_default_collection()

    for change in changes:
        if change.change_type == "moved":
            collection.move_to_set(change.stable_id, change.target_set) #type: ignore
        elif change.change_type == "removed":
            collection.remove_from_collection(change.stable_id)

    return collection
