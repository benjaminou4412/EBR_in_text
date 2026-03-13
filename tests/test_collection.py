"""Tests for the Card Collection system (ebr/collection.py)."""

import unittest
import random

from ebr.models import Card, CardType, Keyword, Area
from ebr.collection import (
    CardEntry, CollectionChange, CardCollection,
    build_default_collection, build_collection_for_day, _make_stable_id,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class DummyCardA(Card):
    """A minimal Card subclass for testing."""
    def __init__(self):
        super().__init__(title="Dummy A", card_types={CardType.PATH, CardType.BEING},
                         traits={"Human"}, presence=1)


class DummyCardB(Card):
    """Another minimal Card subclass for testing."""
    def __init__(self):
        super().__init__(title="Dummy B", card_types={CardType.PATH, CardType.FEATURE},
                         traits={"Flora"}, presence=2)


class DummyPredator(Card):
    """A dummy predator card."""
    def __init__(self):
        super().__init__(title="Test Predator", card_types={CardType.PATH, CardType.BEING},
                         traits={"Predator"}, presence=3)


class DummyPivotalLocation(Card):
    """A location card with the Pivotal trait."""
    def __init__(self):
        super().__init__(title="Test Pivotal Location",
                         card_types={CardType.LOCATION},
                         traits={"Pivotal"}, presence=0)


class DummyNonPivotalLocation(Card):
    """A location card without the Pivotal trait."""
    def __init__(self):
        super().__init__(title="Test Location",
                         card_types={CardType.LOCATION},
                         traits=set(), presence=0)


def _make_entry(card_class, title, set_name, copy_index=0) -> CardEntry:
    """Create a CardEntry with a deterministic stable_id."""
    stable_id = _make_stable_id(set_name, title, copy_index)
    return CardEntry(card_class=card_class, title=title, set_name=set_name,
                     copy_index=copy_index, stable_id=stable_id)


def _simple_collection() -> CardCollection:
    """Build a small collection for unit testing."""
    entries = [
        _make_entry(DummyCardA, "Dummy A", "Valley", 0),
        _make_entry(DummyCardA, "Dummy A", "Valley", 1),
        _make_entry(DummyCardB, "Dummy B", "Valley", 0),
        _make_entry(DummyCardB, "Dummy B", "Woods", 0),
        _make_entry(DummyCardB, "Dummy B", "Woods", 1),
        _make_entry(DummyPredator, "Test Predator", "Woods", 0),
    ]
    return CardCollection(entries=entries)


# ---------------------------------------------------------------------------
# Stable ID generation
# ---------------------------------------------------------------------------

class TestMakeStableId(unittest.TestCase):

    def test_basic_id(self):
        sid = _make_stable_id("Woods", "Prowling Wolhund", 0)
        self.assertEqual(sid, "woods-prowling-wolhund-0")

    def test_strips_commas_and_apostrophes(self):
        sid = _make_stable_id("Valley", "Calypsa, Ranger Mentor", 0)
        self.assertEqual(sid, "valley-calypsa-ranger-mentor-0")
        sid2 = _make_stable_id("Valley", "Ancestor's Grove", 0)
        self.assertEqual(sid2, "valley-ancestors-grove-0")

    def test_multi_word_set_name(self):
        sid = _make_stable_id("Lone Tree Station", "Hy Pimpot, Chef", 0)
        self.assertEqual(sid, "lone-tree-station-hy-pimpot-chef-0")

    def test_copy_index_varies(self):
        sid0 = _make_stable_id("Woods", "Sitka Buck", 0)
        sid1 = _make_stable_id("Woods", "Sitka Buck", 1)
        sid2 = _make_stable_id("Woods", "Sitka Buck", 2)
        self.assertNotEqual(sid0, sid1)
        self.assertNotEqual(sid1, sid2)
        self.assertTrue(sid0.endswith("-0"))
        self.assertTrue(sid2.endswith("-2"))


# ---------------------------------------------------------------------------
# Query methods
# ---------------------------------------------------------------------------

class TestGetAvailableInSet(unittest.TestCase):

    def test_returns_unchecked_out_entries_in_set(self):
        coll = _simple_collection()
        valley = coll.get_available_in_set("Valley")
        self.assertEqual(len(valley), 3)  # 2 Dummy A + 1 Dummy B

    def test_excludes_checked_out(self):
        coll = _simple_collection()
        coll.entries[0].checked_out = True  # check out first Dummy A
        valley = coll.get_available_in_set("Valley")
        self.assertEqual(len(valley), 2)

    def test_excludes_removed(self):
        coll = _simple_collection()
        coll.removed_ids.add(coll.entries[0].stable_id)
        valley = coll.get_available_in_set("Valley")
        self.assertEqual(len(valley), 2)

    def test_empty_for_nonexistent_set(self):
        coll = _simple_collection()
        result = coll.get_available_in_set("Mountains")
        self.assertEqual(result, [])


class TestGetAllInSet(unittest.TestCase):

    def test_includes_checked_out(self):
        coll = _simple_collection()
        coll.entries[0].checked_out = True
        valley = coll.get_all_in_set("Valley")
        self.assertEqual(len(valley), 3)

    def test_excludes_removed(self):
        coll = _simple_collection()
        coll.removed_ids.add(coll.entries[0].stable_id)
        valley = coll.get_all_in_set("Valley")
        self.assertEqual(len(valley), 2)


class TestGetEntryById(unittest.TestCase):

    def test_finds_existing_entry(self):
        coll = _simple_collection()
        expected = coll.entries[0]
        result = coll.get_entry_by_id(expected.stable_id)
        self.assertIs(result, expected)

    def test_returns_none_for_missing(self):
        coll = _simple_collection()
        result = coll.get_entry_by_id("nonexistent-id")
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# Checkout / Checkin
# ---------------------------------------------------------------------------

class TestCheckoutEntries(unittest.TestCase):

    def test_marks_entries_as_checked_out(self):
        coll = _simple_collection()
        entries = coll.get_available_in_set("Valley")
        self.assertTrue(all(not e.checked_out for e in entries))
        coll.checkout_entries(entries)
        self.assertTrue(all(e.checked_out for e in entries))

    def test_returns_fresh_card_instances(self):
        coll = _simple_collection()
        entries = coll.get_available_in_set("Valley")
        cards = coll.checkout_entries(entries)
        self.assertEqual(len(cards), 3)
        for card, entry in zip(cards, entries):
            self.assertIsInstance(card, entry.card_class)
            self.assertEqual(card.id, entry.stable_id)

    def test_each_checkout_creates_new_instance(self):
        """Two checkouts of the same entry class produce distinct objects."""
        coll = _simple_collection()
        entry = coll.entries[0]
        card1 = coll.checkout_entries([entry])[0]
        entry.checked_out = False  # reset for second checkout
        card2 = coll.checkout_entries([entry])[0]
        self.assertIsNot(card1, card2)


class TestCheckoutByTitle(unittest.TestCase):

    def test_returns_card_and_marks_checked_out(self):
        coll = _simple_collection()
        card = coll.checkout_by_title("Valley", "Dummy A")
        self.assertIsNotNone(card)
        self.assertIsInstance(card, DummyCardA)
        # The entry should now be checked out
        checked = [e for e in coll.entries
                   if e.set_name == "Valley" and e.title == "Dummy A" and e.checked_out]
        self.assertEqual(len(checked), 1)

    def test_returns_none_when_unavailable(self):
        coll = _simple_collection()
        # Check out all Dummy A from Valley
        for e in coll.entries:
            if e.set_name == "Valley" and e.title == "Dummy A":
                e.checked_out = True
        card = coll.checkout_by_title("Valley", "Dummy A")
        self.assertIsNone(card)

    def test_returns_none_for_wrong_set(self):
        coll = _simple_collection()
        card = coll.checkout_by_title("Woods", "Dummy A")
        self.assertIsNone(card)

    def test_returns_none_for_removed_card(self):
        coll = _simple_collection()
        for e in coll.entries:
            if e.set_name == "Valley" and e.title == "Dummy A":
                coll.removed_ids.add(e.stable_id)
        card = coll.checkout_by_title("Valley", "Dummy A")
        self.assertIsNone(card)


class TestCheckinAll(unittest.TestCase):

    def test_checkin_returns_all_cards(self):
        coll = _simple_collection()
        coll.checkout_entries(coll.entries)  # check out everything
        self.assertTrue(all(e.checked_out for e in coll.entries))
        coll.checkin_all()
        self.assertTrue(all(not e.checked_out for e in coll.entries))

    def test_checkin_respects_except_ids(self):
        coll = _simple_collection()
        coll.checkout_entries(coll.entries)
        persistent_id = coll.entries[0].stable_id
        coll.checkin_all(except_ids={persistent_id})
        self.assertTrue(coll.entries[0].checked_out)
        self.assertTrue(all(not e.checked_out for e in coll.entries[1:]))

    def test_checkin_with_none_except_ids(self):
        coll = _simple_collection()
        coll.checkout_entries(coll.entries[:2])
        coll.checkin_all(except_ids=None)
        self.assertTrue(all(not e.checked_out for e in coll.entries))


# ---------------------------------------------------------------------------
# Permanent changes
# ---------------------------------------------------------------------------

class TestMoveToSet(unittest.TestCase):

    def test_moves_entry_to_new_set(self):
        coll = _simple_collection()
        changes: list[CollectionChange] = []
        target_entry = coll.entries[0]  # Dummy A in Valley
        self.assertEqual(target_entry.set_name, "Valley")
        coll.move_to_set(target_entry.stable_id, "Tumbledown", changes,
                         description="Test move")
        self.assertEqual(target_entry.set_name, "Tumbledown")

    def test_records_collection_change(self):
        coll = _simple_collection()
        changes: list[CollectionChange] = []
        target_entry = coll.entries[0]
        coll.move_to_set(target_entry.stable_id, "Tumbledown", changes,
                         description="Day 5: moved")
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].stable_id, target_entry.stable_id)
        self.assertEqual(changes[0].change_type, "moved")
        self.assertEqual(changes[0].target_set, "Tumbledown")
        self.assertEqual(changes[0].description, "Day 5: moved")

    def test_no_op_for_missing_id(self):
        coll = _simple_collection()
        changes: list[CollectionChange] = []
        coll.move_to_set("nonexistent", "Tumbledown", changes)
        self.assertEqual(len(changes), 0)

    def test_moved_card_appears_in_new_set(self):
        coll = _simple_collection()
        changes: list[CollectionChange] = []
        target = coll.entries[0]
        coll.move_to_set(target.stable_id, "Woods", changes)
        woods = coll.get_available_in_set("Woods")
        self.assertIn(target, woods)
        valley = coll.get_available_in_set("Valley")
        self.assertNotIn(target, valley)


