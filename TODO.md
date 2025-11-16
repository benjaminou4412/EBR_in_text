# Earthborne Rangers — Dev TODO

A living checklist. Roughly prioritized.


- Implement at least one Gear + one non-response Moment + 1 attachment, and the Play action
  - Have the gear commit effort so we're forced to implement that system too (committing effort from in-play cards in CommitDecision, spending tokens/exhausting as needed)
  - Implement attachment targeting logic
  - Implement:
    - Boundary Sensor
      - Take into account equip slots
    - Share in the Valley's Secrets
      - fix up targeting logic
    - A Dear Friend
    - Passionate
  - Add Play action to main.py action menu
  - Handle "no gamestate change" filtering (future TODO - complex edge cases)
- Implement missions, campaign log entries, clear entries, etc.
- Implement Day system and save/load/autosave
- Implement full Travel map
- Implement fully rules-compliant faceup/facedown cards
  - https://thelivingvalley.earthbornegames.com/docs/rules_glossary/F/facedown_cards/
  - https://thelivingvalley.earthbornegames.com/docs/rules_glossary/A/attach
- automatic keyword loading from JSON
- Implement...the entire rest of the game.


