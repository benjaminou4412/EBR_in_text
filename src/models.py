from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Callable, cast, TYPE_CHECKING
from enum import Enum
from .utils import get_display_id
import uuid

if TYPE_CHECKING:
    from .engine import GameEngine


# Enums for fixed game constants

class Aspect(str, Enum):
    """Energy types in Earthborne Rangers."""
    AWA = "AWA"
    FIT = "FIT"
    SPI = "SPI"
    FOC = "FOC"


class ChallengeIcon(str, Enum):
    """Challenge deck symbols."""
    SUN = "sun"
    MOUNTAIN = "mountain"
    CREST = "crest"


class Approach(str, Enum):
    """Approach types for tests."""
    CONFLICT = "Conflict"
    EXPLORATION = "Exploration"
    REASON = "Reason"
    CONNECTION = "Connection"

class Zone(str, Enum):
    SURROUNDINGS = "Surroundings"
    ALONG_THE_WAY = "Along the Way"
    WITHIN_REACH = "Within Reach"
    PLAYER_AREA = "Player Area"

class CardType(str, Enum):
    #parent card categories; weather/location/mission are neither
    RANGER = "Ranger"
    PATH = "Path"

    #below are card "types" in the rules sense

    #ranger card types
    GEAR = "Gear"
    MOMENT = "Moment"
    ATTRIBUTE = "Attribute"
    ATTACHMENT = "Attachment"

    #path card types
    BEING = "Being"
    FEATURE = "Feature"
    
    #misc. card types
    WEATHER = "Weather"
    LOCATION = "Location"
    MISSION = "Mission"

class EventType(str, Enum):
    #timing windows shared by multiple cards
    TAKE_FATIGUE = "take_fatigue"
    PERFORM_TEST = "perform_test"
    COMMIT_EFFORT = "commit_effort"
    AFTER_TEST = "after_test"
    TEST_SUCCEED = "test_succeed"
    PLAY_CARD = "play_card"
    USE_TOKEN = "use_token"
    REST = "rest"
    SUFFER_INJURY = "suffer_injury"
    ADD_HARM = "add_harm"
    ADD_PROGRESS = "add_progress"
    CLEAR = "clear"
    CHALLENGE_EFFECT = "challenge_effect"
    SCOUT = "scout"
    TRAVEL = "travel"
    READY = "ready"
    CHALLENGE_DECK_SHUFFLE = "challenge_deck_shuffle"
    DRAW_CHALLENGE_CARD = "draw_challenge_card"

class Keyword(str, Enum):
    """Keywords that modify card behavior and game rules."""
    AMBUSH = "Ambush" #fatigues ranger on entering their Within Reach
    ASPIRATION = "Aspiration" #has an associated reward card; tracks progress towards unlocking it in campaign log
    CONDUIT = "Conduit" #as an additional cost to play a Manifestation moment, a unique token must be spent off a Conduit gear
    DANGEROUS = "Dangerous" #if this card fatigues you, take an injury
    DEPLOYED = "Deployed" #at the start of Phase 2, you may exhaust this gear. Its deployed ability is only active when ready.
    DISCONNECTED = "Disconnected" #you cannot add progress to this card with the Connect test
    FATIGUING = "Fatiguing" #during refresh, this card fatigues you. May have a number, which specifies the fatigue amount if present.
    FRIENDLY = "Friendly" #you don't take fatigue for interacting past this card. Weapon-traited cards cannot affect this card.
    MANIFESTATION = "Manifestation" #as an additional cost to play a Manifestation moment, a unique token must be spent off a Conduit gear
    OBSTACLE = "Obstacle" #you cannot interact past this card. you cannot travel if this card is ready during Phase 3: Travel.
    PERSISTENT = "Persistent" #this card stays in play when you Travel
    SETUP = "Setup" #At the start of the day after step 1 of setup, you can search your deck for one card with the setup keyword and put it into play for free.
    UNIQUE = "Unique" #A Ranger cannot have two cards with the unique keyword and with the same name from their deck in play at the same time. If a second copy of the same unique card from your deck enters play, the first one is immediately discarded.
    UNTRAVERSABLE = "Untraversable" #you cannot add progress to this card with the Traverse test

class TimingType(str, Enum):
    BEFORE_WOULD = "before_would"
    BEFORE = "before"
    WHEN_WOULD = "when_would"
    WHEN = "when"
    AFTER = "after"



# Core data structures: pure state and card data


