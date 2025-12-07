from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .engine import GameEngine

class CampaignGuide:
    def __init__(self):
        self.entries : dict[str, Callable[['CampaignGuide', 'GameEngine', str | None], bool]] = {
            "1.01": self.resolve_entry_1_01,
            "47": self.resolve_entry_47, #placeholder to prevent crashing when Hy Pimpot enters play
            "80": self.resolve_entry_80,
            "80.1": self.resolve_entry_80_1,
            "80.2": self.resolve_entry_80_2,
            "80.3": self.resolve_entry_80_3,
            "80.5": self.resolve_entry_80_5,
            "80.6": self.resolve_entry_80_6,
            "85": self.resolve_entry_85, #placeholder to prevent crashing when Calypsa enters play
            "86": self.resolve_entry_86 #placeholder to prevent crashing when The Fundamentalist enters play
            }
    
    def resolve_entry_1_01(self, engine: 'GameEngine', clear_type: str | None) -> bool:
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
        biscuit_delivery = engine.state.get_cards_by_title("Biscuit Delivery")[0]
        biscuit_basket = biscuit_delivery.flip(engine)
        engine.add_message("Then choose a Ranger to equip it. (Only one ranger; automatically chosen)")
        from .models import Area
        engine.move_card(biscuit_basket.id, Area.PLAYER_AREA)

        return False
        
    def resolve_entry_47(self, engine: 'GameEngine', clear_type: str | None) -> bool:
        engine.add_message("")
        engine.add_message("")
        engine.add_message("=== Campaign Log Entry 47: Hy Pimpot, Chef (PLACEHOLDER) ===")
        return False

    def resolve_entry_80(self, engine: 'GameEngine', clear_type: str | None) -> bool: #clear_type of None indicates non-clear resolution
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
                return self.entries["80.1"](engine, clear_type)
            engine.add_message("    Biscuit Basket not found. Proceeding...")
            engine.add_message("    If Oura Vos is in play, go to 80.2.")
            if engine.state.get_cards_by_title("Oura Vos, Traveler") is not None:
                engine.add_message("    Oura Vos found. Resolving Entry 80.2...")
                engine.add_message("")
                engine.add_message("")
                return self.entries["80.2"](engine, clear_type)
            engine.add_message("    Oura Vos not found. Proceeding...")
            engine.add_message("    Otherwise, go to 80.3.")
            engine.add_message("")
            engine.add_message("")
            return self.entries["80.3"](engine, clear_type)
        elif clear_type.casefold() == "progress".casefold():
            engine.add_message("Quisi was cleared by Progress:")
            engine.add_message("    Go to 80.5")
            engine.add_message("")
            engine.add_message("")
            return self.entries["80.5"](engine, clear_type)
        elif clear_type.casefold() == "harm".casefold():
            engine.add_message("Quisi was cleared by Harm:")
            engine.add_message("    Go to 80.6")
            engine.add_message("")
            engine.add_message("")
            return self.entries["80.6"](engine, clear_type)
        else:
            raise RuntimeError("Campaign guide entry resolving with invalid clear type!")
        
    def resolve_entry_80_1(self, engine: 'GameEngine', _clear_type: str | None) -> bool:
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
    
    def resolve_entry_80_2(self, engine: 'GameEngine', _clear_type: str | None) -> bool:
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
        quisi = engine.state.get_cards_by_title("Quisi Vos, Rascal")[0]
        oura.discard_from_play(engine)
        quisi.discard_from_play(engine)

        engine.add_message("Each ranger soothes 2 fatigue.")
        engine.state.ranger.soothe(engine, 2)
        return True
        
    def resolve_entry_80_3(self, engine: 'GameEngine', _clear_type: str | None) -> bool:
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
    
    def resolve_entry_80_5(self, engine: 'GameEngine', _clear_type: str | None) -> bool:
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
        quisi = engine.state.get_cards_by_title("Quisi Vos, Rascal")[0]
        quisi.discard_from_play(engine)
        return True

    def resolve_entry_80_6(self, engine: 'GameEngine', _clear_type: str | None) -> bool:
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
    
    def resolve_entry_85(self, engine: 'GameEngine', clear_type: str | None) -> bool:
        engine.add_message("")
        engine.add_message("")
        engine.add_message("=== Campaign Log Entry 85: Calypsa, Ranger Mentor (PLACEHOLDER) ===")
        return False
    
    def resolve_entry_86(self, engine: 'GameEngine', clear_type: str | None) -> bool:
        engine.add_message("")
        engine.add_message("")
        engine.add_message("=== Campaign Log Entry 86: The Fundamentalist (PLACEHOLDER) ===")
        return False