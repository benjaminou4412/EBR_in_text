from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Callable, cast, TYPE_CHECKING
from enum import Enum
from .utils import get_display_id
import uuid
import random
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

class Area(str, Enum):
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
    ROLE = "Role"

    #path card types
    BEING = "Being"
    FEATURE = "Feature"
    
    #misc. card types
    WEATHER = "Weather"
    LOCATION = "Location"
    MISSION = "Mission"

class EventType(str, Enum):
    #timing windows shared by multiple cards
    TAKE_FATIGUE = "take-fatigue"
    PERFORM_TEST = "perform-test"
    COMMIT_EFFORT = "commit-effort"
    AFTER_TEST = "after-test"
    TEST_SUCCEED = "test-succeed"
    PLAY_CARD = "play-card"
    USE_TOKEN = "use-token"
    REST = "rest"
    SUFFER_INJURY = "suffer-injury"
    ADD_HARM = "add-harm"
    ADD_PROGRESS = "add-progress"
    CLEAR = "clear"
    CHALLENGE_EFFECT = "challenge-effect"
    SCOUT = "scout"
    TRAVEL = "travel"
    READY = "ready"
    CHALLENGE_DECK_SHUFFLE = "challenge-deck-shuffle"
    DRAW_CHALLENGE_CARD = "draw-challenge-card"
    REFRESH = "refresh"

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

class ConstantAbilityType(Enum):
    """Types of passive abilities that modify game rules"""

    # Modifications (change values during calculation)
    MODIFY_EFFORT = "modify_effort" #ranger tokens, tenebrae
    MODIFY_PRESENCE = "modify_presence" #boulder field, the fundamentalist, reclaimer mucus

    # Preventions (block actions from happening)
    PREVENT_INTERACTION = "prevent_interaction" #topside mast
    PREVENT_INTERACTION_PAST = "prevent_interaction_past"  # Obstacle
    PREVENT_RANGER_TOKEN_MOVE = "prevent_ranger_token_move" #caustic mulcher, carnivorous naiad
    PREVENT_TRAVEL = "prevent_travel" #obstacle, caustic mulcher
    PREVENT_READYING = "prevent_readying" #caustic mulcher
    PREVENT_PROGRESS = "prevent_progress" #dolewood canopy, Disconnected, Untraversable
    PREVENT_FATIGUE = "prevent_fatigue" #arcology threshold, talus cave, the bubble, fraying rope bridge

    # Exemptions (ignore normally-applied rules)
    SKIP_INTERACTION_FATIGUE = "skip_interaction_fatigue" # Friendly
    IGNORE_KEYWORD = "ignore_keyword" #spiderline stanchion
    TREAT_AS_EXHAUSTED = "treat_as_exhausted" #dolewood canopy
    IGNORE_WEAPON_EFFECTS = "ignore_weapon_effects" #Friendly

    # Enablement (grant access to abilities)
    GRANT_ABILITY = "grant_ability" #deep woods
    GRANT_TEST = "grant_test" #trained stilt-horse
    GRANT_KEYWORD = "grant_keyword" #puffercrawler, bloodbeckoned velox, trained stilt-horse


# Challenge deck classes

@dataclass
class ChallengeCard:
    """A card in the challenge deck with modifiers for each aspect and a symbol."""
    icon: ChallengeIcon
    mods: dict[Aspect, int]
    reshuffle: bool

    def __repr__(self):
        def mod_to_string(mod: int) -> str:
            if mod >= 0:
                return f"+{mod}"
            else:
                return f"{mod}"
        awa_mod = mod_to_string(self.mods[Aspect.AWA])
        fit_mod = mod_to_string(self.mods[Aspect.FIT])
        foc_mod = mod_to_string(self.mods[Aspect.FOC])
        spi_mod = mod_to_string(self.mods[Aspect.SPI])
        return(f"AWA{awa_mod} | FIT{fit_mod} | FOC{foc_mod} | SPI{spi_mod} | {self.icon.value.upper()}" + (" | Reshuffle" if self.reshuffle else ""))


class ChallengeDeck:
    """The challenge deck used for test resolution.

    Cards are drawn one at a time, and some cards trigger a reshuffle when drawn.
    """

    def __init__(self, deck: list[ChallengeCard] | None = None):
        if deck is None:
            deck = _build_challenge_deck()
        self.deck: list[ChallengeCard] = deck
        random.shuffle(self.deck)
        self.discard: list[ChallengeCard] = []

    def reshuffle(self) -> None:
        """Shuffle discard pile back into deck."""
        self.deck.extend(self.discard)
        self.discard.clear()
        random.shuffle(self.deck)

    def draw_challenge_card(self, engine: GameEngine) -> ChallengeCard:
        """Draw a card from the deck, reshuffling if necessary."""
        engine.add_message(f"Drawing challenge card...")
        if len(self.deck) == 0:
            engine.add_message(f"Challenge deck empty; reshuffling.")
            self.reshuffle()
        drawn = self.deck.pop(0)
        self.discard.append(drawn)
        engine.add_message(f"Drew {drawn}.")
        if drawn.reshuffle:
            self.reshuffle()
            engine.add_message(f"Challenge deck reshuffled.")
        return drawn


