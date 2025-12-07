from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .engine import GameEngine
    from .models import Card

class CampaignGuide:
    def __init__(self):
        self.entries : dict[str, Callable[['CampaignGuide', 'Card | None', 'GameEngine', str | None], bool]] = {
            "1.01": self.resolve_entry_1_01,
            "47": self.resolve_entry_47, #placeholder to prevent crashing when Hy Pimpot enters play
            "80": self.resolve_entry_80,
            "80.1": self.resolve_entry_80_1,
            "80.2": self.resolve_entry_80_2,
            "80.3": self.resolve_entry_80_3,
            "80.5": self.resolve_entry_80_5,
            "80.6": self.resolve_entry_80_6,
            "85": self.resolve_entry_85, #placeholder to prevent crashing when Calypsa enters play
            "86": self.resolve_entry_86, #placeholder to prevent crashing when The Fundamentalist enters play
            "91": self.resolve_entry_91,
            "91.1": self.resolve_entry_91_1,
            "91.2": self.resolve_entry_91_2,
            "91.3": self.resolve_entry_91_3,
            "91.4": self.resolve_entry_91_4,
            "91.5": self.resolve_entry_91_5,
            "91.6": self.resolve_entry_91_6,
            "91.7": self.resolve_entry_91_7,
            "91.8": self.resolve_entry_91_8
            }
    
    def resolve_entry(self, entry_number: str, source_card: 'Card | None', engine: 'GameEngine', clear_type: str | None) -> bool:
        from .models import ConstantAbilityType
        actual_entry_number = entry_number
        for ability in engine.get_constant_abilities_by_type(ConstantAbilityType.OVERRIDE_CAMPAIGN_ENTRY):
            if ability.condition_fn(engine.state, source_card):
                actual_entry_number = ability.override_entry
                break
                #TODO: Handle multiple overrides. 
        return self.entries[actual_entry_number](source_card, engine, clear_type)
    
    def resolve_entry_1_01(self, source_card: 'Card | None', engine: 'GameEngine', clear_type: str | None) -> bool:
        engine.add_message("")
        engine.add_message("")
        engine.add_message("== Campaign Log Entry 1.01 ==")
        engine.add_message("")
        engine.add_message("--- Story ---")
        engine.add_message("Hy Pimpot places the last juniper biscuit into the basket and hands it to you. " \
        "“There’s no better way to begin a friendship than with a freshly baked biscuit,” he says. " \
        "“The people of White Sky just love meeting new Rangers. They always come bearing treats!” " \
        "Hy Pimpot winks and takes a biscuit for himself.")
        engine.add_message("You shoulder the basket and walk down the trail. As you do, the enticing aroma " \
        "of the biscuits wafts up from the basket. You remember that you haven’t eaten anything since " \
        "breakfast. Your stomach growls. Surely they won’t miss one or two.")
        engine.add_message("")
        engine.add_message("--- Results ---")
        engine.add_message("Flip the BISCUIT DELIVERY mission to the BISCUIT BASKET side.")
        biscuit_delivery = source_card
        biscuit_basket = biscuit_delivery.flip(engine)
        engine.add_message("Then choose a Ranger to equip it. (Only one ranger; automatically chosen)")
        from .models import Area
        engine.move_card(biscuit_basket.id, Area.PLAYER_AREA)

        return False
        
    def resolve_entry_47(self, source_card: 'Card | None', engine: 'GameEngine', clear_type: str | None) -> bool:
        engine.add_message("")
        engine.add_message("")
        engine.add_message("=== Campaign Log Entry 47: Hy Pimpot, Chef (PLACEHOLDER) ===")
        return False

    def resolve_entry_80(self, source_card: 'Card | None', engine: 'GameEngine', clear_type: str | None) -> bool: #clear_type of None indicates non-clear resolution
        engine.add_message("")
        engine.add_message("")
        engine.add_message("=== Campaign Log Entry 80: Quisi Vos, Rascal ===")
        engine.add_message("")
        engine.add_message("--- Checking conditionals ---")
        if clear_type is None:
            engine.add_message("Quisi entered play:")
            engine.add_message("    If a Ranger has Biscuit Basket equipped, go to 80.1.")
            if engine.state.get_cards_by_title("Biscuit Basket") is not None:
                engine.add_message("    Biscuit Basket found. Resolving Entry 80.1...")
                engine.add_message("")
                engine.add_message("")
                return self.resolve_entry("80.1", source_card, engine, clear_type)
            engine.add_message("    Biscuit Basket not found. Proceeding...")
            engine.add_message("    If Oura Vos is in play, go to 80.2.")
            if engine.state.get_cards_by_title("Oura Vos, Traveler") is not None:
                engine.add_message("    Oura Vos found. Resolving Entry 80.2...")
                engine.add_message("")
                engine.add_message("")
                return self.resolve_entry("80.2", source_card, engine, clear_type)
            engine.add_message("    Oura Vos not found. Proceeding...")
            engine.add_message("    Otherwise, go to 80.3.")
            engine.add_message("")
            engine.add_message("")
            return self.resolve_entry("80.3", source_card, engine, clear_type)
        elif clear_type.casefold() == "progress".casefold():
            engine.add_message("Quisi was cleared by Progress:")
            engine.add_message("    Go to 80.5")
            engine.add_message("")
            engine.add_message("")
            return self.resolve_entry("80.5", source_card, engine, clear_type)
        elif clear_type.casefold() == "harm".casefold():
            engine.add_message("Quisi was cleared by Harm:")
            engine.add_message("    Go to 80.6")
            engine.add_message("")
            engine.add_message("")
            return self.resolve_entry("80.6", source_card, engine, clear_type)
        else:
            raise RuntimeError("Campaign guide entry resolving with invalid clear type!")
        
    def resolve_entry_80_1(self, _source_card: 'Card | None', engine: 'GameEngine', _clear_type: str | None) -> bool:
        engine.add_message("== Campaign Log Entry 80.1 ==")
        engine.add_message("")
        engine.add_message("--- Story ---")
        engine.add_message('From behind, you hear a giggle. You turn to find a young girl, ' \
        'hand poised over the basket of juniper biscuits. "Hi!" she says, retracting her hand. ' \
        '"What are you doing? Where are you going? Can I have a biscuit? Do you have anything else to eat?"')
        engine.add_message('Each time you answer her question, she has another one at the ready. ' \
        'It seems like you have a new traveling companion, at least until you can satisfy her curiosity.')
        engine.add_message("")
        engine.add_message("--- Guidance ---")
        engine.add_message('Clear Quisi with [Progress] to satisfy her curiosity.')
        return False 
    
    def resolve_entry_80_2(self, source_card: 'Card | None', engine: 'GameEngine', _clear_type: str | None) -> bool:
        engine.add_message("== Campaign Log Entry 80.2 ==")
        engine.add_message("")
        engine.add_message("--- Story ---")
        engine.add_message('“Quisi!” You see a woman step onto the trail. "Didn\'t I tell you to meet me at the Ranger Station?"')
        engine.add_message('Quisi, for her part, is studiously focused on digging a hole in the dirt with her toe. ' \
                           '“I was going to, but then I needed to help do some Ranger stuff. I lost track of time!”')
        engine.add_message('"I\'ve heard that one before," she says. "Next time, please don\'t make me look for you. I don\'t like worrying!"')
        engine.add_message('"Don\'t worry, mama. I\'m fine!" The woman walks up to Quisi and gives her a hug, then looks at you, clearly relieved.')
        engine.add_message('“Thank you for finding my little explorer," she says. "Can you say thank you, Quisi?”')
        engine.add_message('“Thank you!" Quisi says, and gives you a hug. Then she hands you a small pouch."These are my favorite ' \
                           'snacks in the whole world. I have a whole bunch back home, so you can have these ones. Bye!"')
        
        engine.add_message("")
        engine.add_message("--- Results ---")
        engine.add_message("Gain the Quisi's Favorite Snack reward card.")
        engine.state.unlock_reward("Quisi's Favorite Snack")

        engine.add_message("Write ACCEPTED SNACKS on the campaign tracker.")
        engine.state.record_notable_event("ACCEPTED SNACKS")

        engine.add_message("Discard Oura and Quisi.")
        oura = engine.state.get_cards_by_title("Oura Vos, Traveler")[0]
        quisi = source_card
        oura.discard_from_play(engine)
        quisi.discard_from_play(engine)

        engine.add_message("Each ranger soothes 2 fatigue.")
        engine.state.ranger.soothe(engine, 2)
        return True
        
    def resolve_entry_80_3(self, _source_card: 'Card | None', engine: 'GameEngine', _clear_type: str | None) -> bool:
        engine.add_message("== Campaign Log Entry 80.3 ==")
        engine.add_message("")
        engine.add_message("--- Story ---")
        engine.add_message('From up ahead, you hear a child quietly singing to herself. ' \
        'You move around a large cedar bole to find a young girl, maybe eight years old, ' \
        'tracing patterns in the ground with a rock. She’s covered in dirt, head to toe. ' \
        'In place of her left hand is a miraculous piece of technology: a prosthesis, ' \
        'gleaming in the sunlight, its fingers suspended in air, held only by her body’s ' \
        'memory of the hand.')
        engine.add_message('As soon as she notices you, she hops to her feet. “Hi! I’m Quisi! ' \
                           'What are you doing? Where are you going? What is that? Can I use it?”')
        engine.add_message('Each time you answer her question, she has another one at the ready. ' \
        'It seems like you have a new traveling companion, at least until you can satisfy her curiosity.')
        engine.add_message("")
        engine.add_message("--- Guidance ---")
        engine.add_message('Clear Quisi with [Progress] to satisfy her curiosity.')
        return False
    
    def resolve_entry_80_5(self, source_card: 'Card | None', engine: 'GameEngine', _clear_type: str | None) -> bool:
        engine.add_message("== Campaign Log Entry 80.5 ==")
        engine.add_message("")
        engine.add_message("--- Story ---")
        engine.add_message('After a nonstop barrage of questions, you’re a bit surprised when Quisi ' \
        'suddenly stops talking. You turn, and she’s standing on a rock, shielding her eyes as she looks at the sun.')
        engine.add_message('“I would stay and help you some more, but I can’t be late for dinner. See you some other ' \
        'time!” She hops off the rock and scampers down the path, vanishing from view in an instant.')

        engine.add_message("")
        engine.add_message("--- Results ---")
        engine.add_message('Each Ranger soothes 2 fatigue.')
        engine.state.ranger.soothe(engine, 2)

        engine.add_message('Discard Quisi.')
        quisi = source_card
        quisi.discard_from_play(engine)
        return True

    def resolve_entry_80_6(self, _source_card: 'Card | None', engine: 'GameEngine', _clear_type: str | None) -> bool:
        engine.add_message("== Campaign Log Entry 80.6 ==")
        engine.add_message("")
        engine.add_message("--- Story ---")
        engine.add_message('    Quisi yelps. You kneel down next to her, comforting her with ' \
        'soothing words as you inspect the injury. It looks treatable, but doing so will take time.')

        engine.add_message("")
        engine.add_message("--- Results ---")
        engine.add_message('End the day.')
        engine.end_day()
        return True
    
    def resolve_entry_85(self, source_card: 'Card | None', engine: 'GameEngine', clear_type: str | None) -> bool:
        engine.add_message("")
        engine.add_message("")
        engine.add_message("=== Campaign Log Entry 85: Calypsa, Ranger Mentor (PLACEHOLDER) ===")
        return False
    
    def resolve_entry_86(self, source_card: 'Card | None', engine: 'GameEngine', clear_type: str | None) -> bool:
        engine.add_message("")
        engine.add_message("")
        engine.add_message("=== Campaign Log Entry 86: The Fundamentalist (PLACEHOLDER) ===")
        return False
    
    def resolve_entry_91(self, source_card: 'Card | None', engine: 'GameEngine', clear_type: str | None) -> bool: #clear_type of None indicates non-clear resolution
        engine.add_message("")
        engine.add_message("")
        engine.add_message("=== Campaign Log Entry 91: Biscuit Delivery ===")
        engine.add_message("")
        engine.add_message("--- Checking conditionals ---")
        if clear_type is None:
            engine.add_message("Checking who entered play among Kordo, Nal, Hy, and Quisi:")
            if source_card.title == "Kordo, Ranger Veteran":
                engine.add_message("    Kordo entered play. Resolving Entry 91.1...")
                engine.add_message("")
                engine.add_message("")
                return self.entries["91.1"](source_card, engine, clear_type) #go directly to not get overridden again
            elif source_card.title == "Spirit Speaker Nal":
                engine.add_message("    Nal entered play. Resolving Entry 91.2...")
                engine.add_message("")
                engine.add_message("")
                return self.entries["91.2"](source_card, engine, clear_type) #go directly to not get overridden again
            elif source_card.title == "Hy Pimpot, Chef":
                engine.add_message("    Hy entered play. Resolving Entry 91.3...")
                engine.add_message("")
                engine.add_message("")
                return self.entries["91.3"](source_card, engine, clear_type) #go directly to not get overridden again
            elif source_card.title == "Quisi Vos, Rascal":
                engine.add_message("    Quisi entered play. Resolving Entry 91.4...")
                engine.add_message("")
                engine.add_message("")
                return self.entries["91.4"](source_card, engine, clear_type) #go directly to not get overridden again
            else:
                raise RuntimeError("Should not be resolving entry 91 for cards entering play besides Kordo, Nal, Hy, and Quisi!")
        elif clear_type.casefold() == "progress".casefold():
            engine.add_message("Checking who cleared by progress among Kordo, Nal, Hy, and Quisi:")
            if source_card.title == "Kordo, Ranger Veteran":
                engine.add_message("    Kordo cleared. Resolving Entry 91.5...")
                engine.add_message("")
                engine.add_message("")
                return self.entries["91.5"](source_card, engine, clear_type) #go directly to not get overridden again
            elif source_card.title == "Spirit Speaker Nal":
                engine.add_message("    Nal cleared. Resolving Entry 91.6...")
                engine.add_message("")
                engine.add_message("")
                return self.entries["91.6"](source_card, engine, clear_type) #go directly to not get overridden again
            elif source_card.title == "Hy Pimpot, Chef":
                engine.add_message("    Hy cleared. Resolving Entry 91.7...")
                engine.add_message("")
                engine.add_message("")
                return self.entries["91.7"](source_card, engine, clear_type) #go directly to not get overridden again
            elif source_card.title == "Quisi Vos, Rascal":
                engine.add_message("    Quisi cleared. Resolving Entry 91.8...")
                engine.add_message("")
                engine.add_message("")
                return self.entries["91.8"](source_card, engine, clear_type) #go directly to not get overridden again
            else:
                raise RuntimeError("Should not be resolving entry 91 for cards clearing by progress besides Kordo, Nal, Hy, and Quisi!")
        elif clear_type.casefold() == "harm".casefold():
            engine.add_message("Checking who cleared by harm among Kordo, Nal, Hy, and Quisi:")
            if source_card.title == "Kordo, Ranger Veteran":
                engine.add_message("    Kordo cleared. Resolving Entry 44.7...")
                engine.add_message("")
                engine.add_message("")
                return self.entries["44.7"](source_card, engine, clear_type) #go directly to not get overridden again
            elif source_card.title == "Spirit Speaker Nal":
                engine.add_message("    Nal cleared. Resolving Entry 45.8...")
                engine.add_message("")
                engine.add_message("")
                return self.entries["45.8"](source_card, engine, clear_type) #go directly to not get overridden again
            elif source_card.title == "Hy Pimpot, Chef":
                engine.add_message("    Hy cleared. Resolving Entry 47.6...")
                engine.add_message("")
                engine.add_message("")
                return self.entries["47.6"](source_card, engine, clear_type) #go directly to not get overridden again
            elif source_card.title == "Quisi Vos, Rascal":
                engine.add_message("    Quisi cleared. Resolving Entry 80.6...")
                engine.add_message("")
                engine.add_message("")
                return self.entries["80.6"](source_card, engine, clear_type) #go directly to not get overridden again
            else:
                raise RuntimeError("Should not be resolving entry 91 for cards clearing by harm besides Kordo, Nal, Hy, and Quisi!")
        else:
            raise RuntimeError("Campaign guide entry resolving with invalid clear type!")
        
    def resolve_entry_91_1(self, _source_card: 'Card | None', engine: 'GameEngine', clear_type: str | None) -> bool:
        engine.add_message("== Campaign Log Entry 91.1 ==")
        engine.add_message("")
        engine.add_message("--- Story ---")
        engine.add_message('“Glad you made it through training,” the grizzled man sticks out his hand and ' \
                           'shakes yours firmly. “The name\'s Kordo in case you forgot. I understand you ' \
                           'have a lot of new faces to take in.”')
        engine.add_message("")
        engine.add_message("--- Guidance ---")
        engine.add_message('Clear Kordo with [Progress] to speak with him further.')
        return False
    
    def resolve_entry_91_2(self, _source_card: 'Card | None', engine: 'GameEngine', clear_type: str | None) -> bool:
        engine.add_message("== Campaign Log Entry 91.2 ==")
        engine.add_message("")
        engine.add_message("--- Story ---")
        engine.add_message('You come across a woman sitting on a meditation pillow, her eyes closed. She doesn’t ' \
        'open them, but gestures for you to come closer.')
        engine.add_message('“We’re happy to have you,” she says. “I’m Nal, the Spirit Speaker here at Lone Tree ' \
                           'Station. Sit with me for a minute, then we can talk.”')
        engine.add_message("")
        engine.add_message("--- Guidance ---")
        engine.add_message('Clear Nal with [Progress] to speak with her further.')
        return False
    
    def resolve_entry_91_3(self, _source_card: 'Card | None', engine: 'GameEngine', clear_type: str | None) -> bool:
        engine.add_message("== Campaign Log Entry 91.3 ==")
        engine.add_message("")
        engine.add_message("--- Story ---")
        engine.add_message('You come across a massive pile of diced and sliced vegetables, roots, and tubers. ' \
        'Occasionally, more slices fly through the air to land on top of the pile.')
        engine.add_message('“Back already?” a voice says from beyond the vegetable pile. “I told you. There’s no ' \
                           'silverfin curry to be had until the fish has marinated for at least three hours!”')
        engine.add_message('A head pokes out from behind the pile. “Oh, it’s you! I thought you were Elder Thrush. ' \
                           'She gets so impatient on silverfin curry day! Calypsa sent you for the biscuits, eh? ' \
                           'They’re just out of the oven. Let me know when you’re ready to leave, and we’ll get you ' \
                           'and those biscuits to the good people of White Sky straight away.”')
        engine.add_message("")
        engine.add_message("--- Guidance ---")
        engine.add_message('Travel away from Lone Tree Station while Hy Pimpot is in play to complete the Mission.')
        return False
    
    def resolve_entry_91_4(self, _source_card: 'Card | None', engine: 'GameEngine', clear_type: str | None) -> bool:
        engine.add_message("== Campaign Log Entry 91.4 ==")
        engine.add_message("")
        engine.add_message("--- Story ---")
        engine.add_message('You feel a tug on your backpack and turn to see a young girl suddenly walking beside you.')
        engine.add_message('“Hi!” she says. “Do you smell something? Is Hy Pimpot baking his famous juniper biscuits? ' \
                           'Can I have one? Which way to the kitchen?”')
        engine.add_message("")
        engine.add_message("--- Guidance ---")
        engine.add_message('Clear Quisi with [Progress] to help her find the kitchen.')
        return False
    
    def resolve_entry_91_5(self, source_card: 'Card | None', engine: 'GameEngine', clear_type: str | None) -> bool:
        engine.add_message("== Campaign Log Entry 91.5 ==")
        engine.add_message("")
        engine.add_message("--- Story ---")
        engine.add_message('“Well, I’ve been in the Rangers for a few decades. Survived more atrox attacks ' \
                           'than I can count!” Kordo rubs his chin. “Once, I was one of the best hunters in ' \
                           'the Valley. I suppose I still am, but these days I spend most of my time keeping ' \
                           'things running smoothly around here. Though I do get out for a hunt every now and then.”')
        engine.add_message('His voice takes on a tone of mock severity. “I’d take you on a hunt right now, in fact, ' \
                           'but you have some biscuits to deliver! You’re not going to let the people of White Sky ' \
                            'starve are you?”')
        engine.add_message("")
        engine.add_message("--- Results ---")
        engine.add_message('Each ranger soothes 2 fatigue, then discard Kordo.')
        engine.state.ranger.soothe(engine, 2)
        engine.add_message(source_card.discard_from_play(engine))
        return True
    
    def resolve_entry_91_6(self, source_card: 'Card | None', engine: 'GameEngine', clear_type: str | None) -> bool:
        engine.add_message("== Campaign Log Entry 91.6 ==")
        engine.add_message("")
        engine.add_message("--- Story ---")
        engine.add_message('Nal opens her eyes and slowly turns to you, her movements precise and fluid. She smiles ' \
                           'at you like an old friend. “That was lovely,” she says. “I just had the most amazing ' \
                           'experience. I was speaking with the spirit of Mount Nim. It was so powerful! And ancient! ' \
                           'It’s a great spirit to call upon if you ever find yourself in need of some perspective.”')
        engine.add_message('“But right now, we should check on the spirits of those biscuits” she says with a playful ' \
                           'smirk. “You’d better find Hy Pimpot and pick them up while they’re still warm!”')
        engine.add_message("")
        engine.add_message("--- Results ---")
        engine.add_message('Each ranger soothes 2 fatigue, then discard Nal.')
        engine.state.ranger.soothe(engine, 2)
        engine.add_message(source_card.discard_from_play(engine))
        return True
    
    def resolve_entry_91_7(self, source_card: 'Card | None', engine: 'GameEngine', clear_type: str | None) -> bool:
        engine.add_message("== Campaign Log Entry 91.7 ==")
        engine.add_message("")
        engine.add_message("--- Story ---")
        engine.add_message('Hy Pimpot crosses his arms and gives you a severe look. “You’d better grab those ' \
                           'biscuits and hit the trail before they cool too much! They’re still good cold, mind ' \
                           'you, but they’re just so much better when they’re warm!”')
        engine.add_message('You raise your hands and tell him you’re just about to leave. “Good!” he says. '\
                           '“Just let me know when you’re ready. I’ll be right here. Waiting.”')
        engine.add_message("")
        engine.add_message("--- Results ---")
        engine.add_message('Discard all progress from Hy Pimpot (He is not discarded).')
        _, msg = source_card.remove_progress(source_card.progress)
        engine.add_message(msg)
        return False
    
    def resolve_entry_91_8(self, source_card: 'Card | None', engine: 'GameEngine', clear_type: str | None) -> bool:
        engine.add_message("== Campaign Log Entry 91.8 ==")
        engine.add_message("")
        engine.add_message("--- Story ---")
        engine.add_message('In your time together, Quisi has made a game of scouring Lone Tree Station for clues ' \
        'as to the kitchen’s whereabouts. Eventually, the scent of Hy Pimpot’s biscuits grows stronger, and Quisi ' \
        'cheers. “Yes! Yes! Yes! Delicious biscuits, here I come!” She runs off.')
        engine.add_message("")
        engine.add_message("--- Results ---")
        engine.add_message('Each ranger soothes 2 fatigue, then discard Quisi.')
        engine.state.ranger.soothe(engine, 2)
        engine.add_message(source_card.discard_from_play(engine))
        return True