#central Card class with all possible needed fields and state variables
#fields not present on a particular card type are left null or null-like
@dataclass
class Card:
    #(mostly) immutable card identity; stuff printed on the card, "base values"
    title: str = ""
    id: str = ""  # Will be auto-generated in __post_init__ if empty
    card_set: str = ""
    flavor_text: str = ""
    card_types: set[CardType] = field(default_factory=lambda: set())
    traits: set[str] = field(default_factory=lambda: set()) #mutable from cards like Trails Markers
    keywords: set[Keyword] = field(default_factory=lambda: set())
    abilities_text: list[str] = field(default_factory=lambda: cast(list[str], [])) #will be mutable in expansion content (mycileal). includes keywords, tests, rules, and challenge effects
    starting_tokens: tuple[str, int] = field(default_factory=lambda: cast(tuple[str, int], {})) #a card only ever has a single type of starting token
    starting_area: Zone | None = None #None for cards that don't enter play, like moments, attributes, etc. Attachments default to None and use targeting to determine their zone
    #ranger cards only
    aspect: Aspect | None = None
    requirement: int = 0 #required aspect level to be legal for deckbuilding; 1-3 are valid values, 0 is null
    energy_cost: int | None = None #cards always cost energy of their aspect type; always cost a single type. null=unplayable
    approach_icons: dict[Approach, int] = field(default_factory=lambda: cast(dict[Approach, int], {})) #empty dict is null
    equip_value: int | None = None
    #path cards only
    harm_threshold: int | None = None #absence of threshold still allows tokens, but will never clear. "-1" in JSON
    progress_threshold: int | None = None
    harm_forbidden : bool = False #a slash through the threshold box indicates no tokens of that type allowed. "-2" in JSON
    progress_forbidden : bool = False
    presence: int | None = None 
    on_enter_log: str | None = None #campaign log related optional fields
    on_progress_clear_log: str | None = None
    on_harm_clear_log: str | None = None

    #mission cards only
    mission_description: str | None = None
    mission_locations: list[str] | None = None
    mission_objective: str | None = None
    mission_clear_log: str | None = None

    #mutable state variables
    exhausted: bool = False
    modifiers : list[ValueModifier] = field(default_factory=lambda:cast(list[ValueModifier],[]))
    unique_tokens : dict[str, int] = field(default_factory=lambda: cast(dict[str, int], {})) #a card will rarely, but sometimes have a mix of non-progress non-harm tokens
    #path cards only
    progress: int = 0
    harm: int = 0

    
    def __post_init__(self):
        """Generate readable instance ID if not provided"""
        if not self.id:
            safe_title = self.title.lower().replace(" ", "-").replace("'", "")
            short_uuid = str(uuid.uuid4())[:4]
            self.id = f"{safe_title}-{short_uuid}"
        
        if self.starting_tokens:
            self.unique_tokens = {self.starting_tokens[0]: self.starting_tokens[1]}
    
    def get_symbol_handlers(self) -> dict[ChallengeIcon, Callable[[GameEngine], None]] | None:
        return None
    
    def get_tests(self) -> list[Action] | None:
        return None

    #todo: methods for adding/removing unique tokens

    #ranger card only methods
    def get_current_equip_value(self) -> int | None:
        if self.equip_value is not None:
            #first, get just the equip value modifiers
            equip_value_mods = [mod for mod in self.modifiers if mod.target == "equip_value"]
            #then, we apply modifiers in order of largest minimums first
            sorted_by_mins = sorted(equip_value_mods, key=lambda m: m.minimum_result, reverse=True)
            current_equip_value = self.equip_value
            for mod in sorted_by_mins:
                current_equip_value = min(mod.minimum_result, current_equip_value + mod.amount)
            return current_equip_value
        else:
            return None
        
    def get_current_energy_cost(self) -> int | None:
        if self.energy_cost is not None:
            #first, get just the equip value modifiers
            energy_cost_mods = [mod for mod in self.modifiers if mod.target == "energy_cost"]
            #then, we apply modifiers in order of largest minimums first
            sorted_by_mins = sorted(energy_cost_mods, key=lambda m: m.minimum_result, reverse=True)
            current_energy_cost = self.energy_cost
            for mod in sorted_by_mins:
                current_energy_cost = min(mod.minimum_result, current_energy_cost + mod.amount)
            return current_energy_cost
        else:
            return None
        
    def enters_hand(self) -> EventListener | None:
        """Moments and other cards that establish a listener upon entering hand implement this"""
        return None

    #path card only methods
    def get_current_presence(self) -> int | None:
        if self.presence is not None:
            #first, get just the presence modifiers
            presence_mods = [mod for mod in self.modifiers if mod.target == "presence"]
            #then, we apply modifiers in order of largest minimums first
            sorted_by_mins = sorted(presence_mods, key=lambda m: m.minimum_result, reverse=True)
            current_presence = self.presence
            for mod in sorted_by_mins:
                current_presence = min(mod.minimum_result, current_presence + mod.amount)
            return current_presence
        else:
            return None
    
    def harm_from_predator(self, engine: GameEngine, symbol: ChallengeIcon) -> None:
        predators = engine.state.get_cards_by_trait("Predator")
        if predators is not None:
            active_predators = [predator for predator in predators if predator.exhausted == False]
            if not active_predators:
                engine.add_message(f"Challenge ({symbol.value}) on {get_display_id(engine.state.all_cards_in_play(), self)}: (no active predators in play)")
            else:
                if len(active_predators)==1:
                    engine.add_message(f"Challenge ({symbol.value}) on {get_display_id(engine.state.all_cards_in_play(), self)}: the active predator in play exhausts itself and harms Sitka Doe:")
                else:
                    engine.add_message(f"Challenge ({symbol.value}) on {get_display_id(engine.state.all_cards_in_play(), self)}: Choose a predator that will exhaust itself and harm Sitka Doe:")
                target_predator = engine.card_chooser(engine, active_predators)
                target_predator.exhausted = True
                target_presence = target_predator.get_current_presence()
                if target_presence is not None:
                    #this should always happen
                    self.add_harm(target_presence)
                    engine.add_message(f"{get_display_id(active_predators, target_predator)} is now exhausted.")
                    engine.add_message(f"{get_display_id(engine.state.all_cards_in_play(), self)} suffered harm equal to {get_display_id(active_predators, target_predator)}'s presence ({target_presence}).")

        else:
            engine.add_message(f"Challenge ({symbol.value}) on {get_display_id(engine.state.all_cards_in_play(), self)}: (no predators in play)")
    
        
    #todo: validate inputs on all these setters; amount should always be positive
    def add_progress(self, amount: int) -> None:
        if not self.progress_forbidden:
            self.progress = max(0, self.progress + amount) #separate methods for removing progress/harm

    def add_harm(self, amount: int) -> None:
        if not self.harm_forbidden:
            self.harm = max(0, self.harm + amount)

    def remove_progress(self, amount: int) -> int: #amount of tokens actually removed often matters
        if not self.progress_forbidden:
            amount_removed = min(self.progress, amount)
            self.progress = self.progress - amount_removed
            return amount_removed
        else:
            return 0

    def remove_harm(self, amount: int) -> int: 
        if not self.harm_forbidden:
            amount_removed = min(self.harm, amount)
            self.harm = self.harm - amount_removed
            return amount_removed
        else:
            return 0
        
    def clear_if_threshold(self) -> str | None: 
        if self.progress_threshold is not None and self.progress >= self.progress_threshold:
            return "progress"
        if self.harm_threshold is not None and self.harm >= self.harm_threshold:
            return "harm"
        return None
    
