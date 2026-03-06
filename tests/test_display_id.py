"""
Tests for utils.py — get_display_id disambiguation logic.
"""

import unittest
from ebr.models import Card
from ebr.utils import get_display_id


class GetDisplayIdTests(unittest.TestCase):
    """Verify display ID generation for unique and duplicate titles."""

    def test_unique_title_returns_just_title(self):
        card = Card(id="abc", title="Walk With Me")
        context = [card, Card(id="xyz", title="Different Card")]
        self.assertEqual(get_display_id(context, card), "Walk With Me")

    def test_single_card_in_context_returns_title(self):
        card = Card(id="abc", title="Walk With Me")
        self.assertEqual(get_display_id([card], card), "Walk With Me")

    def test_two_duplicates_get_a_and_b_suffixes(self):
        # IDs determine sort order: "aaa" < "bbb"
        card_a = Card(id="aaa", title="Prowling Wolhund")
        card_b = Card(id="bbb", title="Prowling Wolhund")
        context = [card_a, card_b]
        self.assertEqual(get_display_id(context, card_a), "Prowling Wolhund A")
        self.assertEqual(get_display_id(context, card_b), "Prowling Wolhund B")

    def test_three_duplicates_get_a_b_c_suffixes(self):
        card_a = Card(id="aaa", title="Sitka Buck")
        card_b = Card(id="bbb", title="Sitka Buck")
        card_c = Card(id="ccc", title="Sitka Buck")
        context = [card_c, card_a, card_b]  # order in context doesn't matter
        self.assertEqual(get_display_id(context, card_a), "Sitka Buck A")
        self.assertEqual(get_display_id(context, card_b), "Sitka Buck B")
        self.assertEqual(get_display_id(context, card_c), "Sitka Buck C")

    def test_suffix_based_on_id_sort_order(self):
        """The card with the lexically-smallest ID gets 'A'."""
        card_first = Card(id="001", title="Dup")
        card_second = Card(id="999", title="Dup")
        context = [card_second, card_first]  # reversed in context
        self.assertEqual(get_display_id(context, card_first), "Dup A")
        self.assertEqual(get_display_id(context, card_second), "Dup B")

    def test_mixed_titles_only_disambiguates_matching(self):
        """Cards with different titles don't affect disambiguation."""
        card_a = Card(id="aaa", title="Prowling Wolhund")
        card_b = Card(id="bbb", title="Prowling Wolhund")
        other = Card(id="zzz", title="Sitka Buck")
        context = [card_a, other, card_b]
        self.assertEqual(get_display_id(context, card_a), "Prowling Wolhund A")
        self.assertEqual(get_display_id(context, card_b), "Prowling Wolhund B")
        self.assertEqual(get_display_id(context, other), "Sitka Buck")


if __name__ == "__main__":
    unittest.main()
