from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .engine import GameEngine
    from .models import Card

class CampaignGuide:
    def __init__(self):
        self.entries : dict[str, Callable[['CampaignGuide', 'Card | None', 'GameEngine', str | None], bool]] = {
            "1": self.resolve_entry_1,
            "1.01": self.resolve_entry_1_01,
            "1.02": self.resolve_entry_1_02,
            "1.02A": self.resolve_entry_1_02_A,
            "1.03": self.resolve_entry_1_03,
            "2": self.resolve_entry_2, #Lone Tree Station
            "14": self.resolve_entry_14, #Boulder Field
            "15": self.resolve_entry_15, #Ancestor's Grove
            "47": self.resolve_entry_47, #placeholder to prevent crashing when Hy Pimpot enters play
            "80": self.resolve_entry_80, #Quisi
            "80.1": self.resolve_entry_80_1,
            "80.2": self.resolve_entry_80_2,
            "80.3": self.resolve_entry_80_3,
            "80.5": self.resolve_entry_80_5,
            "80.6": self.resolve_entry_80_6,
            "85": self.resolve_entry_85, #placeholder to prevent crashing when Calypsa enters play
            "86": self.resolve_entry_86, #placeholder to prevent crashing when The Fundamentalist enters play
            "91": self.resolve_entry_91, #Biscuit Delivery
            "91.1": self.resolve_entry_91_1,
            "91.2": self.resolve_entry_91_2,
            "91.3": self.resolve_entry_91_3,
            "91.4": self.resolve_entry_91_4,
            "91.5": self.resolve_entry_91_5,
            "91.6": self.resolve_entry_91_6,
            "91.7": self.resolve_entry_91_7,
            "91.8": self.resolve_entry_91_8,
            "94.1": self.resolve_entry_94_1, #start-of-day entry for day 3
            "1.04": self.resolve_entry_1_04, #start-of-day entry for day 4
            }
    
    """
    Resolves the campaign guide entry at ENTRY_NUMBER, noting the SOURCE_CARD if present and CLEAR_TYPE if relevant
    Returns whether or not the SOURCE_CARD was discarded as part of the campaign guide entry resolution
    """
    def resolve_entry(self, entry_number: str, source_card: 'Card | None', engine: 'GameEngine', clear_type: str | None) -> bool:
        from .models import ConstantAbilityType
        actual_entry_number = entry_number
        for ability in engine.get_constant_abilities_by_type(ConstantAbilityType.OVERRIDE_CAMPAIGN_ENTRY):
            if ability.condition_fn(engine.state, source_card):
                actual_entry_number = ability.override_entry
                break
                #TODO: Handle multiple overrides. 
        return self.entries[actual_entry_number](source_card, engine, clear_type)
    
    def resolve_entry_1(self, source_card: 'Card | None', engine: 'GameEngine', clear_type: str | None) -> bool:
        engine.add_message("")
        engine.add_message("")
        engine.add_message("== Campaign Guide Entry 1: Missions ==")
        engine.add_message("")
        engine.add_message("--- CAMPAIGN START ---")
        engine.add_message("To start your campaign, perform the first four steps of setup on page 10 of the rulebook, " \
        "then return here for the remainder of setup.")
        engine.add_message("")
        engine.add_message("--- Day 1 Setup (First four steps) ---")
        engine.add_message("")
        engine.add_message(f"Step 1: Set up player area (skipped)")
        engine.add_message(f"Step 2: Draw starting hand")

        # Draw starting hand
        for _ in range(5):
            card, _ = engine.state.ranger.draw_card(engine)
            if card is None:
                raise RuntimeError(f"Deck should not run out during setup!")

        engine.add_message(f"Step 3: Elect lead Ranger (only one ranger; automatically chosen)")
        engine.add_message(f"Step 4: Shuffle challenge deck")
        engine.state.challenge_deck.reshuffle()
        engine.add_message("First four steps of Setup complete; returning to campaign guide entry 1:")
        engine.add_message("")
        engine.add_message("--- Story ---")
        engine.add_message("Cresting the gentle, grassy hill, you see the unmistakable silhouette of " \
        "Lone Tree Station rise out of the highland plains before you. Lone Tree Station is aptly named. " \
        "The single massive giga-redwood towers above the hills and swaying grass that surround it. You " \
        "can just make out eaves and balconies among the gnarled bark, doors tucked into the winding roots, " \
        "and hanging gardens suspended from branches.")
        engine.add_message("As you draw closer, a woman in a freshly pressed cloak steps out from the main " \
        "entrance and waves. Calypsa, your mentor for the past nine months, strides toward you with a man who " \
        "looks just about your age at her heels.")
        engine.add_message("“Hallo!” she calls out. “You made it. Just look at you!” She clasps your hands, her " \
        "smile warm and her grip firm. “I’m glad to finally have you here,” she says. Then she turns. “This is Kal " \
        "Iver. I trained Kal last year—right before I started training you.” Kal Iver gives you a nod in greeting. " \
        "“A pleasure,” he says.")
        engine.add_message("")
        engine.add_message("--- Instruction ---")
        engine.add_message("Put the Lone Tree Station location into play in the surroundings.")
        from .decks import get_location_by_id
        from .models import Area
        engine.state.location = get_location_by_id("Lone Tree Station")
        engine.state.areas[Area.SURROUNDINGS].append(engine.state.location)
        #skip calling enters_play on Lone Tree Station; we resolve its campaign guide entry later and it has no
        #listeners or constant abilities to register
        engine.add_message("Lone Tree Station has entered play in the Surroundings.")
        engine.add_message("")
        engine.add_message("--- Story ---")
        engine.add_message("Calypsa heads back to the station with you and Kal in tow. She speaks back over " \
                           "her shoulder. “Please, make yourselves at home. Explore the hanging gardens. Find " \
                           "Spirit Speaker Nal and Kordo, and strike up a conversation. Get to know the place.”")
        engine.add_message("“After you’ve spent some time here at the Station, you should head over to White Sky,” " \
                           "she says. “In fact, Hy Pimpot has some juniper biscuits baking right now. His food is " \
                           "legendary around these parts. Once those biscuits are ready and you’ve had a chance to " \
                           "poke around, take a parcel over to White Sky, and offer them to the people you meet. " \
                           "It’s been at least a year since our neighbors have enjoyed the company of Rangers bearing " \
                           "treats.” She turns to look at Kal. “What do you think, Kal? Good way to get started?”")
        engine.add_message("Kal grins at you in a way that you can’t quite describe as a sneer. “Handing out baked goods? " \
                            "I think that’s perfectly suited to their abilities,” he says.")
        engine.add_message("")
        engine.add_message("--- RANGERS CHOOSE: ---")
        engine.add_message("A. Tell Kal what he can do with his condescending attitude.")
        engine.add_message("B. Ignore him.")
        is_A = engine.response_decider(engine, "Input 'y' for option A, 'n' for option B:")
        if is_A:
            engine.add_message("")
            engine.add_message("--- Story ---")
            engine.add_message("    Calypsa glares. “Recall the wisdom of our ancestors,” she says. “Treat each other " \
                               "with kindness.” On “kind” she punches you on the shoulder. On “-ness,” she punches Kal’s.")
            engine.add_message("")
            engine.add_message("--- Result ---")
            engine.add_message("Write STOOD UP TO KAL on the campaign tracker.")
            engine.state.record_notable_event("STOOD UP TO KAL")
        else:
            engine.add_message("")
            engine.add_message("--- Story ---")
            engine.add_message("Calypsa shakes her head and laughs. “Oh, Kal. You’re not long past delivering biscuits " \
                               "yourself. It’s tradition, after all.”")
            engine.add_message("")
            engine.add_message("--- Result ---")
            engine.add_message("Write IMPRESSED CALYPSA on the campaign tracker.")
            engine.state.record_notable_event("IMPRESSED CALYPSA")
        engine.add_message("")
        engine.add_message("--- >> Continue Reading: ---")
        engine.add_message("")
        engine.add_message("--- Instructions ---")
        engine.add_message("Gain the BISCUIT DELIVERY mission. (Add it to the Missions section of the campaign tracker, and " \
                           "put its card into play in the surroundings.)")
        engine.state.gain_mission("Biscuit Delivery") #only adds to campaign tracker; still have to add to game state below
        from .cards import BiscuitDelivery
        b_d = BiscuitDelivery()
        engine.state.missions = [b_d]
        engine.state.areas[Area.SURROUNDINGS].extend(engine.state.missions)
        b_d.enters_play(engine, Area.SURROUNDINGS, None)
        engine.add_message("Check the campaign tracker for the weather for the current day (day 1). Put the corresponding weather " \
                           "card (A Perfect Day) into play.")
        from .cards import APerfectDay
        a_p_d = APerfectDay()
        engine.state.weather = a_p_d
        engine.state.areas[Area.SURROUNDINGS].insert(0, engine.state.weather)
        engine.state.weather.enters_play(engine, Area.SURROUNDINGS, None)
        engine.add_message("")
        engine.add_message("--- Story ---")
        engine.add_message("Calypsa turns to you. “Kal and I are heading out into the Valley. We’ll be on shadow patrol. That is, " \
                           "we’ll never be too far away from you for the next few weeks.”")
        engine.add_message("“You shouldn’t need our help, of course,” Kal says. “I can tell by looking at you that you’re more than capable.”")
        engine.add_message("“Farewell for now,” Calypsa says and starts down the eastern path away from Lone Tree. “Spirits guide you. " \
                           "Follow your instinct!” She and Kal walk steadily out of sight.")
        engine.add_message("")
        engine.add_message("--- Guidance ---")
        engine.add_message("Explore Lone Tree Station to find Hy Pimpot, retrieve the juniper biscuits, and learn what to do next.")
        engine.add_message("")
        engine.add_message("--- Instructions ---")
        engine.add_message("Create the path deck by shuffling together the Woods and Lone Tree card sets (seventeen cards in total).")
        from .decks import build_woods_path_deck, get_pivotal_cards
        from random import shuffle
        woods_set: list[Card] = build_woods_path_deck()
        lone_tree_station_set: list[Card] = get_pivotal_cards(engine.state.location)
        engine.state.path_deck = woods_set + lone_tree_station_set
        shuffle(engine.state.path_deck)
        engine.add_message("(Path deck created, shuffled, and loaded into game.)")
        engine.add_message("Then, complete all initial setup by performing the setup steps on the back of the Lone Tree Station location card.")
        self.resolve_entry_2(source_card, engine, clear_type)
        engine.add_message("")
        engine.add_message("--- Arrival Setup ---")
        engine.state.location.do_arrival_setup(engine)
        engine.add_message("")
        engine.add_message("Returning to Campaign Guide Entry 1...")
        engine.add_message("That concludes setup. You’re ready to play. Now go explore Lone Tree Station, and find Hy Pimpot!")
        from .view import display_and_clear_messages
        display_and_clear_messages(engine)
        return False

    def resolve_entry_2(self, source_card: 'Card | None', engine: 'GameEngine', clear_type: str | None) -> bool:
        engine.add_message("")
        engine.add_message("")
        engine.add_message("== Campaign Guide Entry 2: Lone Tree Station ==")
        engine.add_message("")
        engine.add_message("--- Story ---")
        engine.add_message("Visible for miles around, Lone Tree is a single enormous giga-redwood rising out of " \
        "the thick grass of a high prairie. From far away, the tree is all you can see, but as you come closer, " \
        "you can see the rest of the station: the large box-garden plots hanging from the branches, the airship " \
        "Swift moored to its dock in the tree’s crown, the doors and windows carved into the trunk and peeking " \
        "out from among the roots. Lone Tree Station has been the base of operations for the Rangers ever since " \
        "the people came to the Valley. And ever since you became a Ranger, it’s been your home.")
        return False

    def resolve_entry_14(self, _source_card: 'Card | None', engine: 'GameEngine', _clear_type: str | None) -> bool:
        engine.add_message("")
        engine.add_message("")
        engine.add_message("== Campaign Guide Entry 14: Boulder Field ==")
        engine.add_message("")
        engine.add_message("--- Story ---")
        engine.add_message("    Long ago, a great mountain once stood here, but as the millenniums passed, it " \
        "steadily split and crumbled. At the edges of the boulder field, the ground is littered with round rocks " \
        "the size of apples. As you head deeper in, however, the boulders grow larger until you find yourself " \
        "weaving between what you imagine to be the bones of the lost mountain, pillars of rock that reach toward the sky.")
        return False
    
    def resolve_entry_15(self, _source_card: 'Card | None', engine: 'GameEngine', _clear_type: str | None) -> bool:
        engine.add_message("")
        engine.add_message("")
        engine.add_message("== Campaign Guide Entry 15: Ancestor's Grove ==")
        engine.add_message("")
        engine.add_message("--- Story ---")
        engine.add_message("A reverent calm suffuses your being as you step into the Ancestor’s Grove. Each of the " \
        "trees, from the smallest sapling to the towering giants at the grove’s center, has been planted over the " \
        "final resting place of a loved one. You move with care through the grove. You see several people, some " \
        "keeping to themselves, some speaking softly, some bearing gifts, all here to commune with those who have " \
        "passed. You pause and give thought to your ancestors.")
        return False

    
    def resolve_entry_1_01(self, source_card: 'Card | None', engine: 'GameEngine', clear_type: str | None) -> bool:
        engine.add_message("")
        engine.add_message("")
        engine.add_message("== Campaign Guide Entry 1.01 ==")
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
        engine.enforce_equip_limit()

        return False
    
    def resolve_entry_1_02(self, source_card: 'Card | None', engine: 'GameEngine', clear_type: str | None) -> bool:
        engine.add_message("")
        engine.add_message("")
        engine.add_message("== Campaign Guide Entry 1.02 ==")
        engine.add_message("")
        engine.add_message("--- Checking conditionals ---")
        engine.add_message("    If the rangers have no biscuits on their role cards, go to 1.02A.")
        engine.add_message("    Checking for biscuits on role cards...")
        biscuits = engine.state.role_card.unique_tokens.get("biscuit")
        if biscuits is not None and biscuits > 0:
            engine.add_message("    Biscuits found. Proceeding...")
            engine.add_message("")
            engine.add_message("--- Story ---")
            engine.add_message('With an empty basket, you continue down the path until you come across ' \
            'Calypsa and Kal, resting beside a bubbling stream. Calypsa gestures toward the basket.')
            engine.add_message('“How did it go?” she asks.')
            engine.add_message('Before you can answer, Kal gives a mirthless laugh. “I think those crumbs speak for themselves.”')
            engine.add_message('You glance down and self-consciously brush the biscuit crumbs off your shirt.')
            engine.add_message("")
            engine.add_message("--- Results ---")
            engine.add_message("Complete the BISCUIT DELIVERY Mission and return Biscuit Basket to the collection.")
            engine.state.complete_mission("Biscuit Delivery")
            biscuit_basket = engine.state.get_in_play_cards_by_title("Biscuit Basket")[0] 
            #should always be in play since it had to be in play to trigger this entry
            engine.add_message(biscuit_basket.discard_from_play(engine))
            engine.state.ranger.discard.remove(biscuit_basket)

            engine.add_message("Each Ranger soothes 2 fatigue. Then go to 1.03.")
            engine.state.ranger.soothe(engine, 2)
            return self.resolve_entry("1.03", source_card, engine, clear_type)
        else:
            engine.add_message("    No biscuits found. Proceeding to 1.02A...")
            return self.resolve_entry("1.02A", source_card, engine, clear_type)
        
    def resolve_entry_1_02_A(self, source_card: 'Card | None', engine: 'GameEngine', clear_type: str | None) -> bool:
        engine.add_message("== Campaign Guide Entry 1.02A ==")
        engine.add_message("")
        engine.add_message("--- Story ---")
        engine.add_message('With an empty basket, you continue down the path until you come across ' \
        'Calypsa and Kal, resting beside a bubbling stream. Calypsa gestures toward the basket.')
        engine.add_message('“How did it go?” she asks.')
        engine.add_message('You tell her of the people you met in your travels today and how each was ' \
        'appreciative of Hy Pimpot’s bakery.')
        engine.add_message('Calypsa stands and makes a show of studying you closely. “And … no crumbs! ' \
                           'I’m impressed. Kal, I believe this settles our bet. He figured you would have snuck a few for yourself.”')
        engine.add_message('Kal looks at you suspiciously. “You need to learn to live a little,” he says.')
        engine.add_message("")
        engine.add_message("--- Results ---")
        engine.add_message("Complete the BISCUIT DELIVERY Mission and return Biscuit Basket to the collection.")
        engine.state.complete_mission("Biscuit Delivery")
        biscuit_basket = engine.state.get_in_play_cards_by_title("Biscuit Basket")[0] 
        #should always be in play since it had to be in play to trigger this entry
        engine.add_message(biscuit_basket.discard_from_play(engine))
        engine.state.ranger.discard.remove(biscuit_basket)

        engine.add_message("Each Ranger soothes 2 fatigue. Then go to 1.03.")
        engine.state.ranger.soothe(engine, 2)
        return self.resolve_entry("1.03", source_card, engine, clear_type)
            
    def resolve_entry_1_03(self, source_card: 'Card | None', engine: 'GameEngine', clear_type: str | None) -> bool:
        engine.add_message("== Campaign Guide Entry 1.03 ==")
        engine.add_message("")
        engine.add_message("--- Story ---")
        engine.add_message('From down the path comes the sound of melodic whistling. Before long, a man wearing many ' \
        'layers of cloaks and walking with the aid of an ornate conduit follows. As he passes, he tips his wide-brimmed ' \
        'hat in your direction.')
        engine.add_message('“Good day to you, friends!”')
        engine.add_message('“Good day, Master Aell,” Calypsa replies. “Lone Tree’s hanging gardens are thirsty. ' \
                           'They’ll be grateful for some rain.”')
        engine.add_message('“Fear not, my dear Calypsa! For there is no shaper more skilled at stirring the clouds ' \
                           'than I. By the time you return, those gardens will be thoroughly soaked!”')
        engine.add_message('With that, the shaper continues down the path. He resumes his whistling as he passes from sight.')
        engine.add_message('Kal shakes his head. “That fool is overly impressed by his own abilities,” he says. ' \
                           '“Trouble will come of it. Mark my words.”')
        engine.add_message('Calypsa nods then turns to you. “It\'s time you should be on your way," she says. "The ' \
                           'village elders often have tasks that require the help of the Rangers. I recommend that ' \
                           'you seek them out on your travels. I know also that Kordo would like some help dealing ' \
                           'with the caustic mulcher that roams the woodlands. I\'m not sure what he has in mind, ' \
                           'but you can seek him out at Lone Tree Station if you\'re interested. Farewell!”')
        engine.add_message('With that, Calypsa and Kal disappear into the forest, leaving you to explore the Valley on your own.')
        engine.add_message("")
        engine.add_message("--- Guidance ---")
        engine.add_message('What you do now is entirely up to you. You could, for example, spend time exploring ' \
        'the different path types to familiarize yourself with the flora and fauna, or you could travel to pivotal ' \
        'locations on the map and delve into the path deck to find people in need of assistance and missions to ' \
        'complete. Take your time. You will be called upon if there’s an emergency. Now, you may end the day or ' \
        'continue playing. If you end the day, you are considered to have camped.')
        will_camp = engine.response_decider(engine, f"Will you end the day by camping? (y/n):")
        if will_camp:
            engine.end_day(will_camp)
            
        return True
        
    def resolve_entry_47(self, source_card: 'Card | None', engine: 'GameEngine', clear_type: str | None) -> bool:
        engine.add_message("")
        engine.add_message("")
        engine.add_message("=== Campaign Guide Entry 47: Hy Pimpot, Chef (PLACEHOLDER) ===")
        return False

    def resolve_entry_80(self, source_card: 'Card | None', engine: 'GameEngine', clear_type: str | None) -> bool: #clear_type of None indicates non-clear resolution
        engine.add_message("")
        engine.add_message("")
        engine.add_message("=== Campaign Guide Entry 80: Quisi Vos, Rascal ===")
        engine.add_message("")
        engine.add_message("--- Checking conditionals ---")
        if clear_type is None:
            engine.add_message("Quisi entered play:")
            engine.add_message("    If a Ranger has Biscuit Basket equipped, go to 80.1.")
            if engine.state.get_in_play_cards_by_title("Biscuit Basket"):
                engine.add_message("    Biscuit Basket found. Resolving Entry 80.1...")
                engine.add_message("")
                engine.add_message("")
                return self.resolve_entry("80.1", source_card, engine, clear_type)
            engine.add_message("    Biscuit Basket not found. Proceeding...")
            engine.add_message("    If Oura Vos is in play, go to 80.2.")
            if engine.state.get_in_play_cards_by_title("Oura Vos, Traveler"):
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
        engine.add_message("== Campaign Guide Entry 80.1 ==")
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
        engine.add_message("== Campaign Guide Entry 80.2 ==")
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
        oura = engine.state.get_in_play_cards_by_title("Oura Vos, Traveler")[0]
        quisi = source_card
        oura.discard_from_play(engine)
        quisi.discard_from_play(engine)

        engine.add_message("Each ranger soothes 2 fatigue.")
        engine.state.ranger.soothe(engine, 2)
        return True
        
    def resolve_entry_80_3(self, _source_card: 'Card | None', engine: 'GameEngine', _clear_type: str | None) -> bool:
        engine.add_message("== Campaign Guide Entry 80.3 ==")
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
        engine.add_message("== Campaign Guide Entry 80.5 ==")
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
        engine.add_message("== Campaign Guide Entry 80.6 ==")
        engine.add_message("")
        engine.add_message("--- Story ---")
        engine.add_message('    Quisi yelps. You kneel down next to her, comforting her with ' \
        'soothing words as you inspect the injury. It looks treatable, but doing so will take time.')

        engine.add_message("")
        engine.add_message("--- Results ---")
        engine.add_message('End the day.')
        engine.end_day(False)
        return True
    
    def resolve_entry_85(self, source_card: 'Card | None', engine: 'GameEngine', clear_type: str | None) -> bool:
        engine.add_message("")
        engine.add_message("")
        engine.add_message("=== Campaign Guide Entry 85: Calypsa, Ranger Mentor (PLACEHOLDER) ===")
        return False
    
    def resolve_entry_86(self, source_card: 'Card | None', engine: 'GameEngine', clear_type: str | None) -> bool:
        engine.add_message("")
        engine.add_message("")
        engine.add_message("=== Campaign Guide Entry 86: The Fundamentalist (PLACEHOLDER) ===")
        return False
    
    def resolve_entry_91(self, source_card: 'Card | None', engine: 'GameEngine', clear_type: str | None) -> bool: #clear_type of None indicates non-clear resolution
        engine.add_message("")
        engine.add_message("")
        engine.add_message("=== Campaign Guide Entry 91: Biscuit Delivery ===")
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
        engine.add_message("== Campaign Guide Entry 91.1 ==")
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
        engine.add_message("== Campaign Guide Entry 91.2 ==")
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
        engine.add_message("== Campaign Guide Entry 91.3 ==")
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
        engine.add_message("== Campaign Guide Entry 91.4 ==")
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
        engine.add_message("== Campaign Guide Entry 91.5 ==")
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
        engine.add_message("== Campaign Guide Entry 91.6 ==")
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
        engine.add_message("== Campaign Guide Entry 91.7 ==")
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
        engine.add_message("== Campaign Guide Entry 91.8 ==")
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

    def resolve_entry_94_1(self, _source_card: 'Card | None', engine: 'GameEngine', _clear_type: str | None) -> bool:
        engine.add_message("")
        engine.add_message("")
        engine.add_message("=== Campaign Guide Entry 94.1: Start of Day 3 (PLACEHOLDER) ===")
        return False

    def resolve_entry_1_04(self, _source_card: 'Card | None', engine: 'GameEngine', _clear_type: str | None) -> bool:
        engine.add_message("")
        engine.add_message("")
        engine.add_message("=== Campaign Guide Entry 1.04: Start of Day 4 (PLACEHOLDER) ===")
        return False