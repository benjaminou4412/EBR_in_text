from __future__ import annotations
import random
from dataclasses import dataclass
from typing import Callable, Optional
from .models import (
    GameState, Action, CommitDecision, RangerState, Card, ChallengeIcon,
    Aspect, Approach, Area, CardType, EventType, TimingType, EventListener,
    MessageEvent, Keyword, ConstantAbility, ConstantAbilityType
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
        self.constant_abilities: list[ConstantAbility] = []
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
            self.remove_listeners_by_id(card.id)

    def discard_committed(self, ranger: RangerState, committed_indices: list[int]) -> None:
        """Discard cards committed to a test"""
        cards_to_discard : list[Card] = []
        for i in sorted(committed_indices, reverse=True):
            cards_to_discard.append(ranger.hand[i])
            del ranger.hand[i]

        for card in cards_to_discard:
            ranger.discard.append(card)
            # Remove any listeners associated with committed cards
            self.remove_listeners_by_id(card.id)
    
    def get_valid_targets(self, action: Action) -> list[Card]:
        """Get valid targets for an action, respecting Obstacle keyword.

        Applies game rule filters (Obstacle, etc.) to the raw candidate list.
        """
        if not action.target_provider:
            return []

        raw_candidates = action.target_provider(self.state)
        if action.is_test:
            return self.filter_by_obstacles(raw_candidates)
        else:
            return raw_candidates

    def filter_by_obstacles(self, candidates: list[Card]) -> list[Card]:
        """Filter candidates to exclude cards past the nearest Obstacle"""
        from .models import Keyword, Area

        # Find closest ready Obstacle
        closest_obstacle_area = None
        for area in [Area.WITHIN_REACH, Area.ALONG_THE_WAY, Area.SURROUNDINGS]:
            cards_in_area = self.state.areas[area]
            if any(card.has_keyword(Keyword.OBSTACLE) and card.is_ready()
                   for card in cards_in_area):
                closest_obstacle_area = area
                break

        if closest_obstacle_area is None:
            return candidates  # No obstacles

        # Determine valid areas (at/before obstacle)
        valid_areas = {Area.PLAYER_AREA}
        if closest_obstacle_area == Area.WITHIN_REACH:
            valid_areas.add(Area.WITHIN_REACH)
        elif closest_obstacle_area == Area.ALONG_THE_WAY:
            valid_areas.update([Area.WITHIN_REACH, Area.ALONG_THE_WAY])
        elif closest_obstacle_area == Area.SURROUNDINGS:
            valid_areas.update([Area.WITHIN_REACH, Area.ALONG_THE_WAY, Area.SURROUNDINGS])

        return [card for card in candidates
                if self.state.get_card_area_by_id(card.id) in valid_areas]

    def interaction_fatigue(self, ranger: RangerState, target: Card) -> None:
        """Apply fatigue from cards between ranger and target"""
        cards_between = self.state.get_cards_between_ranger_and_target(target)
        target_area : Area | None = self.state.get_card_area_by_id(target.id)
        if target_area is None:
            raise RuntimeError(f"Something went horribly wrong, this target has no area.")

        # TODO:Filter out Friendly cards
        all_cards = self.state.all_cards_in_play()
        fatiguing_cards = [card for card in cards_between if card.is_ready() and not card.has_keyword(Keyword.FRIENDLY)]
        target_display_id = get_display_id(all_cards, target)
        self.add_message(f"Interacting with {target_display_id} in {target_area.value}...")
        if not fatiguing_cards:
            self.add_message(f"No cards between you and the target; no interaction fatigue.")
            return
        else:
            self.add_message(f"Each ready, non-Friendly card between you and the target fatigues you:")
            for card in fatiguing_cards:
                card_display_id = get_display_id(all_cards, card)
                self.add_message(f"    {card_display_id} fatigues you.")
                curr_presence = card.get_current_presence()
                if curr_presence is not None:
                    self.fatigue_ranger(ranger, curr_presence)
                else:
                    raise RuntimeError(f"Something has gone horribly wrong; this card should have a presence.")
                    
    def initiate_test(self, action: Action, state: GameState, target_id: str | None):
        """Show player relevant information before decisions are made during a test"""
        target_card = self.state.get_card_by_id(target_id)
        # Get display strings for aspect/approach
        aspect_str = action.aspect.value if isinstance(action.aspect, Aspect) else action.aspect
        approach_str = action.approach.value if isinstance(action.approach, Approach) else action.approach  

        # Show player Test Step 1 information
        self.add_message(f"[{action.verb}] test initiated of aspect [{aspect_str}] and approach [{approach_str}].")
        self.add_message(f"This test is of difficulty {action.difficulty_fn(state,target_card)}.")
        self.add_message(f"Step 1: You suffer fatigue from each ready card between you and your interaction target.")
        if target_id is not None:
            target = self.state.get_card_by_id(target_id)
            if target is not None: #should always be not-None
                self.interaction_fatigue(self.state.ranger, target)
        else:
            self.add_message(f"This test has no target; interaction fatigue skipped.")
        # Show player test Step 2 information
        self.add_message(f"Step 2: Commit effort from your energy pool, approach icons in hand, and other sources.")
        

    def perform_test(self, action: Action, decision: CommitDecision, target_id: Optional[str]) -> ChallengeOutcome:
        # Non-test actions (e.g., Rest) skip challenge + energy
        target_card: Card | None = self.state.get_card_by_id(target_id)

        if not action.is_test:
            action.on_success(self, 0, target_card)
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
        difficulty = action.difficulty_fn(self.state, target_card)
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
            action.on_success(self, effort, target_card)
            self.trigger_listeners(EventType.TEST_SUCCEED, TimingType.AFTER, action, effort)

        else:
            self.add_message(f"Result: {base_effort} + ({mod:d}) = {effort} < {difficulty}")
            self.add_message(f"Test failed!")
            if action.on_fail:
                action.on_fail(self, effort, target_card)

        cleared : list[Card]= []
        cleared.extend(self.check_and_process_clears())

        for cleared_card in cleared:
            self.add_message(f"{cleared_card.title} cleared!")

        cleared.clear()
        # Step 5:  Resolve Challenge effects (dynamically from active cards)
        # TODO: Future challenge resolution features:
        #   - When multiple cards in the same area have challenge effects, player chooses the order
        #   - If new cards enter play during challenge resolution, their effects should trigger
        #   - If cards move areas during challenge resolution and become active, their effects should trigger
        self.add_message(f"Step 5: Resolve [{symbol.upper()}] challenge effects, if any.")
        challenge_areas : list[Area] = [
            Area.SURROUNDINGS,     # Weather, Location, Mission
            Area.ALONG_THE_WAY,    # TODO: player chooses order within area
            Area.WITHIN_REACH,     # TODO: player chooses order within area
            Area.PLAYER_AREA,      # TODO: player chooses order within area
        ]

        zero_challenge_effects_resolved = True
        for area in challenge_areas:
            for card in self.state.areas[area]:
                if card.is_ready():
                    # Get handlers directly from the card (always current)
                    handlers = card.get_challenge_handlers()
                    if handlers and symbol in handlers:
                        zero_challenge_effects_resolved = False
                        handlers[symbol](self)
                        cleared.extend(self.check_and_process_clears())
        if zero_challenge_effects_resolved:
            self.add_message("No challenge effects resolved.")

        for cleared_card in cleared:
            self.add_message(f"{cleared_card.title} cleared!")

        return ChallengeOutcome(
            difficulty=difficulty, 
            base_effort=base_effort, 
            modifier=mod, symbol=symbol, 
            resulting_effort=effort, 
            success=success
        )

        
    
    def check_and_process_clears(self) -> list[Card]:
        """
        Check all in-play cards' clear thresholds and process clearing.

        By default, cleared cards leave play (discard).
        TODO: Some cards have special clear entries that keep them in play.

        Returns:
            List of cleared cards (for display messages)
        """
        to_clear: list[Card] = []

        for area in self.state.areas:
            for card in self.state.areas[area]:
                if CardType.PATH in card.card_types:
                    clear_type = card.clear_if_threshold(self.state)
                    if clear_type == "progress":
                        # TODO: Check for clear-by-progress entry (on_progress_clear_log)
                        # Some cards might have special effects or stay in play
                        self.add_message(f"{card.title} cleared by progress!")
                        to_clear.append(card)
                    elif clear_type == "harm":
                        # TODO: Check for clear-by-harm entry (on_harm_clear_log)
                        # Some cards might have special effects or stay in play
                        self.add_message(f"{card.title} cleared by harm!")
                        to_clear.append(card)

        # Discard all cleared cards (this removes them from areas)
        for card in to_clear:
            card.discard_from_play(self)

        return to_clear
    
    #Ranger Token manipulation
    def move_ranger_token_to_card(self, card: Card) -> bool:
        """Return whether token actually moved"""
        curr_location = self.state.ranger.ranger_token_location
        curr_card = self.state.get_card_by_id(curr_location)
        if curr_card is None:
            raise RuntimeError(f"The current location id of the ranger token points to no card!")
        else:
            #TODO: add check for effects that prevent ranger token movement
            if curr_location == card.id:
                self.add_message(f"Your Ranger token is already on {card.title}.")
                return False
            else:
                self.state.ranger.ranger_token_location = card.id
                self.add_message(f"Your Ranger token moves from {curr_card.title} to {card.title}.")
                return True

    def move_ranger_token_to_role(self) -> None:
        """Convenience method for when cards are discarded and the Ranger Token returns to the role card"""
        self.move_ranger_token_to_card(self.state.role_card)

    def get_ranger_token_card(self) -> Card:
        card = self.state.get_card_by_id(self.state.ranger.ranger_token_location)
        if card is None:
            raise RuntimeError(f"Ranger token should always be on a card!")
        else:
            return card

    # Listener management methods

    def trigger_listeners(self, event_type: EventType, timing_type: TimingType, action: Action, effort: int):
        triggered : list[EventListener]= []
        for listener in self.listeners:
                if listener.event_type == event_type and listener.timing_type == timing_type:
                    if action.verb is not None and listener.test_type is not None:
                        if action.verb.casefold() == listener.test_type.casefold():
                            triggered.append(listener)
        for listener in triggered:
            listener.effect_fn(self, effort)
    

    def register_listeners(self, listeners: list[EventListener]) -> None:
        """Add an event listener to the active listener registry"""
        self.listeners.extend(listeners)

    def remove_listeners_by_id(self, id: str) -> None:
        """Remove listeners by source card ID"""
        targets: list[EventListener] = []
        for listener in self.listeners:
            if listener.source_card_id == id:
                targets.append(listener)
        if targets:
            for target in targets:
                self.listeners.remove(target)

    def reconstruct(self) -> None:
        """Rebuild listener and constant ability registry from current game state (for loading saved games)"""
        self.listeners.clear()

        # Listeners from cards in hand
        for card in self.state.ranger.hand:
            listeners : list[EventListener] | None = card.enters_hand(self)
            if listeners:
                self.listeners.extend(listeners)

        # TODO: listeners from cards in play with enters_play(), and any other potential source

        self.constant_abilities.clear()

        # Constant abilities from cards in play
        for card in self.state.all_cards_in_play():
            const_abilities : list[ConstantAbility] | None = card.get_constant_abilities()
            if const_abilities:
                self.constant_abilities.extend(const_abilities)

        # TODO: constant abilities from any other sources besides cards in play


    # ConstantAbility management methods
    def register_constant_abilities(self, abilities: list[ConstantAbility]):
        """Register a constant ability from a card entering play"""
        self.constant_abilities.extend(abilities)

    def remove_constant_abilities_by_id(self, card_id: str):
        """Remove all constant abilities from a specific card (for cleanup)"""
        self.constant_abilities = [
            a for a in self.constant_abilities
            if a.source_card_id != card_id
        ]

    def get_constant_abilities_by_type(self, ability_type: ConstantAbilityType) -> list[ConstantAbility]:
        """Get all constsant abilities of a specific type"""
        return [
            ability for ability in self.constant_abilities
            if ability.ability_type == ability_type
        ]
        
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

    def move_card(self, card_id : str | None, target_area : Area) -> bool:
        """Move a card from its current area to a target area. Returns whether it actually moved."""
        target_card : Card | None = self.state.get_card_by_id(card_id)
        current_area : Area | None = self.state.get_card_area_by_id(card_id)
        if target_card is not None:
            target_display_id = get_display_id(self.state.all_cards_in_play(), target_card)
            if target_area==current_area:
                self.add_message(f"{target_display_id} already in {target_area.value}.")
                return False
            if current_area is not None:
                self.state.areas[current_area].remove(target_card)
                self.state.areas[target_area].append(target_card)
                self.add_message(f"{target_display_id} moves to {target_area.value}.")
                curr_presence = target_card.get_current_presence()
                if target_area == Area.WITHIN_REACH and target_card.has_keyword(Keyword.AMBUSH) and curr_presence is not None:
                    self.fatigue_ranger(self.state.ranger, curr_presence)
                return True
        return False

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
        if cards_to_soothe > 0:
            self.add_message(f"Ranger soothes {cards_to_soothe} fatigue.")
        for _ in range(cards_to_soothe):
            card = ranger.fatigue_pile.pop(0)  # Take from top of fatigue pile
            ranger.hand.append(card)  # Add to hand
            self.add_message(f"   {card.title} is added to your hand.")
        

    def injure_ranger(self, ranger: RangerState) -> None:
        """
        Apply 1 injury to the ranger.
        - Discard entire fatigue pile
        - Increment injury counter
        - If injury reaches 3, end the day
        TODO: Add Lingering Injury card to deck when taking 3rd injury
        """
        # Discard all fatigue
        fatigue_count = len(ranger.fatigue_pile)
        if fatigue_count > 0:
            ranger.discard.extend(ranger.fatigue_pile)
            ranger.fatigue_pile.clear()
            self.add_message(f"Ranger discards {fatigue_count} fatigue from injury.")

        # Increment injury counter
        ranger.injury += 1
        self.add_message(f"Ranger suffers 1 injury (now at {ranger.injury} injury).")

        # Check for third injury
        if ranger.injury >= 3:
            self.add_message("Ranger has taken 3 injuries - the day must end!")
            # TODO: Add "Lingering Injury" card to ranger's deck permanently
            self.end_day()

    def end_day(self) -> None:
        """End the current day (game over for this session)"""
        self.day_has_ended = True
        self.add_message(f"Day {self.state.day_number} has ended after {self.state.round_number} rounds.")
        self.add_message("Thank you for playing!")

    def draw_path_card(self) -> None:
        """Draw one path card and put it into play, reshuffling path discard if necessary"""
        if not self.state.path_deck:
            self.add_message(f"Path deck empty; shuffling in path discard.")
            random.shuffle(self.state.path_discard)
            self.state.path_deck.extend(self.state.path_discard)
            self.state.path_discard.clear()
        card = self.state.path_deck.pop(0)
        if card.starting_area is not None:
                self.state.areas[card.starting_area].append(card)
                constant_abilities: list[ConstantAbility] | None = card.enters_play(self, card.starting_area)
                if constant_abilities:
                    self.register_constant_abilities(constant_abilities)
        else:
            raise AttributeError("Path card drawn is missing a starting area.")
        
    def attach(self, to_attach: Card, attachment_target: Card) -> None:
        if to_attach.id == attachment_target.id:
            raise RuntimeError(f"Cannot attach a card to itself!")
        attachment_target.attached_card_ids.append(to_attach.id)
        to_attach.attached_to_id = attachment_target.id
        attachment_target_area = self.state.get_card_area_by_id(attachment_target.id)
        to_attach_area = self.state.get_card_area_by_id(to_attach.id)
        if attachment_target_area is None:
            #it's ok for the to_attach card to not exist in an area, since it might be an Attachment in a player's hand
            raise RuntimeError(f"Attachment target does not exist in an in-play area!")
        else:
            if attachment_target_area != to_attach_area and to_attach_area is not None:
                #only move cards that are actually in play, not attachments in player's hands 
                #(which should have to_attach_area == None)
                self.move_card(to_attach.id, attachment_target_area)
        to_attach_display = get_display_id(self.state.all_cards_in_play(), to_attach)
        attachment_target_display = get_display_id(self.state.all_cards_in_play(), attachment_target)
        self.add_message(f"{to_attach_display} becomes attached to {attachment_target_display}.")
        
    
    def unattach(self, to_unattach: Card) -> None:
        attached_to: Card | None = self.state.get_card_by_id(to_unattach.attached_to_id)
        if attached_to is None:
            raise RuntimeError(f"{to_unattach.id} is attached to nothing!")
        else:
            attached_to.attached_card_ids.remove(to_unattach.id)
            to_unattach.attached_to_id = None
            to_unattach_display = get_display_id(self.state.all_cards_in_play(), to_unattach)
            attached_to_display = get_display_id(self.state.all_cards_in_play(), attached_to)
            self.add_message(f"{to_unattach_display} unattaches from {attached_to_display}.")
            if CardType.ATTACHMENT in to_unattach.card_types:
                to_unattach.discard_from_play(self) #attachments cannot exist in play without being attached
            #generally, cards in play should stay in area of the card they were just attached to


    # Round/Phase helpers
    def phase1_draw_paths(self, count: int = 1):
        self.add_message(f"Begin Phase 1: Draw Path Cards")
        for _ in range(count):
            self.draw_path_card()


    def phase4_refresh(self):
        self.add_message(f"Begin Phase 4: Refresh")
        #Step 1: Suffer 1 Fatigue per injury
        if (self.state.ranger.injury > 0):
            self.add_message(f"Your ranger is injured, so you suffer fatigue.")
            self.fatigue_ranger(self.state.ranger, self.state.ranger.injury)
        #Step 2: Draw 1 Ranger Card
        card, draw_message, should_end_day = self.state.ranger.draw_card()
        if should_end_day:
            if draw_message:
                self.add_message(draw_message)
            self.end_day()
            return
        if draw_message:
            self.add_message(draw_message)
        if card is not None:
            listener = card.enters_hand(self)
            if listener is not None:
                self.register_listeners(listener)
        #Step 3: Refill energy
        self.state.ranger.refresh_all_energy()
        self.add_message("Your energy is restored.")
        #Step 4: Resolve Refresh effects (TODO)
        self.add_message("Todo: resolve Refresh abilities.")
        #Step 5: Ready all cards in play
        for area in self.state.areas:
            for card in self.state.areas[area]:
                card.ready(self)
        self.add_message("All cards in play Ready.")