def _build_challenge_deck() -> list[ChallengeCard]:
    """Build the standard 24-card challenge deck."""
    card_0 =  ChallengeCard(ChallengeIcon.SUN,      {Aspect.AWA: 0,  Aspect.FIT: -2, Aspect.SPI: 1,  Aspect.FOC: 1},  True)
    card_1 =  ChallengeCard(ChallengeIcon.CREST,    {Aspect.AWA: 0,  Aspect.FIT: -1, Aspect.SPI: 1,  Aspect.FOC: 0},  False)
    card_2 =  ChallengeCard(ChallengeIcon.MOUNTAIN, {Aspect.AWA: -1, Aspect.FIT: 0,  Aspect.SPI: 0,  Aspect.FOC: -1}, False)
    card_3 =  ChallengeCard(ChallengeIcon.CREST,    {Aspect.AWA: -1, Aspect.FIT: 0,  Aspect.SPI: -1, Aspect.FOC: 0},  False)
    card_4 =  ChallengeCard(ChallengeIcon.CREST,    {Aspect.AWA: 1,  Aspect.FIT: 1,  Aspect.SPI: -2, Aspect.FOC: 0},  True)
    card_5 =  ChallengeCard(ChallengeIcon.MOUNTAIN, {Aspect.AWA: 1,  Aspect.FIT: -1, Aspect.SPI: -1, Aspect.FOC: 1},  False)
    card_6 =  ChallengeCard(ChallengeIcon.CREST,    {Aspect.AWA: -1, Aspect.FIT: 0,  Aspect.SPI: 0,  Aspect.FOC: 1},  False)
    card_7 =  ChallengeCard(ChallengeIcon.SUN,      {Aspect.AWA: 0,  Aspect.FIT: -1, Aspect.SPI: 0,  Aspect.FOC: -1}, False)
    card_8 =  ChallengeCard(ChallengeIcon.SUN,      {Aspect.AWA: 0,  Aspect.FIT: 0,  Aspect.SPI: -1, Aspect.FOC: -1}, False)
    card_9 =  ChallengeCard(ChallengeIcon.MOUNTAIN, {Aspect.AWA: -1, Aspect.FIT: 1,  Aspect.SPI: 1,  Aspect.FOC: -1}, False)
    card_10 = ChallengeCard(ChallengeIcon.SUN,      {Aspect.AWA: 1,  Aspect.FIT: 0,  Aspect.SPI: 0,  Aspect.FOC: -1}, False)
    card_11 = ChallengeCard(ChallengeIcon.CREST,    {Aspect.AWA: 1,  Aspect.FIT: 0,  Aspect.SPI: 1,  Aspect.FOC: -2}, True)
    card_12 = ChallengeCard(ChallengeIcon.MOUNTAIN, {Aspect.AWA: 1,  Aspect.FIT: -1, Aspect.SPI: 0,  Aspect.FOC: 0},  False)
    card_13 = ChallengeCard(ChallengeIcon.SUN,      {Aspect.AWA: -2, Aspect.FIT: 1,  Aspect.SPI: 0,  Aspect.FOC: 1},  True)
    card_14 = ChallengeCard(ChallengeIcon.SUN,      {Aspect.AWA: 0,  Aspect.FIT: 1,  Aspect.SPI: -1, Aspect.FOC: 0},  False)
    card_15 = ChallengeCard(ChallengeIcon.MOUNTAIN, {Aspect.AWA: 1,  Aspect.FIT: 0,  Aspect.SPI: -1, Aspect.FOC: 0},  False)
    card_16 = ChallengeCard(ChallengeIcon.MOUNTAIN, {Aspect.AWA: 0,  Aspect.FIT: -1, Aspect.SPI: -1, Aspect.FOC: 0},  False)
    card_17 = ChallengeCard(ChallengeIcon.SUN,      {Aspect.AWA: -1, Aspect.FIT: 1,  Aspect.SPI: 0,  Aspect.FOC: 0},  False)
    card_18 = ChallengeCard(ChallengeIcon.CREST,    {Aspect.AWA: 0,  Aspect.FIT: 0,  Aspect.SPI: -1, Aspect.FOC: 1},  False)
    card_19 = ChallengeCard(ChallengeIcon.CREST,    {Aspect.AWA: -1, Aspect.FIT: -1, Aspect.SPI: 0,  Aspect.FOC: 0},  False)
    card_20 = ChallengeCard(ChallengeIcon.SUN,      {Aspect.AWA: -1, Aspect.FIT: 0,  Aspect.SPI: 1,  Aspect.FOC: 0},  False)
    card_21 = ChallengeCard(ChallengeIcon.MOUNTAIN, {Aspect.AWA: 0,  Aspect.FIT: 0,  Aspect.SPI: 1,  Aspect.FOC: -1}, False)
    card_22 = ChallengeCard(ChallengeIcon.CREST,    {Aspect.AWA: 0,  Aspect.FIT: 1,  Aspect.SPI: 0,  Aspect.FOC: -1}, False)
    card_23 = ChallengeCard(ChallengeIcon.MOUNTAIN, {Aspect.AWA: 0,  Aspect.FIT: -1, Aspect.SPI: 0,  Aspect.FOC: 1},  False)
    return [card_0, card_1, card_2, card_3, card_4, card_5, card_6, card_7, card_8, card_9, card_10, card_11, card_12,
            card_13, card_14, card_15, card_16, card_17, card_18, card_19, card_20, card_21, card_22, card_23]


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
    art_description: str | None = None #textual description of card art for accessibility and LLM context
    card_types: set[CardType] = field(default_factory=lambda: set())
    traits: set[str] = field(default_factory=lambda: set()) #mutable from cards like Trails Markers
    keywords: set[Keyword] = field(default_factory=lambda: set())
    abilities_text: list[str] = field(default_factory=lambda: cast(list[str], [])) #will be mutable in expansion content (mycileal). includes keywords, tests, rules, and challenge effects
    starting_tokens: tuple[str, int] = field(default_factory=lambda: cast(tuple[str, int], {})) #a card only ever has a single type of starting token
    starting_area: Area | None = None #None for cards that don't enter play, like moments, attributes, etc. Attachments default to None and use targeting to determine their area
    backside: Card | None = None
    #ranger cards only
    aspect: Aspect | None = None
    requirement: int = 0 #required aspect level to be legal for deckbuilding; 1-3 are valid values, 0 is null
    energy_cost: int | None = None #cards always cost energy of their aspect type; always cost a single type. null=unplayable
    approach_icons: dict[Approach, int] = field(default_factory=lambda: cast(dict[Approach, int], {})) #empty dict is null
    equip_value: int | None = None
    #path cards only
    harm_threshold: int | None = None #absence of threshold still allows tokens, but will never clear. "-1" in JSON
    progress_threshold: int | None = None
    harm_clears_by_ranger_tokens: bool = False #not True for any existing card, but keeping it for future proofing
    progress_clears_by_ranger_tokens: bool = False
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
    attached_to_id: str | None = None  # ID of card this is attached to, or "role" for role attachment
    attached_card_ids: list[str] = field(default_factory=lambda: cast(list[str], []))  # Cards attached to this card
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
        
        if self.backside is None:
            self.backside = FacedownCard(self)
    
    def __str__(self):
        return f"{self.title}"
    
    def get_challenge_handlers(self) -> dict[ChallengeIcon, Callable[[GameEngine], bool]] | None:
        return None
    
    def get_tests(self) -> list[Action] | None:
        return None
    
    def get_exhaust_abilities(self) -> list[Action] | None:
        return None
    
    def get_listeners(self) -> list[EventListener] | None:
        return None

    def has_hand_based_listener(self) -> bool:
        """
        Returns True if this card establishes listeners while in hand.
        Used to identify response moments that can't be played proactively.
        """
        listeners = self.get_listeners()
        if not listeners:
            return False

        # Response moments are moments that have listeners
        # Non-response moments don't establish listeners
        return self.has_type(CardType.MOMENT) and len(listeners) > 0

    def get_play_targets(self, state: GameState) -> list[Card] | None:
        """
        Returns valid targets for playing this card, or None if no targeting required.
        Override in cards that need targeting when played.
        """
        return None # Default: no targeting required

    def can_be_played(self, engine: GameEngine) -> bool:
        """
        Universal check for whether this card can be played right now.
        Checks energy cost (and potentially additional costs in the future).

        Note: Does NOT check for valid targets - EBR allows playing cards
        even if they have no effect on the gamestate.

        Used by:
        - provide_play_options() to filter non-response moments
        - EventListener.active field to filter response moments
        """
        # Check energy cost
        cost = self.get_current_energy_cost()
        if cost is not None and self.aspect:
            if engine.state.ranger.energy[self.aspect] < cost:
                return False  # Can't afford

        # NOTE: We do NOT check for valid targets - EBR allows playing cards
        # even if they have no effect on the gamestate

        return True

    def play(self, engine: GameEngine, effort: int = 0, target: Card | None = None) -> None:
        """
        Play this card from hand. Behavior depends on CardType:
        - GEAR: Goes into play in Player Area, enters_play triggers
        - MOMENT: Resolves effect, then discards
        - ATTACHMENT: Attaches to target, enters_play triggers
        - ATTRIBUTE: Raises error (cannot be played, only committed)
        - BEING (ranger): Goes into play Within Reach, enters_play triggers

        Energy costs are paid first for all card types that have them.
        """
        if self.has_type(CardType.ATTRIBUTE):
            raise RuntimeError(f"Attributes cannot be played, only committed during tests!")

        # Pay energy cost FIRST (for all card types that have energy costs)
        cost = self.get_current_energy_cost()
        if cost is not None and cost > 0 and self.aspect:
            success, error = engine.state.ranger.spend_energy(cost, self.aspect)
            if not success:
                engine.add_message(error or "Cannot afford to play this card!")
                return

        # Now execute type-specific play logic
        if self.has_type(CardType.GEAR):
            engine.state.ranger.hand.remove(self)
            engine.state.areas[Area.PLAYER_AREA].append(self)
            self.enters_play(engine, Area.PLAYER_AREA, None)
            engine.add_message(f"Played {self.title} into Player Area.")

            # Enforce equip value limit (5 total)
            engine.enforce_equip_limit()

        elif self.has_type(CardType.ATTACHMENT):
            if target is None:
                engine.add_message(f"No attachment target provided; discarding.")
                engine.state.ranger.discard_from_hand(engine, self)
                return
            target_card_area: Area | None = engine.state.get_card_area_by_id(target.id)
            if target_card_area is None:
                #check if it's in an out of play area, which would indicate the attachment is searching
                #it out and putting it into play
                if (target in engine.state.path_deck or
                    target in engine.state.path_discard or
                    target in engine.state.ranger.deck or
                    target in engine.state.ranger.discard or
                    target in engine.state.ranger.fatigue_stack or
                    target in engine.state.ranger.hand):
                    target_card_area = target.starting_area
                else:
                    raise RuntimeError(f"Attachment target is in no area!")
            if target_card_area is None:
                raise RuntimeError(f"Attachment target is in no area!")
            else:
                engine.state.ranger.hand.remove(self)
                self.enters_play(engine, target_card_area, target)
                engine.attach(self, target)
                engine.add_message(f"Played {self.title}, attaching to target.")
            
        elif (self.has_type(CardType.BEING) or self.has_type(CardType.FEATURE)) and CardType.RANGER in self.card_types:
            engine.state.ranger.hand.remove(self)
            engine.state.areas[Area.WITHIN_REACH].append(self)
            self.enters_play(engine, Area.WITHIN_REACH, None)
            engine.add_message(f"Played {self.title} Within Reach.")

        elif self.has_type(CardType.MOMENT):
            # Both response and non-response moments use this path
            engine.state.ranger.discard_from_hand(engine, self)
            self.resolve_moment_effect(engine, effort, target)
            engine.add_message(f"Played {self.title}.")

        else:
            raise RuntimeError(f"Don't know how to play {self.title} with types {self.card_types}")
        
    def resolve_moment_effect(self, engine: GameEngine, effort: int, target: Card | None) -> None:
        """Implemented by both response and non-response moments to execute their on-play effects"""
        raise NotImplementedError(f"{self.title} is a Moment but doesn't implement resolve_moment_effect()!")

    def on_committed(self, engine: GameEngine, action: Action) -> str | None:
        """
        Optional hook called when this card is committed to a test.
        Used primarily by attributes with commit-triggered effects.

        Returns a unique listener ID if an ephemeral listener was registered,
        or None if no listener was registered.

        Override this method to register ephemeral listeners that trigger
        after the test succeeds/fails and then self-remove.
        """
        return None
        
    def get_play_action(self) -> Action | None:
        """
        Returns the Action for playing this card from hand, or None if not playable.
        """
        if self.has_hand_based_listener():
            return None
        
        if self.has_type(CardType.ATTRIBUTE):
            return None
        
        return Action(id=f"{self.id}-play",
                      name=f"Play {self.title}",
                      aspect="",
                      approach="",
                      is_test=False,
                      is_exhaust=False,
                      is_play=True,
                      verb = None,
                      target_provider=self.get_play_targets,
                      on_success=self.play,
                      source_id=self.id,
                      source_title=self.title)

    
    def play_prompt(self, engine: GameEngine, effort: int, context: str = "") -> bool:
        """
        Prompt user to play this card as a response moment.
        Returns True if played, False if declined.
        Used by response moment listeners.

        Mirrors the main loop flow: check playability, select target, prompt, execute.
        """
        # 1. Check if playable (should already be guaranteed by listener's active field)
        if not self.can_be_played(engine):
            return False

        # 2. Prompt to play
        current_cost = self.get_current_energy_cost()
        aspect_str = f"{self.aspect.value}" if self.aspect else ""
        cost_str = f" for {current_cost} {aspect_str}" if current_cost and current_cost > 0 else ""
        prompt = f"Play {self.title}{cost_str}?"
        if context:
            prompt = f"{context}\n{prompt}"

        decision = engine.response_decider(engine, prompt)

        if decision:
            # 3. Decide targets
            target = None
            targets = self.get_play_targets(engine.state)
            if targets is not None and len(targets) > 0:
                # Card needs targeting and has valid targets
                target = engine.card_chooser(engine, targets)
            # 4. Execute play (energy is spent inside play() now)
            self.play(engine, target=target, effort=effort)
            return True

        return False
    
    def exhaust_ability_active(self, token_type: str) -> bool:
        """Many cards have an exhaust ability that spends a unique token off of them
        as a cost. This helper method checks for whether the card is ready and has
        sufficient tokens to pay the cost."""
        return (not self.is_exhausted()) and (self.get_unique_token_count(token_type) > 0)
    
    def get_exhaust_targets(self, state: GameState) -> list[Card] | None:
        """
        Returns valid targets for using an exhaust ability, or None if no targeting required.
        Override in cards whose exhaust abilities require targeting.
        """
        return None # Default: no targeting required
    
    def exhaust_prompt(self, engine: GameEngine, context: str = "") -> bool:
        """
        Prompt user to use an response-like exhaust ability.
        Returns True if acceded, False if declined.
        Used by cards with exhaust abilities that have listeners.
        Does not need to verify exhausted status or token costs; listener system filters that
        """

        # Check for valid targets BEFORE prompting
        targets = self.get_exhaust_targets(engine.state)
        if targets is not None and len(targets) == 0:
            engine.add_message(f"No valid targets; {self.title} cannot be exhausted.")
            return False
        
        """we don't prompt for target selection here for similar reasons as play_prompt"""

        # Now prompt to exhaust
        prompt = f"Exhaust {self.title}?"
        if context:
            prompt = f"{context}\n{prompt}"

        return engine.response_decider(engine, prompt)
        

    def get_constant_abilities(self) -> list[ConstantAbility] | None:
        if self.keywords:
            result: list[ConstantAbility] = []
            for keyword in self.keywords:
                if keyword == Keyword.OBSTACLE:
                    result.append(ConstantAbility(ConstantAbilityType.PREVENT_INTERACTION_PAST,
                                                  self.id,
                                                  lambda _s, _c: self.is_ready()))
                    result.append(ConstantAbility(ConstantAbilityType.PREVENT_TRAVEL,
                                                  self.id,
                                                  lambda _s, _c: self.is_ready()))
                
            return result
        else:
            return None

    def is_exhausted(self) -> bool:
        #TODO: take into account stuff that says to "Treat cards as exhausted"
        return self.exhausted
    
    def is_ready(self) -> bool:
        #TODO: take into account stuff that says to "Treat cards as ready"
        return not self.exhausted
    
    def has_type(self, type: CardType) -> bool:
        return type in self.card_types
    
    def has_keyword(self, keyword: Keyword) -> bool:
        #TODO: take into account keywords added by ConstantAbilities
        return keyword in self.keywords
    
    def has_trait(self, trait: str) -> bool:
        #TODO: take into account added traits from stuff like Trail Makers
        for candidate_trait in self.traits:
            if candidate_trait.casefold() == trait.casefold():
                return True
        return False
    
    def get_progress_threshold(self) -> int | None:
        #TODO: take into account progress threshold modifiers
        return self.progress_threshold
    
    def get_harm_threshold(self) -> int | None:
        #TODO: take into account harm threshold modifiers
        return self.harm_threshold

    def add_unique_tokens(self, token_type: str, amount: int) -> str:
        token_type = token_type.casefold()
        if amount < 0:
            raise ValueError(f"Amount cannot be negative, use remove_unique_tokens instead!")
        if self.has_unique_token_type(token_type):
            self.unique_tokens[token_type] = self.unique_tokens[token_type] + amount
        else:
            self.unique_tokens[token_type] = amount
        return(f"Added {amount} {token_type} token(s) to {self.title}, now at {self.unique_tokens[token_type]}.")
    
    def remove_unique_tokens(self, token_type: str, amount: int) -> tuple[int,str]:
        token_type = token_type.casefold()
        if self.has_unique_token_type(token_type):
            amount_removed = min(self.unique_tokens[token_type], amount)
            self.unique_tokens[token_type] = self.unique_tokens[token_type] - amount_removed
            return amount_removed, f"Removed {amount} {token_type} token(s) from {self.title}. Now at {self.unique_tokens[token_type]}."
        else:
            return 0, f"No {token_type} tokens on {self.title}."
    
    def get_unique_token_count(self, token_type: str) -> int:
        token_type = token_type.casefold()
        if self.has_unique_token_type(token_type):
            return self.unique_tokens[token_type]
        else:
            return 0
    
    def has_unique_token_type(self, token_type: str) -> bool:
        token_type = token_type.casefold()
        return token_type in self.unique_tokens.keys()
    
    def has_any_unique_tokens(self) -> bool:
        """Used to check for actual presence of tokens on card"""
        return len(self.unique_tokens) > 0 and any(x > 0 for x in self.unique_tokens.values())
    
    def has_unique_tokens(self) -> bool:
        """Used to check for if card uses unique tokens, regardless of whether it currently has any."""
        return len(self.unique_tokens) > 0
        

    #location only methods
    def do_arrival_setup(self, engine:GameEngine) -> None:
        """Implemented by locations and executed during Step 5 of Travel or Step 10 of Setup"""
        return None


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
        
    def enters_hand(self, engine: GameEngine) -> list[EventListener]:
        """Called when card enters hand. Shows art description. Override to add listeners."""
        if self.art_description:
            engine.add_message(f"   Art description: {self.art_description}")
        if self.flavor_text:
            engine.add_message(f"   Flavor text: {self.flavor_text}")
        listeners = self.get_listeners()
        if listeners is None:
            return []
        elif self.has_type(CardType.MOMENT):
            return listeners
        else:
            return []

    def enters_play(self, engine: GameEngine, area: Area, action_target: Card | None = None) -> None:
        """Called when card enters play. Adds narrative messages, 
        and can be overridden for enter-play effects, listeners, and in-play ConstantAbilities."""
        """Parameter "action target" is given for cards played with the Play Action, and is otherwise None"""

        #Messaging
        engine.add_message(f"{get_display_id(engine.state.all_cards_in_play(), self)} enters play in {area.value}.")
        if self.art_description:
            engine.add_message(f"   Art description: {self.art_description}")
        if self.has_keyword(Keyword.AMBUSH) and self.starting_area == Area.WITHIN_REACH:
            engine.add_message(f"   {self.title} Ambushes you!")
            engine.state.ranger.fatigue(engine, self.get_current_presence(engine))

        #Set up abilities and listeners
        constant_abilities = self.get_constant_abilities()
        event_listeners = self.get_listeners()
        if constant_abilities:
            engine.register_constant_abilities(constant_abilities)
        if event_listeners:
            engine.register_listeners(event_listeners)
    
    #path card only methods
    def get_current_presence(self, engine: GameEngine) -> int | None:
        if self.presence is not None:
            #first, get just the card's own presence modifiers
            presence_mods = [mod for mod in self.modifiers if mod.target == "presence"]
            #then, we get presence modifiers from Constant Abilities
            presence_mods.extend([ability.modifier for ability in engine.constant_abilities 
                                  if ability.condition_fn(engine.state, self) and ability.modifier is not None])
            #then, we apply modifiers in order of largest minimums first
            sorted_by_mins = sorted(presence_mods, key=lambda m: m.minimum_result, reverse=True)
            current_presence = self.presence
            for mod in sorted_by_mins:
                current_presence = max(mod.minimum_result, current_presence + mod.amount)
            return current_presence
        else:
            return None
    
    def harm_from_predator(self, engine: GameEngine, symbol: ChallengeIcon, harm_target: Card) -> bool:
        """Common challenge effect where an active predator exhausts and adds harm to a harm_target (usually this card)"""
        predators = engine.state.get_cards_by_trait("Predator")
        self_display_id = engine.get_display_id_cached(self)
        harm_target_display_id = engine.get_display_id_cached(harm_target)
        if predators is not None:
            active_predators = [predator for predator in predators if predator.is_ready()]
            if not active_predators:
                engine.add_message(f"Challenge ({symbol.value}) on {self_display_id}: (no active predators in play)")
                return False
            else:
                if len(active_predators)==1:
                    engine.add_message(f"Challenge ({symbol.value}) on {self_display_id}: the active predator in play exhausts itself and harms {harm_target_display_id}:")
                else:
                    engine.add_message(f"Challenge ({symbol.value}) on {self_display_id}: Choose a predator that will exhaust itself and harms {harm_target_display_id}:")
                target_predator = engine.card_chooser(engine, active_predators)
                engine.add_message(target_predator.exhaust())
                target_predator_presence = target_predator.get_current_presence(engine)
                if target_predator_presence is not None:
                    #this should always happen
                    msg = harm_target.add_harm(target_predator_presence)
                    engine.add_message(f"{target_predator.title}: {msg}")
                else:
                    raise RuntimeError("A predator should always have a presence!")
                return True
        else:
            engine.add_message(f"Challenge ({symbol.value}) on {self_display_id}: (no predators in play)")
            return False
    
    def harm_from_prey(self, engine: GameEngine, symbol: ChallengeIcon, harm_target: Card) -> bool:
        """Common challenge effect form where an active prey exhausts and adds harm to a harm_target (usually this card),
        as well as progress to itself."""
        prey_list = engine.state.get_cards_by_trait("Prey")
        self_display_id = engine.get_display_id_cached(self)
        harm_target_display_id = engine.get_display_id_cached(harm_target)
        if prey_list is not None:
            active_prey = [prey for prey in prey_list if prey.is_ready()]
            if not active_prey:
                engine.add_message(f"Challenge ({symbol.value}) on {self_display_id}: (no active prey in play)")
                return False
            else:
                if len(active_prey)==1:
                    engine.add_message(f"Challenge ({symbol.value}) on {self_display_id}: the active prey in play exhausts itself and harms {harm_target_display_id}:")
                else:
                    engine.add_message(f"Challenge ({symbol.value}) on {self_display_id}: Choose a prey that will exhaust itself and harms {harm_target_display_id}:")
                target_prey = engine.card_chooser(engine, active_prey)
                engine.add_message(target_prey.exhaust())
                target_prey_presence = target_prey.get_current_presence(engine)
                if target_prey_presence is not None:
                    #this should always happen
                    msg = harm_target.add_harm(target_prey_presence)
                    engine.add_message(f"{target_prey.title}: {msg}")
                    engine.add_message(target_prey.add_progress(target_prey_presence))
                else:
                    raise RuntimeError("A prey should always have a presence!")
                return True
        else:
            engine.add_message(f"Challenge ({symbol.value}) on {self_display_id}: (no prey in play)")
            return False
        
    def add_progress(self, amount: int) -> str:
        if amount < 0:
            raise ValueError(f"'amount' in add_progress should always be non-negative. Use remove_progress instead.")
        if not self.progress_forbidden:
            self.progress = max(0, self.progress + amount)
            return f"Added {amount} progress to {self.title}. Now has {self.progress} progress."
        else:
            return f"Progress cannot be added to {self.title}!"

    def add_harm(self, amount: int) -> str:
        if amount < 0:
            raise ValueError(f"'amount' in add_harm should always be non-negative. Use remove_harm instead.")
        if not self.harm_forbidden:
            self.harm = max(0, self.harm + amount)
            return f"Added {amount} harm to {self.title}. Now has {self.harm} harm."
        else:
            return f"Harm cannot be added to {self.title}!"

    def remove_progress(self, amount: int) -> tuple[int,str]: #amount of tokens actually removed often matters
        if amount < 0:
            raise ValueError(f"'amount' in remove_progress should always be non-negative. Use add_progress instead.")
        if not self.progress_forbidden:
            amount_removed = min(self.progress, amount)
            self.progress = self.progress - amount_removed
            return amount_removed, f"Removed {amount} progress from {self.title}. Now has {self.progress} progress."
        else:
            return 0, f"Progress cannot exist on {self.title}!"

    def remove_harm(self, amount: int) -> tuple[int, str]: 
        if amount < 0:
            raise ValueError(f"'amount' in remove_harm should always be non-negative. Use add_harm instead.")
        if not self.harm_forbidden:
            amount_removed = min(self.harm, amount)
            self.harm = self.harm - amount_removed
            return amount_removed, f"Removed {amount} harm from {self.title}. Now has {self.harm} harm."
        else:
            return 0, f"Harm cannot exist on {self.title}!"
    
    def exhaust(self) -> str:
        if self.is_exhausted():
            return f"{self.title} is already exhausted."
        else:
            self.exhausted = True
            return f"{self.title} exhausts."
    
    def ready(self, engine: GameEngine) -> str:
        blocker_abilities: list[ConstantAbility] = engine.get_constant_abilities_by_type(ConstantAbilityType.PREVENT_READYING)
        blocker_ids = [blocker_ability.source_card_id for blocker_ability in blocker_abilities if blocker_ability.is_active(engine.state, self)]
        if self.is_ready():
            return f"{self.title} is already ready."
        elif self.attached_to_id in blocker_ids:
            blocker = engine.state.get_card_by_id(self.attached_to_id)
            if blocker is None:
                raise RuntimeError(f"{self.title} has a non-None attached_to_id that refers to no card in play.")
            blocker_display = get_display_id(engine.state.all_cards_in_play(), blocker)
            return f"{self.title} cannot be readied due to {blocker_display}."
        else:
            self.exhausted = False
            return f"{self.title} readies."
        
    def clear_if_threshold(self, state: GameState) -> str | None:
        if self.has_type(CardType.LOCATION):
            return None #locations never clear
        
        prog_threshold = self.get_progress_threshold()
        harm_threshold = self.get_harm_threshold()

        if self.progress_clears_by_ranger_tokens and state.ranger.ranger_token_location==self.id:
            return "progress"
        if self.harm_clears_by_ranger_tokens and state.ranger.ranger_token_location==self.id:
            return "harm"

        if prog_threshold is not None and self.progress >= prog_threshold:
            return "progress"
        if harm_threshold is not None and self.harm >= harm_threshold:
            return "harm"
        return None

    def discard_from_play(self, engine: GameEngine) -> str:
        """
        Remove this card from play and send it to the appropriate discard pile.
        Handles area cleanup and determines correct discard pile based on card type.

        Returns:
            Message describing what happened
        """
        # Handle ranger token if on this card (when ranger token system implemented)
        if engine.state.ranger.ranger_token_location == self.id:
            engine.move_ranger_token_to_role()

        # Recursively discard all attached cards
        for id in list(self.attached_card_ids):
            card = engine.state.get_card_by_id(id)
            if card is None:
                raise RuntimeError(f"Attachment not found!")
            else:
                engine.unattach(card)
                #unattach() already auto-discards attachments
                if not card.has_type(CardType.ATTACHMENT):
                    card.discard_from_play(engine)

        # Remove from area
        for area_cards in engine.state.areas.values():
            if self in area_cards:
                area_cards.remove(self)
                break

        # Determine correct discard pile (polymorphism!)
        if self.has_type(CardType.PATH):
            engine.state.path_discard.append(self)
        elif self.has_type(CardType.RANGER):
            engine.state.ranger.discard.append(self)

        # Weather, Location, and Mission cards never go to a discard pile
            

        # Clean up attachment state
        self.attached_card_ids.clear()
        self.attached_to_id = None

        # Clean up listeners and constant abilities
        engine.remove_constant_abilities_by_id(self.id)
        engine.remove_listeners_by_id(self.id)

        if isinstance(self, FacedownCard):
            original = self.backside
            if original is None:
                raise RuntimeError(f"Facedown cards should have a front side!")
            if original.has_type(CardType.PATH):
                engine.state.path_discard.append(original)
            elif original.has_type(CardType.RANGER):
                engine.state.ranger.discard.append(original)
            return f"{original.title} discarded."
        else:
            return f"{self.title} discarded."

        
    
    def flip(self, engine: GameEngine) -> None:
        current_area = engine.state.get_card_area_by_id(self.id)
        if current_area is None:
            raise RuntimeError(f"Any card that flips should be in an area!")
        if self.backside is None:
            raise RuntimeError(f"All cards should have a backside!")
        
        #can't use discard_from_play because flipping a card facedown retains its tokens/attachments and doesn't go in discard piles
        engine.state.areas[current_area].remove(self)
        engine.remove_constant_abilities_by_id(self.id)
        engine.remove_listeners_by_id(self.id)


        engine.state.areas[current_area].append(self.backside)
        self.backside.progress = self.progress
        self.backside.harm = self.harm
        self.backside.unique_tokens = dict(self.unique_tokens)  # Copy
        self.backside.attached_card_ids = list(self.attached_card_ids)  # Copy
        if isinstance(self.backside, FacedownCard):
            engine.add_message(f"{self.title} flips over facedown.")
        else:
            engine.add_message(f"{self.title} flips over into {self.backside.title}")
            #can't use enters_play because flipping a card faceup technically doesn't have it enter play
            constant_abilities = self.backside.get_constant_abilities()
            event_listeners = self.backside.get_listeners()
            if constant_abilities:
                engine.register_constant_abilities(constant_abilities)
            if event_listeners:
                engine.register_listeners(event_listeners)

    
