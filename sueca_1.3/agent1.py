"""
WeakAgent - AI agent that plays Sueca using heuristics
DO THIS CLASS LAST (orchestrates everything)
"""
from client import GameClient
from game_state_tracker import GameStateTracker
from decision_maker import DecisionMaker
import time


class WeakAgent(GameClient):
    """
    AI agent that automatically plays Sueca.
    Inherits from GameClient to get server communication methods.
    """
    
    def __init__(self, agent_name="WeakAI"):
        """
        Initialize the agent with all components.
        
        TODO:
        1. Call super().__init__() to initialize GameClient
        2. Store agent_name
        3. Create GameStateTracker instance → self.state_tracker
        4. Create DecisionMaker instance → self.decision_maker
           (pass state_tracker to it!)
        5. Set self.auto_play = True
        6. Set self.think_time = 1.0 (seconds to wait before playing)
        """
        super().__init__()
        self.agent_name = agent_name
        self.state_tracker = GameStateTracker()
        self.decision_maker = DecisionMaker(self.state_tracker)
        self.auto_play = True
        self.think_time = 1.0
    
    def run(self):
        """
        Main agent loop - overrides GameClient.run()
        This is the main entry point when you start the agent.
        
        TODO:
        1. Join the game:
           - success, msg = self.join_game(self.agent_name)
           - If not successful, print error and return
        2. Set self.player_name = self.agent_name
        3. Print "Agent joined as {name}"
        4. Start main game loop (while True):
           a) Get status: state = self.get_status()
           b) If state is None, sleep 1 sec and continue
           c) Update state tracker: self.state_tracker.update_from_state(state, self.player_name)
           d) Update hand: hand = self.get_hand()
                         self.state_tracker.update_my_hand(hand)
           e) Check phase and handle:
              - if state['phase'] == 'deck_cutting': 
                  self._handle_deck_cutting(state)
              - elif state['phase'] == 'trump_selection':
                  self._handle_trump_selection(state)
              - elif state['phase'] == 'playing':
                  self._handle_playing_turn(state)
              - elif state['phase'] == 'finished':
                  print game result and break
           f) Sleep for 0.5-1 second
        5. After loop ends, print final scores
        
        Hint: Look at client.py to see available methods!
        """
        pass
    
    def _handle_deck_cutting(self, state):
        """
        Handle if we're NORTH and need to cut the deck.
        
        Args:
            state: current game state dict
        
        TODO:
        1. Check if state['north_player'] == self.player_name
        2. If it's us:
           - Get cut position: cut = self.decision_maker.choose_deck_cut()
           - Cut the deck: self.cut_deck(self.player_name, cut)
           - Print message: "Agent cutting deck at {cut}"
        """
        pass
    
    def _handle_trump_selection(self, state):
        """
        Handle if we're WEST and need to choose trump.
        
        Args:
            state: current game state dict
        
        TODO:
        1. Check if state['west_player'] == self.player_name
        2. If it's us:
           - Get choice: choice = self.decision_maker.choose_trump_selection()
           - Select trump: self.select_trump(self.player_name, choice)
           - Print message: "Agent selecting {choice} card for trump"
        """
        pass
    
    def _handle_playing_turn(self, state):
        """
        Handle if it's our turn to play a card.
        
        Args:
            state: current game state dict
        
        TODO:
        1. Check if state['current_player'] == self.player_name
        2. If it's our turn AND we have cards:
           - Sleep for self.think_time (simulate thinking)
           - Get card: card = self.decision_maker.choose_card(self.state_tracker.my_hand)
           - If card is None, return (shouldn't happen)
           - Convert to string: card_str = str(card)
           - Play it: success, msg = self.play_card(self.player_name, card_str)
           - Print what we played (use CardMapper to show nice format)
        """
        pass