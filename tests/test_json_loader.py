"""
Tests for json_loader.py — parser correctness, fail-loud behavior, and field-level assertions.
"""

import unittest
from ebr.json_loader import (
    parse_card_types, parse_threshold_value, parse_area, parse_energy_cost,
    parse_approach_icons, parse_aspect_requirement, parse_starting_tokens,
    parse_card_abilities, parse_clear_logs, parse_mission_objective_log,
    load_card_json_by_title
)
from ebr.models import CardType, Aspect, Approach, Area
from ebr.cards import (
    BoundarySensor, Passionate, ProwlingWolhund, SitkaBuck, WalkWithMe,
    OvergrownThicket, APerfectDay, MiddaySun, BoulderField, HelpingHand,
    PeerlessPathfinder, HyPimpotChef, BiscuitBasket, SitkaDoe,
    CalypsaRangerMentor, ADearFriend
)


# ── Theme 2: Field-level assertions on representative cards ──────────────

class FieldLevelAssertionTests(unittest.TestCase):
    """Instantiate real cards and verify parsed fields match JSON data.
    Kills load_card_fields return-dict swap mutations."""

    def test_boundary_sensor_gear_fields(self):
        """Gear card: starting_tokens, equip_value, energy_cost, aspect, approach_icons, traits"""
        card = BoundarySensor()
        self.assertEqual(card.card_types, {CardType.RANGER, CardType.GEAR})
        self.assertEqual(card.starting_tokens, ("sensor", 4))
        self.assertEqual(card.equip_value, 2)
        self.assertEqual(card.energy_cost, 1)
        self.assertEqual(card.aspect, Aspect.FIT)
        self.assertEqual(card.requirement, 1)
        self.assertEqual(card.starting_area, Area.PLAYER_AREA)
        self.assertEqual(card.approach_icons, {Approach.EXPLORATION: 1})
        self.assertIn("Tech", card.traits)

    def test_passionate_attribute_fields(self):
        """Attribute card: approach_icons, aspect_requirement, no energy cost"""
        card = Passionate()
        self.assertEqual(card.card_types, {CardType.RANGER, CardType.ATTRIBUTE})
        self.assertEqual(card.approach_icons, {Approach.CONNECTION: 1})
        self.assertEqual(card.aspect, Aspect.FIT)
        self.assertEqual(card.requirement, 1)
        self.assertIsNone(card.energy_cost)
        self.assertIsNone(card.starting_area)

    def test_prowling_wolhund_being_fields(self):
        """Being card: presence, challenge abilities, thresholds, area"""
        card = ProwlingWolhund()
        self.assertEqual(card.card_types, {CardType.PATH, CardType.BEING})
        self.assertEqual(card.presence, 2)
        self.assertEqual(card.harm_threshold, 4)
        self.assertEqual(card.progress_threshold, 6)
        self.assertEqual(card.starting_area, Area.WITHIN_REACH)
        # Challenge abilities should have symbol prefix
        challenge_abilities = [a for a in card.abilities_text if ": " in a and a.split(": ")[0] in ("sun", "crest")]
        self.assertEqual(len(challenge_abilities), 2)

    def test_sitka_buck_being_fields(self):
        """Being card: presence, harm/progress thresholds, traits"""
        card = SitkaBuck()
        self.assertEqual(card.card_types, {CardType.PATH, CardType.BEING})
        self.assertEqual(card.presence, 1)
        self.assertEqual(card.harm_threshold, 3)
        self.assertEqual(card.progress_threshold, 5)
        self.assertIn("Prey", card.traits)
        self.assertIn("Mammal", card.traits)

    def test_walk_with_me_moment_fields(self):
        """Moment card: energy_cost, aspect, no starting_area"""
        card = WalkWithMe()
        self.assertEqual(card.card_types, {CardType.RANGER, CardType.MOMENT})
        self.assertEqual(card.energy_cost, 1)
        self.assertEqual(card.aspect, Aspect.SPI)
        self.assertEqual(card.requirement, 1)
        self.assertIsNone(card.starting_area)

    def test_overgrown_thicket_feature_fields(self):
        """Feature card: progress_threshold parsed from '2R' string"""
        card = OvergrownThicket()
        self.assertEqual(card.card_types, {CardType.PATH, CardType.FEATURE})
        self.assertEqual(card.harm_threshold, 3)
        self.assertEqual(card.progress_threshold, 2)  # parsed from "2R"

    def test_a_perfect_day_weather_fields(self):
        """Weather card: starting_tokens, thresholds as None from -1"""
        card = APerfectDay()
        self.assertEqual(card.card_types, {CardType.WEATHER})
        self.assertEqual(card.starting_tokens, ("cloud", 3))
        self.assertIsNone(card.harm_threshold)
        self.assertIsNone(card.progress_threshold)

    def test_midday_sun_zero_starting_tokens(self):
        """Weather card: enters_play_with amount=0 is valid"""
        card = MiddaySun()
        self.assertEqual(card.card_types, {CardType.WEATHER})
        self.assertEqual(card.starting_tokens, ("cloud", 0))

    def test_boulder_field_location_fields(self):
        """Location card: campaign_log_entry"""
        card = BoulderField()
        self.assertEqual(card.card_types, {CardType.LOCATION})
        self.assertEqual(card.on_enter_log, "14")

    def test_helping_hand_mission_fields(self):
        """Mission card: starting_area=SURROUNDINGS, mission_description"""
        card = HelpingHand()
        self.assertEqual(card.card_types, {CardType.MISSION})
        self.assertEqual(card.starting_area, Area.SURROUNDINGS)
        self.assertIsNotNone(card.mission_description)

    def test_peerless_pathfinder_role_fields(self):
        """Role card: RANGER+ROLE types, starting_area=PLAYER_AREA"""
        card = PeerlessPathfinder()
        self.assertEqual(card.card_types, {CardType.RANGER, CardType.ROLE})
        self.assertEqual(card.starting_area, Area.PLAYER_AREA)

    def test_biscuit_basket_mission_clear_log(self):
        """Mission card with campaign log in objective text"""
        card = BiscuitBasket()
        self.assertEqual(card.mission_clear_log, "1.02")


