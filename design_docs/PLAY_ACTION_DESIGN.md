# Ranger Card Play System - Design Document

## Overview

This document describes the architecture for implementing the "Play" action that allows players to play Ranger cards from hand. This includes Gear, Moments (both response and non-response), Attachments, and Ranger Beings.

## Core Principles

1. **Reuse the Action class** - Playing cards is semantically an "action" just like testing, so we reuse the existing `Action` class with `is_test=False`
2. **Card-level polymorphism** - Different card types behave differently when played, handled via CardType checking
3. **Universal play() method** - All ranger cards use the same `play()` method; response vs non-response distinction happens at the filtering level
4. **Target validation in cards** - Cards specify their own valid targets via `target_provider` in their play Actions

## Architecture Components

### 1. Action Class (models.py)

The existing `Action` class already supports both tests and play actions:
- `is_test` flag distinguishes between test actions and play actions
- `target_provider` provides valid targets (can be None for no targeting)
- `on_success` executes the effect (for tests: on success; for plays: always)
- `on_fail` only relevant for tests

**No changes needed** - Action class already supports this use case.

### 2. Card.play() Method (models.py)

Universal method that handles all card types when played from hand:

```python
def play(self, engine: GameEngine, target_id: str | None = None) -> str:
    """
    Play this card from hand. Behavior depends on CardType:
    - GEAR: Goes into play in Player Area, enters_play triggers
    - MOMENT: Resolves effect via get_play_action().on_success, then discards
    - ATTACHMENT: Attaches to target_id, enters_play triggers
    - ATTRIBUTE: Raises error (cannot be played, only committed)
    - BEING (ranger): Goes into play Within Reach, enters_play triggers

    Returns a message describing what happened.
    """
    if CardType.ATTRIBUTE in self.card_types:
        raise RuntimeError(f"Attributes cannot be played, only committed during tests!")

    if CardType.GEAR in self.card_types:
        engine.state.ranger.hand.remove(self)
        engine.state.areas[Area.PLAYER_AREA].append(self)
        self.enters_play(engine, Area.PLAYER_AREA)
        #in theory, starting tokens are already set up by the json loader
        return f"Played {self.title} into Player Area."

    elif CardType.ATTACHMENT in self.card_types:
        if target_id is None:
            raise RuntimeError(f"Attachments require a target!")
        engine.state.ranger.hand.remove(self)
        self.attach_to(engine, target_id)
        return f"Played {self.title}, attaching to target."

    elif CardType.BEING in self.card_types and CardType.RANGER in self.card_types:
        engine.state.ranger.hand.remove(self)
        engine.state.areas[Area.WITHIN_REACH].append(self)
        self.enters_play(engine, Area.WITHIN_REACH)
        return f"Played {self.title} Within Reach."

    elif CardType.MOMENT in self.card_types:
        # Both response and non-response moments use this path
        engine.state.ranger.hand.remove(self)
        play_action = self.get_play_action()
        if play_action:
            play_action.on_success(engine, 0, None)  # Execute the moment's effect
        engine.state.ranger.discard.append(self)
        return f"Played {self.title}."

    else:
        raise RuntimeError(f"Don't know how to play {self.title} with types {self.card_types}")
```

### 3. Card.get_play_action() Method (models.py)

Cards that can be played proactively override this to return an Action:

```python
def get_play_action(self) -> Action | None:
    """
    Returns the Action for playing this card from hand, or None if not playable.
    Only Moments override this - Gear/Attachments/Beings don't need Actions.
    """
    return None
```

**Example implementation** (in a Moment card):

```python
def get_play_action(self) -> Action | None:
    return Action(
        id=f"play-{self.id}",
        name=f"Play {self.title} [{self.energy_cost}]",
        is_test=False,
        target_provider=self._get_play_targets,  # or None if no targeting
        on_success=self._on_play_effect,
        source_id=self.id,
        source_title=self.title
    )

def _get_play_targets(self, state: GameState) -> list[Card]:
    """Returns valid targets for this moment"""
    # e.g., "Add 2 tokens to an equipped gear"
    return [c for c in state.areas[Area.PLAYER_AREA]
            if c.has_type(CardType.GEAR)]

def _on_play_effect(self, engine: GameEngine, effort: int, target: Card | None) -> None:
    """The actual effect when this moment is played"""
    # Execute the card's effect
    pass
```

### 4. Card.play_prompt() Method (models.py)

Helper for response moments to prompt the user and handle energy payment:

```python
def play_prompt(self, engine: GameEngine, context: str = "") -> bool:
    """
    Prompt user to play this card as a response moment.
    Returns True if played, False if declined.
    Used by response moment listeners.
    """
    if engine.state.ranger.energy < self.energy_cost:
        return False  # Can't afford

    prompt = f"Play {self.title} [{self.energy_cost}]?"
    if context:
        prompt = f"{context}\n{prompt}"

    if engine.response_decider(prompt):
        engine.spend_energy(self.energy_cost)
        msg = self.play(engine)  # Calls play(), which executes the effect
        engine.add_message(msg)
        return True
    return False
```

**Note:** Response moments like Walk With Me would use this in their listener callbacks:

```python
# In WalkWithMe
def get_listeners(self) -> list[EventListener]:
    return [EventListener(
        EventType.TEST_FAIL,
        lambda eng, action, effort: self.play_prompt(eng, f"Test failed with {effort} effort."),
        self.id,
        TimingType.AFTER
    )]
```

### 5. Play Action in main.py

New action option that allows playing cards from hand:

