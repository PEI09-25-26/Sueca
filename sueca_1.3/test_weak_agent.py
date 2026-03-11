"""
Test file for CardAnalyzer, GameStateTracker, and DecisionMaker
Run this to test your implementations!

Usage:
    python test_weak_agent.py
"""
from card_analyzer import CardAnalyzer
from game_state_tracker import GameStateTracker
from decision_maker import DecisionMaker
from card_mapper import CardMapper


def test_card_analyzer():
    """Test CardAnalyzer methods"""
    print("=" * 60)
    print("TESTING CARD ANALYZER")
    print("=" * 60)
    
    # Test 1: get_card_strength
    print("\n1. Testing get_card_strength()...")
    # Card 39 = A♠, Card 38 = 7♠, Card 19 = A♦
    trump = "♠"
    lead = "♦"
    
    strength_trump = CardAnalyzer.get_card_strength(39, trump, lead)
    print(f"   A♠ (trump): {strength_trump} (expected: (2, 9))")
    
    strength_lead = CardAnalyzer.get_card_strength(19, trump, lead)
    print(f"   A♦ (lead): {strength_lead} (expected: (1, 9))")
    
    strength_off = CardAnalyzer.get_card_strength(9, trump, lead)  # A♣
    print(f"   A♣ (off-suit): {strength_off} (expected: (0, 9))")
    
    # Test 2: get_legal_plays
    print("\n2. Testing get_legal_plays()...")
    hand = [0, 1, 10, 20, 30]  # Mix of suits
    legal_diamond = CardAnalyzer.get_legal_plays(hand, "♦")
    print(f"   Hand: {[CardMapper.get_card(c) for c in hand]}")
    print(f"   Legal plays for ♦: {[CardMapper.get_card(c) for c in legal_diamond]}")
    
    legal_leading = CardAnalyzer.get_legal_plays(hand, None)
    print(f"   Legal plays when leading: {len(legal_leading)} cards (should be all)")
    
    # Test 3: is_high_value_card
    print("\n3. Testing is_high_value_card()...")
    print(f"   A♠ (39): {CardAnalyzer.is_high_value_card(39)} (expected: True)")
    print(f"   7♠ (38): {CardAnalyzer.is_high_value_card(38)} (expected: True)")
    print(f"   K♠ (37): {CardAnalyzer.is_high_value_card(37)} (expected: False)")
    
    # Test 4: get_lowest_card
    print("\n4. Testing get_lowest_card()...")
    cards = [39, 37, 30, 0]  # A♠, K♠, 2♣, 2♣
    lowest = CardAnalyzer.get_lowest_card(cards, trump)
    print(f"   From {[CardMapper.get_card(c) for c in cards]}")
    print(f"   Lowest: {CardMapper.get_card(lowest) if lowest else None}")
    
    print("\n✓ CardAnalyzer tests complete!\n")


def test_game_state_tracker():
    """Test GameStateTracker methods"""
    print("=" * 60)
    print("TESTING GAME STATE TRACKER")
    print("=" * 60)
    
    tracker = GameStateTracker()
    
    # Test 1: Initialization
    print("\n1. Testing initialization...")
    print(f"   Player name: {tracker.player_name}")
    print(f"   Remaining cards: {len(tracker.remaining_cards)} (expected: 40)")
    
    # Test 2: Mock state update
    print("\n2. Testing update_from_state()...")
    mock_state = {
        'players': [
            {'name': 'Alice', 'position': 'NORTH', 'cards_left': 10},
            {'name': 'Bob', 'position': 'EAST', 'cards_left': 10},
            {'name': 'Charlie', 'position': 'SOUTH', 'cards_left': 10},
            {'name': 'Dave', 'position': 'WEST', 'cards_left': 10},
        ],
        'teams': {
            'team1': ['Alice', 'Charlie'],
            'team2': ['Bob', 'Dave']
        },
        'trump_suit': '♠',
        'current_round': 1,
        'round_suit': None,
        'round_plays': [],
        'team_scores': {'team1': 0, 'team2': 0}
    }
    
    tracker.update_from_state(mock_state, 'Alice')
    print(f"   Player: {tracker.player_name}")
    print(f"   Position: {tracker.position}")
    print(f"   Team ID: {tracker.team_id}")
    print(f"   Partner: {tracker.partner_id}")
    print(f"   Opponents: {tracker.opponents}")
    print(f"   Trump suit: {tracker.trump_suit}")
    
    # Test 3: Update hand
    print("\n3. Testing update_my_hand()...")
    test_hand = ['0', '10', '20', '30', '39']
    tracker.update_my_hand(test_hand)
    print(f"   Hand: {[CardMapper.get_card(c) for c in tracker.my_hand]}")
    
    # Test 4: Get cards of suit
    print("\n4. Testing get_my_cards_of_suit()...")
    clubs = tracker.get_my_cards_of_suit('♣')
    print(f"   Clubs in hand: {[CardMapper.get_card(c) for c in clubs]}")
    
    print("\n✓ GameStateTracker tests complete!\n")


