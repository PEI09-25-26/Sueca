"""
RandomAgent - AI agent that plays Sueca using heuristics
"""
from ...clients.client import GameClient
from ...game_state_tracker import GameStateTracker
from ...card_mapper import CardMapper
from .decision_maker import DecisionMaker
import random
import time


class RandomAgent(GameClient):
    """
    AI agent that automatically plays Sueca.
    Inherits from GameClient to get server communication methods.
    """
    
    def __init__(self, agent_name="RandomAI", game_id=None, position=None):
        super().__init__()
        self.agent_name = agent_name
        self.state_tracker = GameStateTracker()
        self.decision_maker = DecisionMaker(self.state_tracker)
        self.auto_play = True
        self.think_time = 1.0
        self.player_id = None
        self.game_id = game_id
        self.position = position
    
    def run(self):
        """
        Main agent loop - overrides GameClient.run()
        This is the main entry point when you start the agent.
        """
        # Join the game
        success, message, player_id = self.join_game(self.player_name, self.game_id, self.position)
        if success:
            self.player_id = player_id
        if not success:
            print(f"[ERROR] Failed to join game: {message}")
            return
        
        self.player_name = self.agent_name
        print(f"RandomAgent joined as {self.player_name}\n")
        
        while True:
            state = self.get_status()
            if state is None:
                time.sleep(1)
                continue
            
            # Update state tracker
            self.state_tracker.update_from_state(state, self.player_name)
            
            # Update hand
            hand = self.get_hand()
            self.state_tracker.update_my_hand(hand)
            
            # Handle deck cutting
            if state["phase"] == "deck_cutting":
                self._handle_deck_cutting(state)
            
            # Handle trump selection
            elif state["phase"] == "trump_selection":
                self._handle_trump_selection(state)
            
            # Handle playing turn
            elif state["phase"] == "playing":
                self._handle_playing_turn(state)
            
            # Game finished
            elif state["phase"] == "finished":
                team1 = state.get("team_scores", {}).get("team1", 0)
                team2 = state.get("team_scores", {}).get("team2", 0)
                print(f"Game finished! Team 1: {team1} | Team 2: {team2}")
                break
            time.sleep(random.uniform(0.5, 1.0))
    
    def _handle_deck_cutting(self, state):
        """
        Handle if we're NORTH and need to cut the deck.
        """
        if state.get("north_player") != self.player_name:
            return
        
        cut = self.decision_maker.choose_deck_cut()
        success, msg = self.cut_deck(cut)
        if success:
            print(f"Agent cutting deck at {cut}")
        else:
            print(f"[ERROR] Cutting deck failed: {msg}")
    
    def _handle_trump_selection(self, state):
        """
        Handle if we're WEST and need to choose trump.
        """
        if state.get("west_player") != self.player_name:
            return
        
        choice = self.decision_maker.choose_trump_selection()
        success, msg = self.select_trump(choice)
        if success:
            print(f"Agent selecting {choice} card for trump")
        else:
            print(f"[ERROR] Selecting trump failed: {msg}")
        
    
    def _handle_playing_turn(self, state):
        """
        Handle if it's our turn to play a card.
        """
        if state.get("current_player") != self.player_name or not self.state_tracker.my_hand:
            return
        
        time.sleep(self.think_time)  # Simulate thinking
        
        card = self.decision_maker.choose_card(self.state_tracker.my_hand)
        if card is None:
            return
        
        card_str = str(card)
        success, msg = self.play_card(card_str)
        if success:
            card_display = CardMapper.get_card(card)
            print(f"Agent played: {card_display}")
        else:
            print(f"[ERROR] Playing card failed: {msg}")