class TestRemoveFromCollection(unittest.TestCase):

    def test_removes_entry(self):
        coll = _simple_collection()
        changes: list[CollectionChange] = []
        target = coll.entries[0]
        coll.remove_from_collection(target.stable_id, changes, description="Removed")
        self.assertIn(target.stable_id, coll.removed_ids)
        available = coll.get_available_in_set("Valley")
        self.assertNotIn(target, available)

    def test_records_collection_change(self):
        coll = _simple_collection()
        changes: list[CollectionChange] = []
        target = coll.entries[0]
        coll.remove_from_collection(target.stable_id, changes, description="Gone")
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].change_type, "removed")
        self.assertEqual(changes[0].stable_id, target.stable_id)
        self.assertEqual(changes[0].description, "Gone")

    def test_removed_entry_excluded_from_all_queries(self):
        coll = _simple_collection()
        changes: list[CollectionChange] = []
        target = coll.entries[0]
        coll.remove_from_collection(target.stable_id, changes)
        self.assertEqual(len(coll.get_available_in_set("Valley")), 2)
        self.assertEqual(len(coll.get_all_in_set("Valley")), 2)


# ---------------------------------------------------------------------------
# Path deck building
# ---------------------------------------------------------------------------

class TestBuildPathDeck(unittest.TestCase):

    def test_non_pivotal_location_uses_valley_cards(self):
        """At a non-pivotal location, deck = all terrain + 3 random valley cards."""
        coll = _simple_collection()
        location = DummyNonPivotalLocation()
        random.seed(42)
        deck = coll.build_path_deck("Woods", location)
        # Woods has 3 entries (2 Dummy B + 1 Predator)
        # Valley has 3 entries (2 Dummy A + 1 Dummy B), all 3 should be drawn
        self.assertEqual(len(deck), 6)
        # All entries should now be checked out
        self.assertTrue(all(e.checked_out for e in coll.entries))

    def test_valley_cards_capped_at_3(self):
        """At most 3 valley cards are selected."""
        # Add extra valley entries
        entries = [
            _make_entry(DummyCardA, "Dummy A", "Valley", i) for i in range(10)
        ] + [
            _make_entry(DummyCardB, "Dummy B", "Woods", 0),
        ]
        coll = CardCollection(entries=entries)
        location = DummyNonPivotalLocation()
        random.seed(42)
        deck = coll.build_path_deck("Woods", location)
        # 1 woods + 3 valley = 4
        self.assertEqual(len(deck), 4)
        # Only 3 of the 10 valley entries should be checked out
        valley_checked = [e for e in coll.entries
                          if e.set_name == "Valley" and e.checked_out]
        self.assertEqual(len(valley_checked), 3)

    def test_pivotal_location_uses_pivotal_set(self):
        """At a pivotal location, deck = all terrain + all cards from location's set."""
        entries = [
            _make_entry(DummyCardB, "Dummy B", "Woods", 0),
            _make_entry(DummyCardA, "Pivotal Card", "Test Pivotal Location", 0),
            _make_entry(DummyCardA, "Pivotal Card 2", "Test Pivotal Location", 0),
            _make_entry(DummyCardA, "Valley Bystander", "Valley", 0),
        ]
        coll = CardCollection(entries=entries)
        location = DummyPivotalLocation()
        deck = coll.build_path_deck("Woods", location)
        # 1 woods + 2 pivotal = 3 (valley card NOT included)
        self.assertEqual(len(deck), 3)
        # Valley entry should NOT be checked out
        valley_entry = coll.entries[3]
        self.assertFalse(valley_entry.checked_out)

    def test_checked_out_cards_excluded_from_deck(self):
        """Cards already checked out (e.g. Persistent from previous travel) are not re-added."""
        coll = _simple_collection()
        # Pre-check-out one valley card (simulating a Persistent card)
        coll.entries[0].checked_out = True
        location = DummyNonPivotalLocation()
        random.seed(42)
        deck = coll.build_path_deck("Woods", location)
        # Woods: 3, Valley available: 2 (one already checked out)
        self.assertEqual(len(deck), 5)

    def test_removed_cards_excluded_from_deck(self):
        """Removed cards don't appear in the deck."""
        coll = _simple_collection()
        coll.removed_ids.add(coll.entries[0].stable_id)
        location = DummyNonPivotalLocation()
        random.seed(42)
        deck = coll.build_path_deck("Woods", location)
        # Woods: 3, Valley available: 2 (one removed)
        self.assertEqual(len(deck), 5)

    def test_deck_cards_have_stable_ids(self):
        """Cards returned from build_path_deck should have stable IDs assigned."""
        coll = _simple_collection()
        location = DummyNonPivotalLocation()
        random.seed(42)
        deck = coll.build_path_deck("Woods", location)
        for card in deck:
            entry = coll.get_entry_by_id(card.id)
            self.assertIsNotNone(entry)
            self.assertEqual(card.id, entry.stable_id)


