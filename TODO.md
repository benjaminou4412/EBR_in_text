# Earthborne Rangers — Dev TODO

API-ish notes:
  -To implement Gear:
    -By default play, cost, and unique token setup logic are automatically handled
    -For non-reactive exhaust abilities, implement get_exhaust_abilities() returning:
      - An Action with is_exhaust=True and appropriate target_provider and on_success callables
    -For reactive exhaust abilities, implement get_listeners() returning:
      - an EventListener with appropriate fields, particularly "active" and "effect_fn" callables
        "active" will usually default to lambda eng: self.exhaust_ability_active(["appropriate unique token name"])
        "effect_fn" will usually need to be implemented in the card subclass and is where the meat of its rules is implemented. It will usually call exhaust_prompt
  -To implement Moments:
    -By default play and cost logic is automatically handled.
    -For non-response moments implement:
      -resolve_moment_effect()
      -if it has targets, get_play_targets()
    -For response moments implement:
      -resolve_moment_effect()
      -if it has targets, get_play_targets()
      -get_listeners() returning:
        -an EventListener with appropriate fields, particularly "active" and "effect_fn" callables:
          -"active" will usually default to lambda eng: self.can_be_played(eng)
          -"effect_fn" will usually default to a simple trigger_play_prompt local helper function passing in an appropriate prompt and calling self.play_prompt



A living checklist. Roughly prioritized.

- Implement at least one Gear + one non-response Moment + 1 attachment, and the Play action
  - Implement:
    - Afforded by Nature
      - Try out multi-target paradigm: one "primary" target that the usual methods use, then secondary
        targets handled by resolve_moment_effects
          -Need to make sure can_be_played overrides and properly takes into account secondary targets
    - A Dear Friend
    - Passionate
  - Handle "no gamestate change" filtering (future TODO - complex edge cases)
- Implement missions, campaign log entries, clear entries, etc.
- Implement Day system and save/load/autosave
- Implement full Travel map
- Implement fully rules-compliant faceup/facedown cards
  - https://thelivingvalley.earthbornegames.com/docs/rules_glossary/F/facedown_cards/
  - https://thelivingvalley.earthbornegames.com/docs/rules_glossary/A/attach
- automatic keyword loading from JSON
- implement multi-target tests
  - need to have interaction/obstacle rules consider multiple interaction targets
    (the farthest target is the one true interaction target)
- Implement...the entire rest of the game.