@dataclass
class FacedownCard(Card):
    def __init__(self, frontside: Card):
        super().__init__(
            title="Facedown Card",
            id=f"{frontside.id}-facedown",
            backside=frontside
            # All other fields use Card's defaults (empty sets, None, etc.)
        )


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
    fatigue_stack: list[Card] = field(default_factory=lambda: cast(list[Card], []))
    energy: dict[Aspect, int] = field(init=False)
    injury: int = 0
    ranger_token_location: str = ""

    def __post_init__(self):
        self.energy = dict(self.aspects)

    def draw_card(self, eng: GameEngine) -> tuple[Card | None, str, bool]:
        """Draw a card from deck to hand.
        Returns (card, message, should_end_day).
        If deck is empty, returns (None, error_message, True)."""
        if len(self.deck) == 0:
            return None, "Cannot draw from empty deck - the day must end!", True
        else:
            drawn: Card = self.deck.pop(0)
            self.hand.append(drawn)
            eng.register_listeners(drawn.enters_hand(eng))
            return drawn, f"You draw a copy of {drawn.title}.", False

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

    def commit_icons(self, approach: Approach, decision: CommitDecision) -> tuple[int, list[int]]:
        total = decision.energy
        valid_indices : list[int] = []
        for idx in decision.hand_indices:
            if not (0 <= idx < len(self.hand)):
                continue
            c: Card = self.hand[idx]
            num_icons = c.approach_icons.get(approach, 0)
            if num_icons:
                total += num_icons
                valid_indices.append(idx)
        return total, valid_indices

    def discard_committed(self, engine: GameEngine, committed_indices: list[int]) -> list[Card]:
        """Discard cards committed to a test and return the list of committed cards"""
        cards_to_discard : list[Card] = []
        for i in sorted(committed_indices, reverse=True):
            cards_to_discard.append(self.hand[i])

        for card in cards_to_discard:
            self.discard_from_hand(engine, card)

        return cards_to_discard

    def discard_from_hand(self, engine: GameEngine, card: Card) -> None:
        """Move a card from hand to discard pile and clean up its listeners"""
        if card in self.hand:
            self.hand.remove(card)
            self.discard.append(card)
            # Remove any listeners associated with this card
            engine.remove_listeners_by_id(card.id)

    def fatigue(self, engine: GameEngine, amount: int | None) -> None:
        """Move top amount cards from ranger deck to top of fatigue pile (one at a time)"""
        if amount is None:
            raise RuntimeError(f"Can't fatigue a ranger by None amount")
        if amount > len(self.deck):
            # Can't fatigue more than remaining deck - end the day
            engine.add_message(f"Ranger needs to suffer {amount} fatigue, but only {len(self.deck)} cards remain in deck.")
            engine.add_message("Cannot fatigue from empty deck - the day must end!")
            engine.end_day()
            return

        for _ in range(amount):
            card = self.deck.pop(0)  # Take from top of deck
            self.fatigue_stack.insert(0, card)  # Insert at top of fatigue pile

        if amount > 0:
            engine.add_message(f"Ranger suffers {amount} fatigue.")

    def soothe(self, engine: GameEngine, amount: int) -> None:
        """Move top amount cards from fatigue pile to hand"""
        cards_to_soothe = min(amount, len(self.fatigue_stack))
        if cards_to_soothe > 0:
            engine.add_message(f"Ranger soothes {cards_to_soothe} fatigue.")
        for _ in range(cards_to_soothe):
            card = self.fatigue_stack.pop(0)  # Take from top of fatigue pile
            self.hand.append(card)  # Add to hand
            engine.register_listeners(card.enters_hand(engine))
            engine.add_message(f"   {card.title} is added to your hand.")
    
    def injure(self, engine: GameEngine) -> None:
        """
        Apply 1 injury to the ranger.
        - Discard entire fatigue pile
        - Increment injury counter
        - If injury reaches 3, end the day
        TODO: Add Lingering Injury card to deck when taking 3rd injury
        """
        # Discard all fatigue
        fatigue_count = len(self.fatigue_stack)
        if fatigue_count > 0:
            self.discard.extend(self.fatigue_stack)
            self.fatigue_stack.clear()
            engine.add_message(f"Ranger discards {fatigue_count} fatigue from injury.")

        # Increment injury counter
        self.injury += 1
        engine.add_message(f"Ranger suffers 1 injury (now at {self.injury} injury).")

        # Check for third injury
        if self.injury >= 3:
            engine.add_message("Ranger has taken 3 injuries - the day must end!")
            # TODO: Add "Lingering Injury" card to ranger's deck permanently
            engine.end_day()