@dataclass
class ValueModifier:
    target : str = "" #which value field is modified? presence, energy cost, equip slots?
    amount : int = 0 #for now, "set to 0" will be implemented as amount=-9999
    source_id : str = ""
    minimum_result : int = 0 #these go first in the order of operations




@dataclass
class RangerState:
    name: str
    aspects: dict[Aspect, int]
    deck: list[Card] = field(default_factory=lambda: cast(list[Card], []))
    hand: list[Card] = field(default_factory=lambda: cast(list[Card], []))
    discard: list[Card] = field(default_factory=lambda: cast(list[Card], []))
    fatigue_pile: list[Card] = field(default_factory=lambda: cast(list[Card], []))
    energy: dict[Aspect, int] = field(init=False)
    injury: int = 0

    def __post_init__(self):
        self.energy = dict(self.aspects)

    def draw_card(self) -> tuple[EventListener | None, str | None, bool]:
        """Draw a card from deck to hand.
        Returns (listener, message, should_end_day).
        If deck is empty, returns (None, error_message, True)."""
        if len(self.deck) == 0:
            return None, "Cannot draw from empty deck - the day must end!", True
        else:
            drawn: Card = self.deck.pop(0)
            self.hand.append(drawn)
            return drawn.enters_hand(), f"You draw a copy of {drawn.title}.", False

    def spend_energy(self, amount: int, aspect: Aspect) -> tuple[bool, str | None]:
        """Attempt to spend the specified amount of energy from the specified aspect's energy pool.
        Returns (success: bool, error_message: str | None)"""
        curr_energy = self.energy[aspect]
        if amount > curr_energy:
            return (False, f"Insufficient {aspect.value} energy.")
        else:
            self.energy[aspect] = self.energy[aspect] - amount
            return (True, None)
        
    def refresh_all_energy(self) -> None:
        """Reset energy pool to initial amounts dictated by fixed aspects. Excess energy not retained."""
        self.energy = dict(self.aspects)