# ---------------------------------------------------------------------------
# build_default_collection
# ---------------------------------------------------------------------------

class TestBuildDefaultCollection(unittest.TestCase):

    def test_has_woods_set(self):
        coll = build_default_collection()
        woods = coll.get_all_in_set("Woods")
        # 3 Wolhund + 3 Buck + 1 Doe + 1 Mulcher + 2 Bramble + 2 Thicket = 12
        self.assertEqual(len(woods), 12)

    def test_has_valley_set(self):
        coll = build_default_collection()
        valley = coll.get_all_in_set("Valley")
        # Calypsa + Quisi + Fundamentalist + Tala = 4
        self.assertEqual(len(valley), 4)

    def test_has_lone_tree_station_set(self):
        coll = build_default_collection()
        lts = coll.get_all_in_set("Lone Tree Station")
        self.assertEqual(len(lts), 1)  # Hy Pimpot

    def test_has_general_set(self):
        coll = build_default_collection()
        general = coll.get_all_in_set("General")
        self.assertEqual(len(general), 2)  # Cyclone + Ball Lightning

    def test_all_entries_start_not_checked_out(self):
        coll = build_default_collection()
        self.assertTrue(all(not e.checked_out for e in coll.entries))

    def test_no_removed_ids(self):
        coll = build_default_collection()
        self.assertEqual(len(coll.removed_ids), 0)

    def test_stable_ids_are_unique(self):
        coll = build_default_collection()
        ids = [e.stable_id for e in coll.entries]
        self.assertEqual(len(ids), len(set(ids)))

    def test_multi_copy_cards_have_distinct_ids(self):
        """Cards with multiple copies (e.g. 3 Prowling Wolhund) each have unique stable IDs."""
        coll = build_default_collection()
        wolhund_entries = [e for e in coll.entries if e.title == "Prowling Wolhund"]
        self.assertEqual(len(wolhund_entries), 3)
        ids = {e.stable_id for e in wolhund_entries}
        self.assertEqual(len(ids), 3)

    def test_card_titles_match_json(self):
        """Spot-check that card titles in the collection match expected JSON titles."""
        coll = build_default_collection()
        titles = {e.title for e in coll.entries}
        self.assertIn("Prowling Wolhund", titles)
        self.assertIn("Calypsa, Ranger Mentor", titles)
        self.assertIn("The Fundamentalist", titles)
        self.assertIn("Cerberusian Cyclone", titles)
        self.assertIn("Hy Pimpot, Chef", titles)

    def test_checkout_produces_correct_card_type(self):
        """Checking out an entry produces an instance of the right Card subclass."""
        from ebr.cards import ProwlingWolhund, CalypsaRangerMentor
        coll = build_default_collection()
        wolhund = coll.checkout_by_title("Woods", "Prowling Wolhund")
        self.assertIsInstance(wolhund, ProwlingWolhund)
        calypsa = coll.checkout_by_title("Valley", "Calypsa, Ranger Mentor")
        self.assertIsInstance(calypsa, CalypsaRangerMentor)