```python
def action_play(state: GameState, engine: GameEngine) -> None:
    """Play a card from hand"""
    # Build list of playable cards
    playable_cards: list[Card] = []

    for card in state.ranger.hand:
        # Can't afford?
        if card.energy_cost > state.ranger.energy:
            continue

        # Attributes can't be played
        if CardType.ATTRIBUTE in card.card_types:
            continue

        # Response moments (cards with hand-based listeners) can't be played proactively
        # They're only playable when their trigger occurs
        if card.has_hand_based_listener():  # New helper method
            continue

        # For moments, check if they have a play action
        if CardType.MOMENT in card.card_types:
            play_action = card.get_play_action()
            if play_action is None:
                continue  # This moment can't be played proactively

            # Check if moment has valid targets (if targeting required)
            if play_action.target_provider:
                targets = play_action.target_provider(state)
                if not targets:
                    continue  # No valid targets

        # For attachments, check if there are valid targets
        if CardType.ATTACHMENT in card.card_types:
            # TODO: Need to determine valid attachment targets
            # For now, assume all attachments need targets and skip if none
            pass

        playable_cards.append(card)

    if not playable_cards:
        engine.add_message("No playable cards in hand.")
        return

    # Let player choose which card to play
    chosen_card = engine.card_chooser(engine, playable_cards)

    # Handle targeting if needed
    target_id = None
    if CardType.MOMENT in chosen_card.card_types:
        play_action = chosen_card.get_play_action()
        if play_action and play_action.target_provider:
            targets = play_action.target_provider(state)
            target = engine.card_chooser(engine, targets)
            target_id = target.id
    elif CardType.ATTACHMENT in chosen_card.card_types:
        # Get valid attachment targets
        # TODO: Implement attachment targeting
        pass

    # Pay energy cost
    engine.spend_energy(chosen_card.energy_cost)

    # Play the card
    msg = chosen_card.play(engine, target_id)
    engine.add_message(msg)
```

### 6. Helper Method: has_hand_based_listener() (models.py)

```python
def has_hand_based_listener(self) -> bool:
    """
    Returns True if this card establishes listeners while in hand.
    Used to identify response moments that can't be played proactively.
    """
    listeners = self.get_listeners()
    if not listeners:
        return False

    # Response moments register listeners for events they're not involved in
    # (e.g., Walk With Me listens for TEST_FAIL but isn't the card being tested)
    # This is a heuristic - might need refinement
    return any(listener.source_card_id == self.id for listener in listeners)
```

## Card Type Behavior Summary

| Card Type           | Playable?        | Needs Targeting? | Destination        | Uses get_play_action()? |
|-----------          |-----------       |------------------|-------------       |-------------------------|
| Gear                | Yes              | No               | Player Area        | No                      |
| Non-response Moment | Yes              | Maybe            | Discard            | Yes                     |
| Response Moment     | Only via trigger | Maybe            | Discard            | Yes (for effect)        |
| Attachment          | Yes              | Yes              | Attached to target | No                      |
| Ranger Being        | Yes              | No               | Within Reach       | No                      |
| Attribute           | No               | N/A              | N/A                | No                      |

## Flow Diagrams

### Non-Response Moment Flow
```
1. Player chooses "Play" action in main.py
2. main.py filters playable cards (energy, no response moments, etc.)
3. Player selects moment card
4. If moment needs targeting:
   a. Call moment.get_play_action().target_provider() to get valid targets
   b. Player selects target
5. main.py pays energy cost
6. main.py calls moment.play(engine, target_id)
7. play() removes from hand, calls get_play_action().on_success(), discards
```

### Response Moment Flow
```
1. Event occurs (e.g., test fails)
2. Listener callback triggers � calls moment.play_prompt(engine, context)
3. play_prompt() checks energy, prompts user
4. If user agrees:
   a. play_prompt() pays energy
   b. play_prompt() calls moment.play(engine)
   c. play() removes from hand, calls get_play_action().on_success(), discards
```

### Gear/Being Flow
```
1. Player chooses "Play" action in main.py
2. main.py filters playable cards
3. Player selects gear/being
4. main.py pays energy cost
5. main.py calls card.play(engine)
6. play() removes from hand, puts in area, calls enters_play()
```

### Attachment Flow
```
1. Player chooses "Play" action in main.py
2. main.py filters playable cards and checks for valid targets
3. Player selects attachment
4. Player selects target
5. main.py pays energy cost
6. main.py calls attachment.play(engine, target_id)
7. play() removes from hand, calls attach_to(target_id)
```

## Key Design Decisions

1. **Action reuse**: We reuse the `Action` class because playing cards IS an action, and it already has all the infrastructure we need (targeting, callbacks, etc.)

2. **play() is universal**: The `play()` method doesn't distinguish between response and non-response moments - that distinction happens at the filtering level (response moments aren't offered as options in the Play action)

3. **Energy payment location**: Energy is paid BEFORE calling `play()`, either by main.py (proactive plays) or by `play_prompt()` (response plays)

4. **Targeting in cards**: Target validation logic lives in the card subclass via `target_provider`, maintaining the principle that you can understand a card by reading its class

5. **get_play_action() only for Moments**: Gear, Beings, and Attachments don't need Actions - they're handled directly in `play()`. Only Moments need Actions to package their effects.

## TODO Items

2. Implement attachment targeting logic
6. Implement at least one example of each:
   - Gear card with play functionality
   - Non-response Moment card
   - Attachment card
7. Add Play action to main.py action menu
8. Handle "no gamestate change" filtering (future TODO - complex edge cases)

## Testing Strategy

1. Test `play()` method for each card type (Gear, Moment, Attachment, Being)
2. Test response moment triggering via `play_prompt()`
3. Test non-response moment via Play action
4. Test energy payment and affordability filtering
5. Test targeting for moments and attachments
6. Test that attributes cannot be played
7. Test that response moments aren't offered in Play action