@dataclass
class GameState:
    ranger: RangerState
    zones: dict[Zone, list[Card]] = field(
        default_factory=lambda: cast(
            dict[Zone, list[Card]], 
            {zone: [] for zone in Zone}
        )
    )
    day_number: int = 1
    round_number: int = 1
    # Path deck for Phase 1 draws
    path_deck: list[Card] = field(default_factory=lambda: cast(list[Card], []))
    path_discard: list[Card] = field(default_factory=lambda: cast(list[Card], []))

    #Card getter methods

    def all_cards_in_play(self) -> list[Card]:
        """Get all cards across all zones"""
        return [card for cards in self.zones.values() for card in cards]
    
    def cards_by_type(self, card_type: CardType) -> list[Card]:
        """Get all cards of a specific type"""
        return [card for card in self.all_cards_in_play() if card_type in card.card_types]
    
    def path_cards_in_play(self) -> list[Card]:
        """Get all path cards (beings and features) in play"""
        return self.cards_by_type(CardType.BEING) + self.cards_by_type(CardType.FEATURE)

    def beings_in_play(self) -> list[Card]:
        """Get all beings currently in play"""
        return self.cards_by_type(CardType.BEING)
    
    def features_in_play(self) -> list[Card]:
        """Get all features currently in play"""
        return self.cards_by_type(CardType.FEATURE)

    def get_card_by_id(self, card_id: str | None) -> Card | None:
        """Get a specific card by its instance ID"""
        return next((c for c in self.all_cards_in_play() if c.id == card_id), None)
    
    def get_card_zone_by_id(self, card_id: str | None) -> Zone | None:
        """Get a card's current zone by its instance ID"""
        for zone in self.zones:
            for card in self.zones[zone]:
                if card.id == card_id:
                    return zone
        return None
    
    def get_cards_by_title(self, title: str) -> list[Card] | None:
        """Get all in-play cards of a given title"""
        results: list[Card] = []
        for zone in self.zones:
            for card in self.zones[zone]:
                if card.title == title:
                    results.append(card)
        if results:
            return results
        else:
            return None
    
    def get_cards_by_trait(self, trait: str) -> list[Card] | None:
        """Get all in-play cards with a given trait"""
        results: list[Card] = []
        for zone in self.zones:
            for card in self.zones[zone]:
                for curr_trait in card.traits:
                    if trait.lower() == curr_trait.lower():
                        results.append(card)
                
        if results:
            return results
        else:
            return None

    def get_cards_between_ranger_and_target(self, target: Card) -> list[Card]:
        """Get all cards that are 'between' the ranger and a target in the given zone.
        Returns cards in order from closest to farthest."""
        between: list[Card] = []
        target_zone = self.get_card_zone_by_id(target.id)
        
        # Cards attached to role are ALWAYS between (all zones)
        # TODO: When we have attachments, add them here
        
        if target_zone == Zone.WITHIN_REACH:
            # Only role attachments (already added above)
            pass
        elif target_zone == Zone.ALONG_THE_WAY:
            # Role attachments + Within Reach
            between.extend(self.zones[Zone.WITHIN_REACH])
        elif target_zone == Zone.SURROUNDINGS:
            # Role attachments + Within Reach + Along the Way
            between.extend(self.zones[Zone.WITHIN_REACH])
            between.extend(self.zones[Zone.ALONG_THE_WAY])
        
        return between


# Action system: derived from state; executed by engine.

@dataclass
class Action:
    id: str  # stable identifier for the action option
    name: str  # human-readable label
    aspect: Aspect | str  # required energy type (if is_test), str for non-test actions like Rest
    approach: Approach | str  # legal approach icons to commit (if is_test), str for non-test actions
    is_test: bool = True
    verb: Optional[str] = None  # action verb (e.g. "Traverse", "Connect", "Hunt") for game effects that care
    # If the action requires a target, provide candidate Card targets based on state
    target_provider: Optional[Callable[[GameState], list['Card']]] = None
    # Computes difficulty for the chosen target (or state)
    difficulty_fn: Callable[[GameState, Optional[str]], int] = lambda _s, _t: 1
    # Effects
    on_success: Callable[[GameEngine, int, Optional[str]], None] = lambda _s, _e, _t: None
    on_fail: Optional[Callable[[GameEngine, Optional[str]], None]] = None
    # Source metadata (for display/tracking)
    source_id: Optional[str] = None  # card/entity id or "common"
    source_title: Optional[str] = None


@dataclass
class CommitDecision:
    # Amount of energy committed
    energy: int = 1
    # Indices into the ranger.hand to commit for icons
    hand_indices: list[int] = field(default_factory=lambda: cast(list[int], []))

@dataclass
class MessageEvent:
    # Message to print to player
    message: str = field(default_factory=lambda:cast(str, ""))

@dataclass
class EventListener:
    event_type: EventType
    effect_fn: Callable[[GameEngine, int], None]
    source_card_id: str
    timing_type: TimingType
    test_type: str | None = None #"Traverse", "Connect", etc.

    
    