# ---------------------------------------------------------------------------
# build_collection_for_day
# ---------------------------------------------------------------------------

class TestBuildCollectionForDay(unittest.TestCase):

    def test_no_changes_equals_default(self):
        coll = build_collection_for_day([])
        default = build_default_collection()
        self.assertEqual(len(coll.entries), len(default.entries))

    def test_applies_move_change(self):
        changes = [
            CollectionChange(
                stable_id=_make_stable_id("Valley", "Tala the Red, Exile", 0),
                change_type="moved",
                target_set="Tumbledown",
            )
        ]
        coll = build_collection_for_day(changes)
        entry = coll.get_entry_by_id(_make_stable_id("Valley", "Tala the Red, Exile", 0))
        self.assertIsNotNone(entry)
        self.assertEqual(entry.set_name, "Tumbledown")
        # Should not appear in Valley anymore
        valley_titles = {e.title for e in coll.get_all_in_set("Valley")}
        self.assertNotIn("Tala the Red, Exile", valley_titles)

    def test_applies_removal_change(self):
        target_id = _make_stable_id("Woods", "Caustic Mulcher", 0)
        changes = [
            CollectionChange(stable_id=target_id, change_type="removed")
        ]
        coll = build_collection_for_day(changes)
        self.assertIn(target_id, coll.removed_ids)
        woods = coll.get_available_in_set("Woods")
        self.assertFalse(any(e.stable_id == target_id for e in woods))

    def test_changes_not_duplicated_on_rebuild(self):
        """Building for day should not append to the changes list passed in."""
        changes = [
            CollectionChange(
                stable_id=_make_stable_id("Valley", "Quisi Vos, Rascal", 0),
                change_type="moved",
                target_set="Tumbledown",
            )
        ]
        original_len = len(changes)
        build_collection_for_day(changes)
        self.assertEqual(len(changes), original_len)

    def test_multiple_changes_applied_in_order(self):
        tala_id = _make_stable_id("Valley", "Tala the Red, Exile", 0)
        changes = [
            CollectionChange(stable_id=tala_id, change_type="moved",
                             target_set="Tumbledown"),
            CollectionChange(stable_id=tala_id, change_type="moved",
                             target_set="Final Set"),
        ]
        coll = build_collection_for_day(changes)
        entry = coll.get_entry_by_id(tala_id)
        self.assertEqual(entry.set_name, "Final Set")