# ── Theme 3: load_card_json_by_title error paths ─────────────────────────

class LoadCardJsonErrorTests(unittest.TestCase):
    """Test unhappy paths in load_card_json_by_title."""

    def test_unknown_card_set_raises(self):
        with self.assertRaises(ValueError) as ctx:
            load_card_json_by_title("Anything", "nonexistent_set")
        self.assertIn("Unknown card set", str(ctx.exception))

    def test_missing_card_title_raises(self):
        with self.assertRaises(ValueError) as ctx:
            load_card_json_by_title("Card That Does Not Exist", "explorer")
        self.assertIn("not found", str(ctx.exception))


# ── Theme 4: parse_threshold_value edge cases ────────────────────────────

class ParseThresholdValueTests(unittest.TestCase):
    """Test all 6 branches of parse_threshold_value."""

    def test_none_returns_missing(self):
        self.assertEqual(parse_threshold_value(None), (None, False, False))

    def test_negative_one_returns_missing(self):
        self.assertEqual(parse_threshold_value(-1), (None, False, False))

    def test_negative_two_returns_nulled(self):
        self.assertEqual(parse_threshold_value(-2), (None, True, False))

    def test_positive_int_returns_value(self):
        self.assertEqual(parse_threshold_value(3), (3, False, False))

    def test_zero_returns_zero(self):
        self.assertEqual(parse_threshold_value(0), (0, False, False))

    def test_ranger_token_string(self):
        self.assertEqual(parse_threshold_value("Ranger Token"), (None, False, True))

    def test_ranger_token_case_insensitive(self):
        self.assertEqual(parse_threshold_value("ranger token"), (None, False, True))

    def test_digit_string_2R(self):
        self.assertEqual(parse_threshold_value("2R"), (2, False, False))

    def test_digit_string_3R(self):
        self.assertEqual(parse_threshold_value("3R"), (3, False, False))


# ── Theme 1: parse_card_types coverage ───────────────────────────────────