# def test_decision_maker():
#     """Test DecisionMaker methods"""
#     print("=" * 60)
#     print("TESTING DECISION MAKER")
#     print("=" * 60)
    
#     tracker = GameStateTracker()
#     tracker.trump_suit = "♠"
#     tracker.my_hand = [0, 1, 2, 10, 20, 30, 35, 37, 38, 39]  # Mix of cards
#     tracker.current_round = 1
    
#     decision_maker = DecisionMaker(tracker)
    
#     # Test 1: choose_deck_cut
#     print("\n1. Testing choose_deck_cut()...")
#     cut = decision_maker.choose_deck_cut()
#     print(f"   Cut position: {cut} (should be 15-25)")
    
#     # Test 2: choose_trump_selection
#     print("\n2. Testing choose_trump_selection()...")
#     choice = decision_maker.choose_trump_selection()
#     print(f"   Trump choice: {choice} (should be 'top' or 'bottom')")
    
#     # Test 3: choose_card (when you implement it)
#     print("\n3. Testing choose_card()...")
#     print("   (Will work once you implement choose_card and helper methods)")
#     # Uncomment when ready:
#     # card = decision_maker.choose_card(tracker.my_hand)
#     # if card:
#     #     print(f"   Chose: {CardMapper.get_card(card)}")
    
#     print("\n✓ DecisionMaker tests complete!\n")


# def run_integration_test():
#     """Full integration test"""
#     print("=" * 60)
#     print("INTEGRATION TEST")
#     print("=" * 60)
#     print("\nSimulating a game scenario...")
    
#     tracker = GameStateTracker()
#     decision_maker = DecisionMaker(tracker)
    
#     # Setup game state
#     mock_state = {
#         'players': [
#             {'name': 'WeakAI', 'position': 'NORTH', 'cards_left': 10},
#             {'name': 'Player2', 'position': 'EAST', 'cards_left': 10},
#             {'name': 'Player3', 'position': 'SOUTH', 'cards_left': 10},
#             {'name': 'Player4', 'position': 'WEST', 'cards_left': 10},
#         ],
#         'teams': {
#             'team1': ['WeakAI', 'Player3'],
#             'team2': ['Player2', 'Player4']
#         },
#         'trump_suit': '♠',
#         'current_round': 5,
#         'round_suit': '♥',
#         'round_plays': [
#             {'player': 'Player2', 'card': '18', 'position': 'EAST'},  # K♥
#             {'player': 'Player3', 'card': '19', 'position': 'SOUTH'},  # A♥ (partner winning!)
#         ],
#         'team_scores': {'team1': 25, 'team2': 20},
#         'current_player': 'WeakAI'
#     }
    
#     tracker.update_from_state(mock_state, 'WeakAI')
#     tracker.update_my_hand(['10', '11', '15', '25', '30', '35', '38', '39'])
    
#     print(f"Trump: {tracker.trump_suit}")
#     print(f"Lead suit: {tracker.lead_suit}")
#     print(f"Partner winning? {tracker.is_partner_winning()}")
#     print(f"Trick points: {tracker.get_trick_points()}")
#     print(f"My hand: {[CardMapper.get_card(c) for c in tracker.my_hand]}")
    
#     # Try to make a decision (when you implement it)
#     print("\nAttempting to choose a card...")
#     # Uncomment when ready:
#     # card = decision_maker.choose_card(tracker.my_hand)
#     # if card:
#     #     print(f"Decision: Play {CardMapper.get_card(card)}")
#     #     print("(Since partner is winning with A♥, should play low card!)")
    
#     print("\n✓ Integration test complete!\n")


if __name__ == "__main__":
    print("\n" + "="*60)
    print(" WEAK AGENT TEST SUITE")
    print("="*60 + "\n")
    
    try:
        test_card_analyzer()
    except Exception as e:
        print(f"❌ CardAnalyzer tests failed: {e}\n")
    
    try:
        test_game_state_tracker()
    except Exception as e:
        print(f"❌ GameStateTracker tests failed: {e}\n")
    
    # try:
    #     test_decision_maker()
    # except Exception as e:
    #     print(f"❌ DecisionMaker tests failed: {e}\n")
    
    # try:
    #     run_integration_test()
    # except Exception as e:
    #     print(f"❌ Integration test failed: {e}\n")
    
    print("="*60)
    print("Testing complete! Fix any errors and re-run.")
    print("="*60)
