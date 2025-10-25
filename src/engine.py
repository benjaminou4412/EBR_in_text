from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Optional
from .models import (
    GameState, Action, CommitDecision, RangerState, Card, ChallengeIcon,
    Aspect, Approach, Zone, CardType, EventType, TimingType, EventListener,
    MessageEvent, Keyword
)
from .challenge import draw_challenge
from .utils import get_display_id


@dataclass
class ChallengeOutcome:
    base_effort: int
    modifier: int
    difficulty: int
    symbol: ChallengeIcon
    resulting_effort: int
    success: bool




class GameEngine:
    def __init__(self,
                  state: GameState,
                  challenge_drawer: Callable[[], tuple[int, ChallengeIcon]] = draw_challenge,
                  card_chooser: Callable[[GameEngine, list[Card]], Card] | None = None,
                  response_decider: Callable[[GameEngine, str],bool] | None = None):
        self.state = state
        self.draw_challenge = challenge_drawer
        self.card_chooser = card_chooser if card_chooser is not None else self._default_chooser
        self.response_decider = response_decider if response_decider is not None else self._default_decider
        # Event listeners and message queue (game engine concerns, not board state)
        self.listeners: list[EventListener] = []
        self.message_queue: list[MessageEvent] = []
        self.day_has_ended: bool = False

    def _default_chooser(self, _engine: 'GameEngine', choices: list[Card]) -> Card:  # noqa: ARG002
        """Placeholder default; tests should pass in more sophisticated choosers, runtime should prompt player"""
        return choices[0]

    def _default_decider(self, _engine: 'GameEngine', _prompt: str) -> bool:  # noqa: ARG002
        """Default: always play responses (for tests)"""
        return True

    def commit_icons(self, ranger: RangerState, approach: Approach, decision: CommitDecision) -> tuple[int, list[int]]:
        total = decision.energy
        valid_indices : list[int] = []
        for idx in decision.hand_indices:
            if not (0 <= idx < len(ranger.hand)):
                continue
            c: Card = ranger.hand[idx]
            num_icons = c.approach_icons.get(approach, 0)
            if num_icons:
                total += num_icons
                valid_indices.append(idx)
        return total, valid_indices

    def discard_from_hand(self, card: Card) -> None:
        """Move a card from hand to discard pile and clean up its listeners"""
        if card in self.state.ranger.hand:
            self.state.ranger.hand.remove(card)
            self.state.ranger.discard.append(card)
            # Remove any listeners associated with this card
            self.remove_listener_by_id(card.id)

    def discard_committed(self, ranger: RangerState, committed_indices: list[int]) -> None:
        """Discard cards committed to a test"""
        cards_to_discard : list[Card] = []
        for i in sorted(committed_indices, reverse=True):
            cards_to_discard.append(ranger.hand[i])
            del ranger.hand[i]

        for card in cards_to_discard:
            ranger.discard.append(card)
            # Remove any listeners associated with committed cards
            self.remove_listener_by_id(card.id)
    
    def get_valid_targets(self, action: Action) -> list[Card]:
        """Get valid targets for an action, respecting Obstacle keyword.

        Applies game rule filters (Obstacle, etc.) to the raw candidate list.
        """
        if not action.target_provider:
            return []

        raw_candidates = action.target_provider(self.state)
        return self._filter_by_obstacles(raw_candidates)

    def _filter_by_obstacles(self, candidates: list[Card]) -> list[Card]:
        """Filter candidates to exclude cards past the nearest Obstacle"""
        from .models import Keyword, Zone

        # Find closest ready Obstacle
        closest_obstacle_zone = None
        for zone in [Zone.WITHIN_REACH, Zone.ALONG_THE_WAY, Zone.SURROUNDINGS]:
            cards_in_zone = self.state.zones[zone]
            if any(Keyword.OBSTACLE in card.keywords and not card.exhausted
                   for card in cards_in_zone):
                closest_obstacle_zone = zone
                break

        if closest_obstacle_zone is None:
            return candidates  # No obstacles

        # Determine valid zones (at/before obstacle)
        valid_zones = {Zone.PLAYER_AREA}
        if closest_obstacle_zone == Zone.WITHIN_REACH:
            valid_zones.add(Zone.WITHIN_REACH)
        elif closest_obstacle_zone == Zone.ALONG_THE_WAY:
            valid_zones.update([Zone.WITHIN_REACH, Zone.ALONG_THE_WAY])
        elif closest_obstacle_zone == Zone.SURROUNDINGS:
            valid_zones.update([Zone.WITHIN_REACH, Zone.ALONG_THE_WAY, Zone.SURROUNDINGS])

        return [card for card in candidates
                if self.state.get_card_zone_by_id(card.id) in valid_zones]

    def interaction_fatigue(self, ranger: RangerState, target: Card) -> None:
        """Apply fatigue from cards between ranger and target"""
        cards_between = self.state.get_cards_between_ranger_and_target(target)
        target_zone : Zone | None = self.state.get_card_zone_by_id(target.id)
        if target_zone is None:
            raise RuntimeError(f"Something went horribly wrong, this target has no zone.")
        
        # TODO:Filter out Friendly cards
        fatiguing_cards = [card for card in cards_between if card.exhausted == False and Keyword.FRIENDLY not in card.keywords]
        self.add_message(f"Interacting with {get_display_id(self.state.all_cards_in_play(), target)} in {target_zone.value}...")
        if not fatiguing_cards:
            self.add_message(f"No cards between you and the target; no interaction fatigue.")
            return
        else:
            self.add_message(f"Each ready, non-Friendly card between you and the target fatigues you:")
            for card in fatiguing_cards:
                self.add_message(f"    {get_display_id(self.state.all_cards_in_play(), card)} fatigues you.")
                curr_presence = card.get_current_presence()
                if curr_presence is not None:
                    self.fatigue_ranger(ranger, curr_presence)
                else:
                    raise RuntimeError(f"Something has gone horribly wrong; this card should have a presence.")
                    
    def initiate_test(self, action: Action, state: GameState, target_id: str | None):
        """Show player relevant information before decisions are made during a test"""
        # Get display strings for aspect/approach
        aspect_str = action.aspect.value if isinstance(action.aspect, Aspect) else action.aspect
        approach_str = action.approach.value if isinstance(action.approach, Approach) else action.approach  

        # Show player Test Step 1 information
        self.add_message(f"[{action.verb}] test initiated of aspect [{aspect_str}] and approach [{approach_str}].")
        self.add_message(f"This test is of difficulty {action.difficulty_fn(state,target_id)}.")
        self.add_message(f"Step 1: You suffer fatigue from each ready card between you and your interaction target.")
        if target_id is not None:
            target = self.state.get_card_by_id(target_id)
            if target is not None: #should always be not-None
                self.interaction_fatigue(self.state.ranger, target)
        else:
            self.add_message(f"This test has no target; interaction fatigue skipped.")
        # Show player test Step 2 information
        self.add_message(f"Step 2: Commit effort from your energy pool, approach icons in hand, and other sources.")
        

    def perform_action(self, action: Action, decision: CommitDecision, target_id: Optional[str]) -> ChallengeOutcome:
        # Non-test actions (e.g., Rest) skip challenge + energy
        if not action.is_test:
            action.on_success(self, 0, target_id)
            return ChallengeOutcome(difficulty=0, base_effort=0, modifier=0, symbol=ChallengeIcon.SUN, resulting_effort=0, success=True)

        r = self.state.ranger        

        # At this point, action.aspect/approach are guaranteed to be enums (not str) since is_test=True
        aspect = action.aspect if isinstance(action.aspect, Aspect) else Aspect.AWA  # type guard
        approach = action.approach if isinstance(action.approach, Approach) else Approach.EXPLORATION  # type guard
        if r.energy.get(aspect, 0) < decision.energy:
            raise RuntimeError(f"Insufficient energy for {aspect}")
        r.energy[aspect] -= decision.energy

        # Step 2: Commit effort in the form of energy tokens and approach icons. TODO: Commit effort from other sources.

        base_effort, committed = self.commit_icons(r, approach, decision)

        # Discard committed cards immediately after committing
        self.discard_committed(r, committed)

        # Step 3: Apply modifiers. TODO: Take into account modifiers from non-challenge-card sources.

        mod, symbol = self.draw_challenge()
        effort = max(0, base_effort + mod)
        difficulty = action.difficulty_fn(self.state, target_id)
        self.add_message(f"Step 3: Draw a challenge card and apply modifiers.")
        self.add_message(f"You drew: [{aspect.value}]{mod:+d}, symbol [{symbol.upper()}]")



        # Step 4: Determine success or failure and apply results. TODO: notify "after you succeed/fail" listeners
        self.add_message(f"Step 4: Determine success or failure and apply results.")
        self.add_message(f"Total effort committed: {base_effort}")
        self.add_message(f"Test difficulty: {difficulty}")
        success = effort >= difficulty

        if success:
            self.add_message(f"Result: {base_effort} + ({mod:d}) = {effort} >= {difficulty}")
            self.add_message(f"Test succeeded!")
            action.on_success(self, effort, target_id)
            self.trigger_listeners(EventType.TEST_SUCCEED, TimingType.AFTER, action, effort)

        else:
            self.add_message(f"Result: {base_effort} + ({mod:d}) = {effort} < {difficulty}")
            self.add_message(f"Test failed!")
            if action.on_fail:
                action.on_fail(self, target_id)

        cleared : list[Card]= []
        cleared.extend(self.check_and_process_clears())

        for cleared_card in cleared:
            self.add_message(f"{cleared_card.title} cleared!")

        cleared.clear()
        # Step 5:  Resolve Challenge effects (dynamically from active cards)
        # TODO: Future challenge resolution features:
        #   - When multiple cards in the same zone have challenge effects, player chooses the order
        #   - If new cards enter play during challenge resolution, their effects should trigger
        #   - If cards move zones during challenge resolution and become active, their effects should trigger
        self.add_message(f"Step 5: Resolve [{symbol.upper()}] challenge effects, if any.")
        challenge_zones : list[Zone] = [
            Zone.SURROUNDINGS,     # Weather, Location, Mission
            Zone.ALONG_THE_WAY,    # TODO: player chooses order within zone
            Zone.WITHIN_REACH,     # TODO: player chooses order within zone
            Zone.PLAYER_AREA,      # TODO: player chooses order within zone
        ]

        nonzero_challenges = False
        for zone in challenge_zones:
            for card in self.state.zones[zone]:
                if not card.exhausted:
                    # Get handlers directly from the card (always current)
                    handlers = card.get_symbol_handlers()
                    if handlers and symbol in handlers:
                        nonzero_challenges = True
                        handlers[symbol](self)
        if not nonzero_challenges:
            self.add_message("No challenge effects resolved.")
        cleared.extend(self.check_and_process_clears())

        for cleared_card in cleared:
            self.add_message(f"{cleared_card.title} cleared!")

        return ChallengeOutcome(
            difficulty=difficulty, 
            base_effort=base_effort, 
            modifier=mod, symbol=symbol, 
            resulting_effort=effort, 
            success=success
        )

        
    
    #check all in-play cards' clear thresholds and moves them to discard when thresholds are met
    #return list of cleared entities to display
    def check_and_process_clears(self) -> list[Card]:
        to_clear : list[Card]= []
        
        for zone in self.state.zones:
            remaining : list[Card] = []
            for card in self.state.zones[zone]:
                if CardType.PATH in card.card_types:
                    clear_type = card.clear_if_threshold()
                    if clear_type == "progress":
                        #todo: check for clear-by-progress entry
                        to_clear.append(card)
                    elif clear_type == "harm":
                        #todo: check for clear-by-harm entry
                        to_clear.append(card)
                    else:
                        remaining.append(card)
                else:
                    remaining.append(card)
            self.state.zones[zone] = remaining
        self.state.path_discard.extend(to_clear)
        return to_clear
    
    # Listener management methods

    def trigger_listeners(self, event_type: EventType, timing_type: TimingType, action: Action, effort: int):
        triggered : list[EventListener]= []
        for listener in self.listeners:
                if listener.event_type == event_type and listener.timing_type == timing_type:
                    if action.verb is not None and listener.test_type is not None:
                        if action.verb.lower() == listener.test_type.lower():
                            triggered.append(listener)
        for listener in triggered:
            listener.effect_fn(self, effort)
    

    def add_listener(self, listener: EventListener) -> None:
        """Add an event listener to the active listener registry"""
        self.listeners.append(listener)

    def remove_listener_by_id(self, id: str) -> None:
        """Remove listener by source card ID"""
        target = None
        for listener in self.listeners:
            if listener.source_card_id == id:
                target = listener
        if target is not None:
            self.listeners.remove(target)

    def reconstruct_listeners(self) -> None:
        """Rebuild listener registry from current game state (for loading saved games)"""
        self.listeners.clear()

        # Listeners from cards in hand
        for card in self.state.ranger.hand:
            listener = card.enters_hand()
            if listener:
                self.listeners.append(listener)

        # Future: listeners from cards in play with enters_play()

    # Message management methods

    def add_message(self, message: str) -> None:
        """Add a message to the message queue"""
        new_message = MessageEvent(message)
        self.message_queue.append(new_message)

    def get_messages(self) -> list[MessageEvent]:
        """Get copy of current message queue"""
        return self.message_queue.copy()

    def clear_messages(self) -> None:
        """Clear the message queue"""
        self.message_queue.clear()

    #Gamestate manipulation methods

    def move_card(self, card_id : str | None, target_zone : Zone) -> None:
        """Move a card from its current zone to a target zone"""
        target_card : Card | None = self.state.get_card_by_id(card_id)
        current_zone : Zone | None = self.state.get_card_zone_by_id(card_id)
        if current_zone is not None and target_card is not None:
            self.state.zones[current_zone].remove(target_card)
            self.state.zones[target_zone].append(target_card)
            self.add_message(f"{get_display_id(self.state.all_cards_in_play(), target_card)} moves to {target_zone.value}.")

    def fatigue_ranger(self, ranger: RangerState, amount: int) -> None:
        """Move top amount cards from ranger deck to top of fatigue pile (one at a time)"""
        if amount > len(ranger.deck):
            # Can't fatigue more than remaining deck - end the day
            self.add_message(f"Ranger needs to suffer {amount} fatigue, but only {len(self.state.ranger.deck)} cards remain in deck.")
            self.add_message("Cannot fatigue from empty deck - the day must end!")
            self.end_day()
            return

        for _ in range(amount):
            card = ranger.deck.pop(0)  # Take from top of deck
            ranger.fatigue_pile.insert(0, card)  # Insert at top of fatigue pile

        if amount > 0:
            self.add_message(f"Ranger suffers {amount} fatigue.")

    def soothe_ranger(self, ranger: RangerState, amount: int) -> None:
        """Move top amount cards from fatigue pile to hand"""
        cards_to_soothe = min(amount, len(ranger.fatigue_pile))
        for _ in range(cards_to_soothe):
            card = ranger.fatigue_pile.pop(0)  # Take from top of fatigue pile
            ranger.hand.append(card)  # Add to hand
        if cards_to_soothe > 0:
            self.add_message(f"Ranger soothes {cards_to_soothe} fatigue.")

    def end_day(self) -> None:
        """End the current day (game over for this session)"""
        self.day_has_ended = True
        self.add_message(f"Day {self.state.day_number} has ended after {self.state.round_number} rounds.")
        self.add_message("Thank you for playing!")

    # Round/Phase helpers
    def phase1_draw_paths(self, count: int = 1):
        self.add_message(f"Begin Phase 1: Draw Path Cards")
        for _ in range(count):
            if not self.state.path_deck:
                #TODO: set up path discard, and reshuffle path discard into deck when deck is empty
                break
            card = self.state.path_deck.pop(0)
            if card.starting_area is not None:
                self.state.zones[card.starting_area].append(card)
                self.add_message(f"Drew {get_display_id(self.state.all_cards_in_play(),card)}, which enters play {card.starting_area.value}.")
            else:
                raise ValueError("Path card drawn is missing a starting area.")


    def phase4_refresh(self):
        self.add_message(f"Begin Phase 4: Refresh")
        #Step 1: Suffer 1 Fatigue per injury
        if (self.state.ranger.injury > 0):
            self.add_message(f"Your ranger is injured, so you suffer fatigue.")
            self.fatigue_ranger(self.state.ranger, self.state.ranger.injury)
        #Step 2: Draw 1 Ranger Card
        listener, draw_message, should_end_day = self.state.ranger.draw_card()
        if should_end_day:
            if draw_message:
                self.add_message(draw_message)
            self.end_day()
            return
        if listener is not None:
            self.add_listener(listener)
        if draw_message is not None:
            self.add_message(draw_message)
        #Step 3: Refill energy
        self.state.ranger.refresh_all_energy()
        self.add_message("Your energy is restored.")
        #Step 4: Resolve Refresh effects (TODO)
        self.add_message("Todo: resolve Refresh abilities.")
        #Step 5: Ready all cards in play
        for zone in self.state.zones:
            for card in self.state.zones[zone]:
                card.exhausted = False
        self.add_message("All cards in play Ready.")