class ParseCardTypesTests(unittest.TestCase):
    """Test parse_card_types for each CardType enum member."""

    def test_ranger_set_membership(self):
        """Explorer set → RANGER base type"""
        types = parse_card_types("explorer", "gear")
        self.assertIn(CardType.RANGER, types)

    def test_path_set_membership(self):
        """Woods set → PATH base type"""
        types = parse_card_types("woods", "being")
        self.assertIn(CardType.PATH, types)

    def test_neither_ranger_nor_path(self):
        """Weather set → no RANGER or PATH"""
        types = parse_card_types("weather", "weather")
        self.assertNotIn(CardType.RANGER, types)
        self.assertNotIn(CardType.PATH, types)

    def test_each_card_type(self):
        """Every card_type string maps to the correct CardType enum"""
        cases = [
            ("gear", CardType.GEAR),
            ("moment", CardType.MOMENT),
            ("attachment", CardType.ATTACHMENT),
            ("attribute", CardType.ATTRIBUTE),
            ("being", CardType.BEING),
            ("feature", CardType.FEATURE),
            ("weather", CardType.WEATHER),
            ("location", CardType.LOCATION),
            ("mission", CardType.MISSION),
            ("role", CardType.ROLE),
        ]
        for type_str, expected_type in cases:
            with self.subTest(type_str=type_str):
                types = parse_card_types("weather", type_str)  # neutral set
                self.assertIn(expected_type, types)

    def test_unknown_card_type_raises(self):
        with self.assertRaises(ValueError) as ctx:
            parse_card_types("weather", "bogus_type")
        self.assertIn("Unknown card_type", str(ctx.exception))

    def test_empty_card_type_no_raise(self):
        """Empty string card_type is valid (some cards have no type beyond set)"""
        types = parse_card_types("weather", "")
        self.assertNotIn(CardType.GEAR, types)  # no type added

    def test_normalization(self):
        """Spaces, underscores, hyphens, case are all normalized"""
        types = parse_card_types("weather", "Being")
        self.assertIn(CardType.BEING, types)
        types = parse_card_types("weather", "BEING")
        self.assertIn(CardType.BEING, types)
        types = parse_card_types("weather", "be-ing")
        self.assertIn(CardType.BEING, types)


# ── Theme 5: parse_card_abilities formatting ─────────────────────────────

class ParseCardAbilitiesTests(unittest.TestCase):
    """Test abilities parsing including challenge symbol formatting."""

    def test_regular_ability(self):
        data = {"rules": [{"text": "Do something cool.", "kind": "regular"}]}
        result = parse_card_abilities(data)
        self.assertEqual(result, ["Do something cool."])

    def test_challenge_ability_with_symbol(self):
        data = {"rules": [{"text": "Deal damage.", "kind": "challenge", "challenge_symbol": "sun"}]}
        result = parse_card_abilities(data)
        self.assertEqual(result, ["sun: Deal damage."])

    def test_challenge_missing_symbol_raises(self):
        data = {"rules": [{"text": "Deal damage.", "kind": "challenge"}]}
        with self.assertRaises(ValueError) as ctx:
            parse_card_abilities(data)
        self.assertIn("challenge_symbol", str(ctx.exception))

    def test_empty_text_skipped(self):
        data = {"rules": [{"text": "", "kind": "regular"}, {"text": "Real ability."}]}
        result = parse_card_abilities(data)
        self.assertEqual(result, ["Real ability."])

    def test_no_rules_returns_empty(self):
        result = parse_card_abilities({})
        self.assertEqual(result, [])


# ── Fail-loud behavior tests for individual parsers ──────────────────────

class ParseStartingTokensFailLoudTests(unittest.TestCase):

    def test_missing_type_raises(self):
        data = {"enters_play_with": {"amount": 3}}
        with self.assertRaises(ValueError) as ctx:
            parse_starting_tokens(data)
        self.assertIn("no 'type'", str(ctx.exception))

    def test_empty_type_raises(self):
        data = {"enters_play_with": {"type": "", "amount": 3}}
        with self.assertRaises(ValueError) as ctx:
            parse_starting_tokens(data)
        self.assertIn("no 'type'", str(ctx.exception))

    def test_valid_tokens_parsed(self):
        data = {"enters_play_with": {"type": "Sensor", "amount": 4}}
        self.assertEqual(parse_starting_tokens(data), ("sensor", 4))

    def test_zero_amount_valid(self):
        data = {"enters_play_with": {"type": "Cloud", "amount": 0}}
        self.assertEqual(parse_starting_tokens(data), ("cloud", 0))

    def test_no_enters_play_with_returns_none(self):
        self.assertIsNone(parse_starting_tokens({}))


class ParseApproachIconsFailLoudTests(unittest.TestCase):

    def test_unknown_approach_raises(self):
        data = {"approach_icons": [{"approach": "Telepathy", "count": 1}]}
        with self.assertRaises(ValueError):
            parse_approach_icons(data)

    def test_valid_approach_parsed(self):
        data = {"approach_icons": [{"approach": "Connection", "count": 2}]}
        result = parse_approach_icons(data)
        self.assertEqual(result, {Approach.CONNECTION: 2})

    def test_no_icons_returns_empty(self):
        self.assertEqual(parse_approach_icons({}), {})