@dataclass
class GameState:
    ranger: RangerState
    role_card: Card = field(default_factory=lambda: Card()) #pointer to a card that always exists in the Player Area
    location: Card = field(default_factory=lambda: Card()) #pointer to a card that always exists in the Surroundings
    weather: Card = field(default_factory=lambda: Card()) #pointer to a card that always exists in the Surroundings
    challenge_deck: ChallengeDeck = field(default_factory=lambda: ChallengeDeck())
    areas: dict[Area, list[Card]] = field(
        default_factory=lambda: cast(
            dict[Area, list[Card]], 
            {area: [] for area in Area}
        )
    )
    day_number: int = 1
    round_number: int = 1
    # Path deck for Phase 1 draws
    path_deck: list[Card] = field(default_factory=lambda: cast(list[Card], []))
    path_discard: list[Card] = field(default_factory=lambda: cast(list[Card], []))
    

    def __post_init__(self) -> None:
        self.ranger.ranger_token_location=self.role_card.id #ranger token begins on the Role Card
        if self.role_card not in self.areas[Area.PLAYER_AREA]:
            self.areas[Area.PLAYER_AREA].append(self.role_card)

    #Card getter methods

    def all_cards_in_play(self) -> list[Card]:
        """Get all cards across all areas"""
        return [card for cards in self.areas.values() for card in cards]
    
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
        all_cards = (self.all_cards_in_play() + 
                     self.path_deck + 
                     self.path_discard +
                     self.ranger.hand + 
                     self.ranger.discard + 
                     self.ranger.deck + 
                     self.ranger.fatigue_stack)
        return next((c for c in all_cards if c.id == card_id), None)
    
    def get_card_area_by_id(self, card_id: str | None) -> Area | None:
        """Get a card's current area by its instance ID"""
        for area in self.areas:
            for card in self.areas[area]:
                if card.id == card_id:
                    return area
        return None
    
    def get_cards_by_title(self, title: str) -> list[Card] | None:
        """Get all in-play cards of a given title"""
        results: list[Card] = []
        for area in self.areas:
            for card in self.areas[area]:
                if card.title == title:
                    results.append(card)
        if results:
            return results
        else:
            return None
    
    def get_cards_by_trait(self, trait: str) -> list[Card] | None:
        """Get all in-play cards with a given trait"""
        results: list[Card] = []
        for area in self.areas:
            for card in self.areas[area]:
                for curr_trait in card.traits: #TODO: take into account added traits from cards like Trail Marker
                    if trait.casefold() == curr_trait.casefold():
                        results.append(card)
                
        if results:
            return results
        else:
            return None

    def get_cards_between_ranger_and_target(self, target: Card) -> list[Card]:
        """Get all cards that are 'between' the ranger and a target in the given area.
        Returns cards in order from closest to farthest."""
        between: list[Card] = []
        target_area = self.get_card_area_by_id(target.id)
        
        # Cards attached to role are ALWAYS between (all areas)
        attached_ids = self.role_card.attached_card_ids
        for id in attached_ids:
            card = self.get_card_by_id(id)
            if card is None:
                raise RuntimeError(f"Card attached to role does not exist!")
            else:
                between.append(card)
        
        if target_area == Area.WITHIN_REACH:
            #role attachments already added above
            pass
        elif target_area == Area.ALONG_THE_WAY:
            # Role attachments + Within Reach
            between.extend(self.areas[Area.WITHIN_REACH])
        elif target_area == Area.SURROUNDINGS:
            # Role attachments + Within Reach + Along the Way
            between.extend(self.areas[Area.WITHIN_REACH])
            between.extend(self.areas[Area.ALONG_THE_WAY])
        
        return between