# ---------------------------------------------------------------------------
# Duplicate prevention (the Persistent Quisi bug)
# ---------------------------------------------------------------------------

class TestNoDuplicateCards(unittest.TestCase):
    """Regression tests for the bug where a Persistent card could appear twice."""

    def test_checked_out_card_not_in_available(self):
        """A checked-out card (e.g. Persistent Quisi traveling with you) must not
        be available for selection into a new path deck."""
        coll = build_default_collection()
        quisi_id = _make_stable_id("Valley", "Quisi Vos, Rascal", 0)
        # Simulate Quisi being checked out (Persistent, traveling with ranger)
        entry = coll.get_entry_by_id(quisi_id)
        entry.checked_out = True
        available = coll.get_available_in_set("Valley")
        self.assertFalse(any(e.stable_id == quisi_id for e in available))

    def test_persistent_card_survives_checkin(self):
        """Persistent cards should remain checked out after checkin_all with except_ids."""
        coll = build_default_collection()
        quisi_id = _make_stable_id("Valley", "Quisi Vos, Rascal", 0)
        # Check out everything
        coll.checkout_entries(coll.entries)
        # Checkin all except Quisi
        coll.checkin_all(except_ids={quisi_id})
        quisi_entry = coll.get_entry_by_id(quisi_id)
        self.assertTrue(quisi_entry.checked_out)
        # Building a new deck should not include Quisi
        location = DummyNonPivotalLocation()
        random.seed(42)
        deck = coll.build_path_deck("Woods", location)
        deck_ids = {card.id for card in deck}
        self.assertNotIn(quisi_id, deck_ids)


# ---------------------------------------------------------------------------
# CollectionChange dataclass
# ---------------------------------------------------------------------------

class TestCollectionChange(unittest.TestCase):

    def test_moved_change_defaults(self):
        change = CollectionChange(stable_id="test-id", change_type="moved",
                                  target_set="Woods")
        self.assertEqual(change.description, "")

    def test_removed_change_has_no_target_set(self):
        change = CollectionChange(stable_id="test-id", change_type="removed")
        self.assertIsNone(change.target_set)


if __name__ == "__main__":
    unittest.main()
