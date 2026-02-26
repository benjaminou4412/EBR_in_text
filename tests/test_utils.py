"""Test utilities for Earthborne Rangers tests."""

from ebr.models import ChallengeCard, ChallengeDeck, ChallengeIcon, Aspect


class MockChallengeDeck(ChallengeDeck):
    """A challenge deck with predetermined cards for testing.

    Unlike the regular ChallengeDeck, this doesn't shuffle on init
    and uses a fixed sequence of cards.
    """

    def __init__(self, cards: list[ChallengeCard]):
        """Initialize with a fixed list of cards (will be drawn in order)."""
        self.deck = list(cards)  # Copy to avoid mutating the input
        self.discard: list[ChallengeCard] = []


def make_challenge_card(
    icon: ChallengeIcon,
    awa: int = 0,
    fit: int = 0,
    spi: int = 0,
    foc: int = 0,
    reshuffle: bool = False
) -> ChallengeCard:
    """Helper to create a challenge card with explicit modifiers."""
    return ChallengeCard(
        icon=icon,
        mods={
            Aspect.AWA: awa,
            Aspect.FIT: fit,
            Aspect.SPI: spi,
            Aspect.FOC: foc,
        },
        reshuffle=reshuffle
    )
