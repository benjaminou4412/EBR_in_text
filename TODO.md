# Earthborne Rangers — Dev TODO

A living checklist. Roughly prioritized.


- Implement at least one Gear + one non-response Moment + 1 attachment, and the Play action
  - Implement:
    - Share in the Valley's Secrets
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


