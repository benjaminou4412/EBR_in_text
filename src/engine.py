from __future__ import annotations
import random
from dataclasses import dataclass
from typing import Callable, Optional, Any, cast
from .models import (
    GameState, Action, CommitDecision, RangerState, Card, ChallengeIcon,
    Aspect, Approach, Area, CardType, EventType, TimingType, EventListener,
    MessageEvent, Keyword, ConstantAbility, ConstantAbilityType
)

from .utils import get_display_id
from .decks import build_woods_path_deck, select_three_random_valley_cards, get_new_location, get_current_weather


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
                  card_chooser: Callable[[GameEngine, list[Card]], Card] | None = None,
                  response_decider: Callable[[GameEngine, str],bool] | None = None,
                  order_decider: Callable[[GameEngine, Any, str], Any] | None = None,
                  option_chooser: Callable[[GameEngine, list[str], str | None], str] | None = None):
        self.state = state
        self.card_chooser = card_chooser if card_chooser is not None else self._default_chooser
        self.response_decider = response_decider if response_decider is not None else self._default_decider
        self.order_decider = order_decider if order_decider is not None else self._default_order_decider
        self.option_chooser = option_chooser if option_chooser is not None else self._default_option_chooser
        # Event listeners and message queue (game engine concerns, not board state)
        self.listeners: list[EventListener] = []
        self.constant_abilities: list[ConstantAbility] = []
        self.message_queue: list[MessageEvent] = []
        self.day_has_ended: bool = False
        # Display ID cache for challenge resolution (maintains consistent IDs even if cards clear)
        self._display_id_cache: dict[str, str] = {}
        # Test outcome tracking (for edge case challenge effects like "A Perfect Day")
        # These are set during test resolution and available during challenge effect resolution
        self.last_test_added_progress: bool = False
        self.last_test_target: Card | None = None
        self.reconstruct()

    def _default_chooser(self, _engine: 'GameEngine', choices: list[Card]) -> Card:  # noqa: ARG002
        """Placeholder default; tests should pass in more sophisticated choosers, runtime should prompt player"""
        return choices[0]

    def _default_decider(self, _engine: 'GameEngine', _prompt: str) -> bool:  # noqa: ARG002
        """Default: always play responses (for tests)"""
        return True

    def _default_order_decider(self, _engine: 'GameEngine', items: Any, _prompt: str) -> Any:  # noqa: ARG002
        """Default: maintain current order (no rearrangement)"""
        return items

    def _default_option_chooser(self, _engine: 'GameEngine', options: list[str], _prompt: str | None) -> str:  # noqa: ARG002
        """Default: choose first option (for tests)"""
        return options[0]

    def get_display_id_cached(self, card: Card) -> str:
        """Get display ID for a card, using cache if available (during challenge resolution).

        This ensures consistent display IDs even if cards get cleared mid-resolution.
        Falls back to live computation if cache is empty.
        """
        if self._display_id_cache and card.id in self._display_id_cache:
            return self._display_id_cache[card.id]
        # Fallback to live computation
        return get_display_id(self.state.all_cards_in_play(), card)

    def will_challenge_resolve(self, card: Card, icon: ChallengeIcon) -> bool:
        """
        Dry run a challenge effect to see if it would resolve (change gamestate).
        Returns True if the challenge would resolve, False otherwise.

        Creates a deep copy of the engine, swaps in deterministic decision makers,
        and executes the challenge to see if it returns True.

        IMPORTANT: Retrieves the handler from the COPIED card, not the original,
        to prevent the dry run from modifying the original game state.
        """
        import copy

        # Create a deep copy of the engine for the dry run
        dry_run_engine = copy.deepcopy(self)

        # Replace all user interaction callbacks with deterministic defaults
        # This prevents prompting the player during the dry run
        dry_run_engine.card_chooser = dry_run_engine._default_chooser
        dry_run_engine.response_decider = dry_run_engine._default_decider
        dry_run_engine.order_decider = dry_run_engine._default_order_decider
        dry_run_engine.option_chooser = dry_run_engine._default_option_chooser

        # Clear messages to avoid pollution
        dry_run_engine.message_queue = []

        # Get the COPIED version of the card to prevent modifying original state
        copied_card = dry_run_engine.state.get_card_by_id(card.id)
        if not copied_card:
            # Card not found in copy, assume it would resolve (safe default)
            return True

        # Get handlers from the COPIED card
        handlers = copied_card.get_challenge_handlers()
        if not handlers or icon not in handlers:
            return False

        # Run the challenge effect from the copied card
        try:
            would_resolve = handlers[icon](dry_run_engine)
            return would_resolve
        except Exception:
            # If it errors during dry run, assume it would resolve
            # (Better to prompt unnecessarily than skip a valid effect)
            return True

    

    

    
    
    def get_valid_targets(self, action: Action) -> list[Card]:
        """Get valid targets for an action, respecting Obstacle and Friendly keyword.

        Applies game rule filters (Obstacle, etc.) to the raw candidate list.
        """
        if not action.target_provider:
            return []

        raw_candidates = action.target_provider(self.state)

        if raw_candidates is None:
            return []

        if action.is_test:
            raw_candidates = self.filter_by_obstacles(raw_candidates)

        if raw_candidates is None:
            return []

        source_card = self.state.get_card_by_id(action.source_id)

        if source_card and source_card.has_trait("Weapon"):
            raw_candidates = [c for c in raw_candidates if not c.has_keyword(Keyword.FRIENDLY)]

        return raw_candidates

    def filter_by_obstacles(self, candidates: list[Card]) -> list[Card] | None:
        """Filter candidates to exclude cards past the nearest Obstacle"""
        # Gather active ConstantAbilities that block interaction
        ability_ids = [ability.source_card_id for ability in self.constant_abilities 
                     if ability.ability_type==ConstantAbilityType.PREVENT_INTERACTION_PAST
                     and ability.is_active(self.state, Card())] #card input unused; pass in empty card dummy
        ability_areas : list[Area]= []
        for id in ability_ids:
            area = self.state.get_card_area_by_id(id)
            if area is None:
                raise RuntimeError(f"ability_id points to no Card object!")
            else:
                ability_areas.append(area)
        # Find closest ready Obstacle
        closest_obstacle_area = None
        for area in [Area.WITHIN_REACH, Area.ALONG_THE_WAY, Area.SURROUNDINGS]:
            if area in ability_areas:
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

        all_cards = self.state.all_cards_in_play()
        fatiguing_cards = [card for card in cards_between if card.is_ready() and not card.has_keyword(Keyword.FRIENDLY)]
        target_display_id = get_display_id(all_cards, target)
        self.add_message(f"Target: {target_display_id} in {target_area.value}. Checking interaction fatigue...")
        if not fatiguing_cards:
            self.add_message(f"No cards between you and the target; no interaction fatigue.")
            return
        else:
            self.add_message(f"Each ready, non-Friendly card between you and the target fatigues you:")
            for card in fatiguing_cards:
                card_display_id = get_display_id(all_cards, card)
                self.add_message(f"    {card_display_id} fatigues you.")
                curr_presence = card.get_current_presence(self)
                if curr_presence is not None:
                    self.state.ranger.fatigue(self, curr_presence)
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
        self.add_message(f"This test is of difficulty {action.difficulty_fn(self,target_card)}.")
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

        # Step 2: Commit effort in the form of energy tokens and approach icons..

        base_effort, committed = self.state.ranger.commit_icons(approach, decision)

        base_effort = base_effort + self.trigger_listeners(EventType.PERFORM_TEST, TimingType.WHEN, action, base_effort)

        # Discard committed cards immediately after committing
        self.state.ranger.discard_committed(self, committed)

        # Step 3: Apply modifiers. TODO: Take into account modifiers from non-challenge-card sources.
        self.add_message(f"Step 3: Draw a challenge card and apply modifiers.") 
        challenge_card_drawn = self.state.challenge_deck.draw_challenge_card(self)
        mod, icon = challenge_card_drawn.mods[aspect], challenge_card_drawn.icon
        effort = max(0, base_effort + mod)
        difficulty = action.difficulty_fn(self, target_card)
        self.add_message(f"You drew: [{aspect.value}]{mod:+d}, symbol [{icon.upper()}]")



        # Step 4: Determine success or failure and apply results.
        self.add_message(f"Step 4: Determine success or failure and apply results.")
        self.add_message(f"Total effort committed: {base_effort}")
        self.add_message(f"Test difficulty: {difficulty}")
        success = effort >= difficulty

        # Track test outcome and target (for edge case challenge effects)
        self.last_test_added_progress = False
        self.last_test_target = target_card
        progress_before = target_card.progress if target_card else 0

        if success:
            self.add_message(f"Result: {base_effort} + ({mod:d}) = {effort} >= {difficulty}")
            self.add_message(f"Test succeeded!")
            action.on_success(self, effort, target_card)
            self.trigger_listeners(EventType.TEST_SUCCEED, TimingType.AFTER, action, effort)

            # Check if progress was added to the target
            if target_card:
                self.last_test_added_progress = (target_card.progress > progress_before)

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
        #   - If new cards enter play during challenge resolution, their effects should trigger
        #   - If cards move areas during challenge resolution and become active, their effects should trigger
        self.add_message(f"Step 5: Resolve [{icon.upper()}] challenge effects, if any.")
        challenge_areas : list[Area] = [
            Area.SURROUNDINGS,     # Weather, Location, Mission
            Area.ALONG_THE_WAY,
            Area.WITHIN_REACH,
            Area.PLAYER_AREA,
        ]

        zero_challenge_effects_resolved = True
        already_resolved_ids: list[tuple[str, ChallengeIcon]] = []
        #track which cards had a challenge effect resolve so they don't resolve again

        # Pre-compute display IDs for all cards before any effects resolve
        # This ensures consistent naming even if cards get cleared mid-resolution
        all_cards_snapshot = self.state.all_cards_in_play()
        self._display_id_cache.clear()
        for card in all_cards_snapshot:
            self._display_id_cache[card.id] = get_display_id(all_cards_snapshot, card)

        for area in challenge_areas:
            # Collect cards with challenge effects for this symbol in this area
            cards_with_effects: list[Card] = []
            for card in self.state.areas[area]:
                if card.is_ready():
                    handlers = card.get_challenge_handlers()
                    if handlers and icon in handlers and (card.id, icon) not in already_resolved_ids:
                        cards_with_effects.append(card)

            # Filter to only effects that would actually resolve
            # This prevents prompting the player to order effects that won't change the gamestate
            resolvable_cards: list[Card] = []
            for card in cards_with_effects:
                if self.will_challenge_resolve(card, icon):
                    resolvable_cards.append(card)

            # If multiple cards have resolvable effects in the same area, let player choose order
            if len(resolvable_cards) > 1:
                resolvable_cards = cast(list[Card], self.order_decider(self, resolvable_cards,
                    f"Choose order to resolve {icon.upper()} challenge effects in {area.value}"))

            # Resolve effects in the chosen order
            for card in resolvable_cards:
                handlers = card.get_challenge_handlers()
                if handlers and icon in handlers and (card.id, icon) not in already_resolved_ids:
                    resolved = handlers[icon](self)
                    if resolved:
                        already_resolved_ids.append((card.id, icon))
                        zero_challenge_effects_resolved = False
                    cleared.extend(self.check_and_process_clears())

        if zero_challenge_effects_resolved:
            self.add_message("No challenge effects resolved.")

        for cleared_card in cleared:
            self.add_message(f"{cleared_card.title} cleared!")

        # Clear the display ID cache after challenge resolution is complete
        self._display_id_cache.clear()

        return ChallengeOutcome(
            difficulty=difficulty,
            base_effort=base_effort,
            modifier=mod, symbol=icon,
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
                if card.has_type(CardType.PATH):
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
            blockers = [blocker for blocker in self.constant_abilities 
                        if blocker.ability_type == ConstantAbilityType.PREVENT_RANGER_TOKEN_MOVE
                        and blocker.condition_fn(self.state, card)]
            if blockers:
                blocker_card = self.state.get_card_by_id(blockers[0].source_card_id)
                if blocker_card is None:
                    raise RuntimeError(f"Card blocking ranger token movement does not exist!")
                
                blocker_display = get_display_id(self.state.all_cards_in_play(), blocker_card)
                self.add_message(f"Your Ranger token cannot move due to {blocker_display}")
                return False
            else:
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

    def trigger_listeners(self, event_type: EventType, timing_type: TimingType, action: Action | None, effort: int) -> int:
        """Trigger all listeners that are active, pasing in effort for effects that need it.
        Returns an integer for effects that involve a variable result amount, such as committed effort."""
        triggered : list[EventListener]= []
        for listener in self.listeners:
                if listener.event_type == event_type and listener.timing_type == timing_type:
                    if action is not None:
                        if action.verb is not None and listener.test_type is not None:
                            if action.verb.casefold() == listener.test_type.casefold():
                                triggered.append(listener)
                        else:
                            raise RuntimeError(f"A listener that triggers during an action should have a verb and test_type to compare.")
                    else:
                        #trigger happens outside of tests, no need to compare
                        triggered.append(listener)

        # If multiple listeners trigger simultaneously, let player choose order
        if len(triggered) > 1:
            triggered = cast(list[EventListener], self.order_decider(self, triggered,
                f"Choose order to resolve {event_type.value} triggers."))

        committed_effort = 0
        for listener in triggered:
            if listener.active(self):  # Pass engine to check playability/activation
                committed_effort = committed_effort + listener.effect_fn(self, effort)

        return committed_effort #ignored by listener consumers who don't care about effort
    

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
        """Move a card from its current area to a target area. Returns whether it actually moved.

        When a card moves, all of its attachments (and recursive attachments) move with it.
        Cards that are attached to other cards cannot move independently.
        """
        target_card : Card | None = self.state.get_card_by_id(card_id)
        current_area : Area | None = self.state.get_card_area_by_id(card_id)
        if target_card is not None:
            target_display_id = get_display_id(self.state.all_cards_in_play(), target_card)
            if target_area==current_area:
                self.add_message(f"{target_display_id} already in {target_area.value}.")
                return False
            if target_card.attached_to_id is not None:
                #cards attached to other cards cannot move independently
                self.add_message(f"{target_display_id} cannot move because it is attached to something else.")
                return False
            if current_area is not None:
                # Move the card itself
                self.state.areas[current_area].remove(target_card)
                self.state.areas[target_area].append(target_card)
                self.add_message(f"{target_display_id} moves to {target_area.value}.")

                # Recursively move all attachments
                self._move_attachments_recursively(target_card, target_area)

                curr_presence = target_card.get_current_presence(self)
                if target_area == Area.WITHIN_REACH and target_card.has_keyword(Keyword.AMBUSH) and curr_presence is not None:
                    self.add_message(f"...and Ambushes you!")
                    self.state.ranger.fatigue(self, curr_presence)
                return True
        return False

    def _move_attachments_recursively(self, card: Card, target_area: Area) -> None:
        """Helper method to recursively move all attachments when a card moves."""
        for attached_id in card.attached_card_ids:
            attached_card = self.state.get_card_by_id(attached_id)
            if attached_card is None:
                continue

            current_area = self.state.get_card_area_by_id(attached_id)
            if current_area is not None and current_area != target_area:
                # Move the attachment
                self.state.areas[current_area].remove(attached_card)
                self.state.areas[target_area].append(attached_card)
                attached_display_id = get_display_id(self.state.all_cards_in_play(), attached_card)
                self.add_message(f"  {attached_display_id} (attached) moves to {target_area.value}.")

                # Recursively move this attachment's attachments
                self._move_attachments_recursively(attached_card, target_area)

    

    def enforce_equip_limit(self) -> None:
        """
        Enforce the 5 equip value limit for gear in Player Area.
        Prompts player to discard gear until total equip value <= 5.
        """
        MAX_EQUIP = 5

        # Get all gear in Player Area
        gear_in_play = [c for c in self.state.areas[Area.PLAYER_AREA] if c.has_type(CardType.GEAR)]

        # Calculate total equip value
        total_equip = sum(g.get_current_equip_value() or 0 for g in gear_in_play)

        # Prompt to discard until within limit
        while total_equip > MAX_EQUIP:
            self.add_message(f"Total equip value is {total_equip}/{MAX_EQUIP}. You must discard gear to reduce it.")

            # Get gear that can be discarded
            discardable_gear = [g for g in gear_in_play
                               if g.get_current_equip_value() is not None and (g.get_current_equip_value() or 0) > 0]

            if not discardable_gear:
                # Edge case: no gear with equip value (shouldn't happen)
                self.add_message("No gear with equip value to discard!")
                break

            # Prompt player to choose gear to discard
            to_discard = self.card_chooser(self, discardable_gear)

            # Discard the chosen gear
            equip_val = to_discard.get_current_equip_value()
            to_discard.discard_from_play(self)
            self.add_message(f"Discarded {to_discard.title} (equip value {equip_val}).")

            # Recalculate
            gear_in_play = [c for c in self.state.areas[Area.PLAYER_AREA] if c.has_type(CardType.GEAR)]
            total_equip = sum(g.get_current_equip_value() or 0 for g in gear_in_play)

        if total_equip <= MAX_EQUIP:
            self.add_message(f"Total equip value is now {total_equip}/{MAX_EQUIP}.")

    def end_day(self) -> None:
        """End the current day (game over for this session)"""
        self.day_has_ended = True
        self.add_message(f"Day {self.state.day_number} has ended after {self.state.round_number} rounds.")
        self.add_message("Thank you for playing!")

    def draw_path_card(self, target_card: Card | None) -> None:
        """Draw one path card and put it into play, reshuffling path discard if necessary"""
        """If target_card parameter is given, put it into play without drawing from path deck."""
        if target_card is None:
            if not self.state.path_deck:
                self.add_message(f"Path deck empty; shuffling in path discard.")
                random.shuffle(self.state.path_discard)
                self.state.path_deck.extend(self.state.path_discard)
                self.state.path_discard.clear()
            card = self.state.path_deck.pop(0)
            if card.starting_area is not None:
                    self.state.areas[card.starting_area].append(card)
                    card.enters_play(self, card.starting_area)
            else:
                raise AttributeError("Path card drawn is missing a starting area.")
        else:
            card = target_card
            if card.starting_area is not None:
                    self.state.areas[card.starting_area].append(card)
                    card.enters_play(self, card.starting_area)
            else:
                raise AttributeError("Path card drawn is missing a starting area.")

    def scout_cards(self, deck: list[Card], count: int) -> None:
        """Scout X cards from a deck: look at top X cards, then place each on top or bottom in any order.

        The scouting process:
        1. Look at the top X cards
        2. Sort them one-by-one into "top" and "bottom" piles
        3. Order the "top" pile (first card will be closest to top of deck)
        4. Order the "bottom" pile (first card will be closest to bottom of deck)
        5. Reconstruct deck: remaining cards + bottom pile + top pile

        Args:
            deck: The deck to scout from (typically path_deck or ranger.deck)
            count: Number of cards to scout
        """
        if count <= 0:
            return

        # Can't scout more cards than exist in the deck
        actual_count = min(count, len(deck))
        if actual_count == 0:
            self.add_message("No cards to scout.")
            return

        # Step 1: Look at top X cards
        scouted_cards = deck[:actual_count]
        self.add_message(f"Scouting {actual_count} cards from deck:")
        for card in scouted_cards:
            self.add_message(f"   {card.title}")

        # Step 2: Sort cards into "top" and "bottom" piles one at a time
        top_pile: list[Card] = []
        bottom_pile: list[Card] = []

        for card in scouted_cards:
            place_on_top = self.response_decider(self,
                f"Place '{card.title}' on TOP of deck? (No = place on BOTTOM) (y/n)")
            if place_on_top:
                top_pile.append(card)
            else:
                bottom_pile.append(card)

        # Step 3: Order the top pile (if more than one card)
        if len(top_pile) > 1:
            top_pile = cast(list[Card], self.order_decider(self, top_pile,
                "Order cards for TOP of deck (first choice will be drawn first)"))

        # Step 4: Order the bottom pile (if more than one card)
        if len(bottom_pile) > 1:
            bottom_pile = cast(list[Card], self.order_decider(self, bottom_pile,
                "Order cards for BOTTOM of deck (first choice will be farthest from bottom; last choice will be bottom)"))

        # Step 5: Reconstruct the deck
        # Remove all scouted cards from the deck
        for card in scouted_cards:
            deck.remove(card)

        # Add bottom pile to end of remaining deck (in order, first card goes closest to bottom)
        deck.extend(bottom_pile)

        # Add top pile to beginning of deck (in reverse, so first card ends up on top)
        for card in reversed(top_pile):
            deck.insert(0, card)

        self.add_message(f"Scout complete: {len(top_pile)} cards on top, {len(bottom_pile)} cards on bottom.")

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

    def resolve_fatiguing_keyword(self):
        fatiguing_cards: list[Card] = []
        for area in self.state.areas:
            for card in self.state.areas[area]:
                if card.has_keyword(Keyword.FATIGUING):
                    fatiguing_cards.append(card)
        for card in fatiguing_cards:
            if not card.is_exhausted():
                self.add_message(f"{card.title} fatigues you, due to the Fatiguing keyword.")
                curr_presence = card.get_current_presence(self)
                self.state.ranger.fatigue(self, curr_presence)

    # Round/Phase helpers
    def phase1_draw_paths(self, count: int = 1):
        self.add_message(f"Begin Phase 1: Draw Path Cards")
        for _ in range(count):
            self.draw_path_card(None)

    def phase3_travel(self) -> bool: #returns whether day ended by camping
        self.add_message(f"Begin Phase 3: Travel")
        location_progress_threshold = self.state.location.get_progress_threshold()
        travel_blockers = [ability for ability in self.constant_abilities 
                           if ability.ability_type == ConstantAbilityType.PREVENT_TRAVEL
                           and ability.condition_fn(self.state, Card())] #travel blockers don't use Card input
        if travel_blockers:
            travel_blocker_ids: list[str] = []
            for blocker_ability in travel_blockers:
                card = self.state.get_card_by_id(blocker_ability.source_card_id)
                if card is None:
                    raise RuntimeError(f"Travel-blocking id points to no card!")
                else:
                    travel_blocker_ids.append(get_display_id(self.state.all_cards_in_play(),card))
            self.add_message(f"You cannot travel due to: {travel_blocker_ids}")
            return False
        
        if location_progress_threshold is None:
            if self.state.location.progress_clears_by_ranger_tokens:
                if self.state.ranger.ranger_token_location == self.state.location.id:
                    decision = self.response_decider(self, "Your Ranger Token is on the location. Would you like to Travel? (y/n):")
                    if decision: return self.execute_travel()
                else:
                    self.add_message(f"Your Ranger Token is not yet on the location. You may not yet Travel.")
                    return False
            else:
                raise RuntimeError(f"Locations should have a progress threshold!")
        else:
            if self.state.location.progress >= location_progress_threshold:
                decision = self.response_decider(self, "There is sufficient Progress on the Location. Would you like to Travel? (y/n):")
                if decision: return self.execute_travel()
            else:
                self.add_message(f"There is insufficient Progress on the Location. You may not yet Travel.")
                return False
        return False
    def execute_travel(self) -> bool: #returns whether day ended by camping
        #Step 1: Clear Play Area

        self.add_message(f"Step 1: Clear Play Area")

        self.add_message(f"   Discarding all non-persistent path cards from play...")
        for card in [card for card in list(self.state.all_cards_in_play()) 
                     if card.has_type(CardType.PATH) and not card.has_keyword(Keyword.PERSISTENT)]:
            card.discard_from_play(self) #ignore return messages b/c spammy

        self.add_message(f"   Discarding all non-persistent ranger cards from path areas...")
        for area, cards in self.state.areas.items():
            path_areas = [Area.WITHIN_REACH, Area.ALONG_THE_WAY, Area.SURROUNDINGS]
            if area in path_areas:
                ranger_cards = [card for card in cards 
                                if card.has_type(CardType.RANGER) and not card.has_keyword(Keyword.PERSISTENT)]
                for card in list(ranger_cards):
                    card.discard_from_play(self) #ignore return messages b/c spammy

        self.add_message(f"   Returning Path Deck and Path Discard to collection...")
        self.state.path_deck.clear()
        self.state.path_discard.clear()

        #TODO: resolve Missions that instruct you to "travel away" from a location

        #Step 2: Travel to a new location

        #TODO: Render valley map and offer choice
        #For now: fixed choice to single other implemented location
        curr_location = self.state.location
        new_location = get_new_location(curr_location)
        self.state.areas[Area.SURROUNDINGS].append(new_location)
        self.state.areas[Area.SURROUNDINGS].remove(curr_location)
        self.state.location = new_location
        self.add_message(f"Traveled away from {curr_location.title} to {new_location.title}.")
        self.state.location.enters_play(self, Area.SURROUNDINGS)
        #(note: unlike path cards, locations' campaign log entries and arrival setup should not be called with enters_play)
        #(instead, Step 5 of the Travel sequence resolves campaign log entries and arrival setup)

        #Step 3: Decide to camp
        will_camp = self.response_decider(self, f"Will you end the day by camping? (y/n):")
        if will_camp:
            #TODO: take into account ending-day-by-camping to allow reward card swaps
            self.end_day()
            return True
        #Step 4 and 5: Build path deck, arrival setup
        self.arrival_setup(start_of_day=False)

        
        return False
    
    def arrival_setup(self, start_of_day: bool):
        if start_of_day:
            self.add_message(f"Step 5: Set up starting location")
            self.state.location = get_new_location(Card()) #TODO: reference campaign log for start of day location
            self.state.areas[Area.SURROUNDINGS].append(self.state.location)
            self.state.location.enters_play(self, Area.SURROUNDINGS)
            self.add_message(f"Step 6: Set up the weather card")
            self.state.weather = get_current_weather()
            self.state.areas[Area.SURROUNDINGS].insert(0, self.state.weather)
            self.state.weather.enters_play(self, Area.SURROUNDINGS)
            self.add_message(f"Step 7: Set up mission cards (skipped)")
            #TODO: setup missions
            self.add_message(f"Steps 8, 9, and 10: Build path deck, resolve arrival setup, and finishing touches.")


        #load terrain set
        woods_set: list[Card] = build_woods_path_deck() #TODO: path set should vary based on terrain type
        
        
        #TODO: load location set or 3 random Valley NPCs 
        if self.state.location.has_trait("Pivotal"):
            location_set_or_valley: list[Card] = select_three_random_valley_cards() #TODO: replace with pivotal card set
        else:
            location_set_or_valley: list[Card] = select_three_random_valley_cards()
        

        #TODO: check weather, location, and missions for additional cards from "path deck assembly"
        #shuffle everything together

        self.state.path_deck = woods_set + location_set_or_valley
        random.shuffle(self.state.path_deck)

        #TODO: display campaign log entry and resolve decisions; may be overridden by missions
        #TODO: resolve missions to "arrive at" the new location
        self.add_message(f"--- Arrival Setup ---")
        self.state.location.do_arrival_setup(self)

    def phase4_refresh(self):
        self.add_message(f"Begin Phase 4: Refresh")
        #Step 1: Suffer 1 Fatigue per injury
        if (self.state.ranger.injury > 0):
            self.add_message(f"Your ranger is injured, so you suffer fatigue.")
            self.state.ranger.fatigue(self, self.state.ranger.injury)
        #Step 2: Draw 1 Ranger Card
        card, draw_message, should_end_day = self.state.ranger.draw_card(self)
        if should_end_day:
            if draw_message:
                self.add_message(draw_message)
            self.end_day()
            return
        if draw_message:
            self.add_message(draw_message)
        #Step 3: Refill energy
        self.state.ranger.refresh_all_energy()
        self.add_message("Your energy is restored.")
        #Step 4: Resolve Refresh effects (TODO)
        self.add_message("Resolving refresh effects...")
        self.trigger_listeners(EventType.REFRESH, TimingType.WHEN, None, 0)
        #Step 5: Ready all cards in play
        for area in self.state.areas:
            for card in self.state.areas[area]:
                card.ready(self)
        self.add_message("All cards in play Ready.")
