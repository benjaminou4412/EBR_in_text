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
  -To implement a top-level CampaignGuide entry:
    -clear_type == None indicates a default entry (typically enters_play for path cards and arrival setup for Locations)
    -returns True if the associated card gets discarded on a particular resolution route. For a top-level entry this typically means returning the result of a sub-level call
  -To implement a sub-level CampaignGuide entry:
    -generally no additional routing
    -return True if the associated card gets discarded; False if it stays in play



A living checklist. Roughly prioritized.


- Implement missions
  -Implement Biscuit Delivery
    -Currently functioning:
      -Biscuit delivery enters play during setup and sets up a listener for its objective
      -this objective properly triggers when you travel while hy pimpot is in play
      -as part of resolving the corresponding campaign entry, biscuit delivery flips into biscuit basket and is equipped to the ranger
    -still to do:
      -implement and enforce biscuit delivery's campaign guide entry overrides for Quisi, Hy, etc.
      -implement Lone Tree Station and have Biscuit Delivery's listener only active when the current location is Lone Tree Station
      -check equip slots when Biscuit Basket is equipped
      -Implement Biscuit Basket (currently mostly unimplemented)
- Implement save/load/autosave
- Implement full Travel map
- Implement fully rules-compliant faceup/facedown cards
  - https://thelivingvalley.earthbornegames.com/docs/rules_glossary/F/facedown_cards/
  - https://thelivingvalley.earthbornegames.com/docs/rules_glossary/A/attach
- automatic keyword loading from JSON
- implement multi-target tests
  - need to have interaction/obstacle rules consider multiple interaction targets
    (the farthest target is the one true interaction target)
- Implement...the entire rest of the game.