# Action system: derived from state; executed by engine.

@dataclass
class Action:
    id: str  # stable identifier for the action option
    name: str  # human-readable label
    aspect: Aspect | str  # required energy type (if is_test), str for non-test actions like Rest
    approach: Approach | str  # legal approach icons to commit (if is_test), str for non-test actions
    is_test: bool = True
    is_exhaust: bool = False #for "Exhaust:" abilities
    is_play: bool = False #for playing cards
    verb: Optional[str] = None  # action verb (e.g. "Traverse", "Connect", "Hunt") for game effects that care
    # If the action requires a target, provide candidate Card targets based on state
    target_provider: Optional[Callable[[GameState], list['Card'] | None]] = None
    # Computes difficulty for the chosen target (or state)
    difficulty_fn: Callable[[GameEngine, Optional[Card]], int] = lambda _s, _t: 1
    # Effects
    on_success: Callable[[GameEngine, int, Optional[Card]], None] = lambda _s, _e, _t: None
    on_fail: Optional[Callable[[GameEngine, int, Optional[Card]], None]] = lambda _s, _e, _t: None
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
    """For Response abilities and other game effects that trigger before/when/after another effect"""
    event_type: EventType
    active: Callable[[GameEngine, Card | None], bool]  # Check if this listener should trigger (energy, tokens, targets, etc.)
    effect_fn: Callable[[GameEngine, int], int]
    source_card_id: str
    timing_type: TimingType
    test_type: str | None = None #"Traverse", "Connect", etc.

@dataclass
class ConstantAbility:
    """A continuous/passive ability that modifies game rules while active.
    Caller of condition_fn responsible for the ability's behavior"""
    ability_type: ConstantAbilityType
    source_card_id: str

    # Condition function: determines when this ability is "active"
    # Returns True if the ability should currently apply
    condition_fn: Callable[[GameState, Card], bool]

    modifier: ValueModifier | None = None

    # Optional: human-readable description for debugging
    description: str = ""

    def is_active(self, state: GameState, card: Card) -> bool:
        return self.condition_fn(state, card)