class ParseAspectRequirementFailLoudTests(unittest.TestCase):

    def test_unknown_aspect_raises(self):
        data = {"aspect_requirement": {"aspect": "ZZZ", "min": 1}}
        with self.assertRaises(ValueError):
            parse_aspect_requirement(data)

    def test_valid_aspect_parsed(self):
        data = {"aspect_requirement": {"aspect": "SPI", "min": 2}}
        aspect, min_val = parse_aspect_requirement(data)
        self.assertEqual(aspect, Aspect.SPI)
        self.assertEqual(min_val, 2)

    def test_no_requirement_returns_none(self):
        aspect, min_val = parse_aspect_requirement({})
        self.assertIsNone(aspect)
        self.assertEqual(min_val, 0)


class ParseAreaFailLoudTests(unittest.TestCase):

    def test_unknown_enters_play_raises(self):
        with self.assertRaises(ValueError) as ctx:
            parse_area("flying", {CardType.BEING})
        self.assertIn("Unknown enters_play", str(ctx.exception))

    def test_weather_always_surroundings(self):
        self.assertEqual(parse_area("anything", {CardType.WEATHER}), Area.SURROUNDINGS)

    def test_location_always_surroundings(self):
        self.assertEqual(parse_area("anything", {CardType.LOCATION}), Area.SURROUNDINGS)

    def test_mission_always_surroundings(self):
        self.assertEqual(parse_area("anything", {CardType.MISSION}), Area.SURROUNDINGS)

    def test_gear_always_player_area(self):
        self.assertEqual(parse_area("anything", {CardType.GEAR}), Area.PLAYER_AREA)

    def test_role_always_player_area(self):
        self.assertEqual(parse_area("player area", {CardType.ROLE}), Area.PLAYER_AREA)

    def test_moment_returns_none(self):
        self.assertIsNone(parse_area("anything", {CardType.MOMENT}))

    def test_attribute_returns_none(self):
        self.assertIsNone(parse_area("anything", {CardType.ATTRIBUTE}))

    def test_attachment_returns_none(self):
        self.assertIsNone(parse_area("anything", {CardType.ATTACHMENT}))

    def test_within_reach(self):
        self.assertEqual(parse_area("within_reach", {CardType.BEING}), Area.WITHIN_REACH)

    def test_along_the_way(self):
        self.assertEqual(parse_area("along_the_way", {CardType.FEATURE}), Area.ALONG_THE_WAY)

    def test_surroundings_string(self):
        self.assertEqual(parse_area("surroundings", {CardType.BEING}), Area.SURROUNDINGS)

    def test_none_returns_none(self):
        self.assertIsNone(parse_area(None, {CardType.BEING}))


class ParseEnergyCostTests(unittest.TestCase):

    def test_valid_cost(self):
        data = {"energy_cost": {"amount": 2, "aspect": "AWA"}}
        self.assertEqual(parse_energy_cost(data), 2)

    def test_no_cost_returns_none(self):
        self.assertIsNone(parse_energy_cost({}))

    def test_zero_cost_returns_none(self):
        """Zero energy cost treated as no cost"""
        data = {"energy_cost": {"amount": 0, "aspect": "AWA"}}
        self.assertIsNone(parse_energy_cost(data))


class ParseClearLogsTests(unittest.TestCase):

    def test_progress_clear_log(self):
        data = {"rules": [{"text": "When you clear [progress], read [Campaign Log Entry] 89"}]}
        progress, harm = parse_clear_logs(data)
        self.assertEqual(progress, "89")
        self.assertIsNone(harm)

    def test_harm_clear_log(self):
        data = {"rules": [{"text": "When you clear [harm], read [Campaign Log Entry] 110.15"}]}
        progress, harm = parse_clear_logs(data)
        self.assertIsNone(progress)
        self.assertEqual(harm, "110.15")

    def test_no_clear_rules(self):
        data = {"rules": [{"text": "Some other ability."}]}
        progress, harm = parse_clear_logs(data)
        self.assertIsNone(progress)
        self.assertIsNone(harm)

    def test_no_rules(self):
        progress, harm = parse_clear_logs({})
        self.assertIsNone(progress)
        self.assertIsNone(harm)


class ParseMissionObjectiveLogTests(unittest.TestCase):

    def test_extracts_log_number(self):
        data = {"mission_objective": "Complete the task: [Campaign Log Entry] 1.02"}
        self.assertEqual(parse_mission_objective_log(data), "1.02")

    def test_no_objective_returns_none(self):
        self.assertIsNone(parse_mission_objective_log({}))

    def test_no_log_in_objective_returns_none(self):
        data = {"mission_objective": "Just do the thing."}
        self.assertIsNone(parse_mission_objective_log(data))


if __name__ == "__main__":
    unittest.main()
