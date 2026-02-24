"""
Simple CLI client for Sueca game
Auto-updates every 2 seconds, always shows hand
"""

import requests
import os
import time
import sys
from threading import Thread, Lock
from card_mapper import CardMapper

SERVER_URL = 'http://localhost:5000'


class GameClient:
    def __init__(self):
        self.player_name = None
        self.running = True
        self.last_state = None
        self.my_hand = []
        self.display_lock = Lock()
        self.pause_updates = False  # Pause updates when waiting for user input
        
    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('clear' if os.name != 'nt' else 'cls')
    
    def get_status(self):
        """Get game status from server"""
        try:
            response = requests.get(f'{SERVER_URL}/api/status', timeout=1)
            return response.json()
        except:
            return None
    
    def join_game(self, name):
        """Join the game"""
        try:
            response = requests.post(f'{SERVER_URL}/api/join', 
                                    json={'name': name}, timeout=2)
            data = response.json()
            return data['success'], data['message']
        except Exception as e:
            return False, f"Error: {e}"
    
    def get_hand(self):
        """Get player's hand"""
        try:
            response = requests.get(f'{SERVER_URL}/api/hand/{self.player_name}', timeout=1)
            data = response.json()
            if data['success']:
                return data['hand']
            return []
        except:
            return []
    
    def cut_deck(self, index):
        """Cut the deck at given index (1-40)"""
        try:
            response = requests.post(f'{SERVER_URL}/api/cut_deck',
                                    json={'player': self.player_name, 'index': index}, 
                                    timeout=2)
            data = response.json()
            return data['success'], data['message']
        except Exception as e:
            return False, f"Error: {e}"
    
    def select_trump(self, choice):
        """Select trump card (top or bottom)"""
        try:
            response = requests.post(f'{SERVER_URL}/api/select_trump',
                                    json={'player': self.player_name, 'choice': choice}, 
                                    timeout=2)
            data = response.json()
            return data['success'], data['message']
        except Exception as e:
            return False, f"Error: {e}"
    
    def play_card(self, card):
        """Play a card"""
        try:
            response = requests.post(f'{SERVER_URL}/api/play',
                                    json={'player': self.player_name, 'card': card}, 
                                    timeout=2)
            data = response.json()
            return data['success'], data['message']
        except Exception as e:
            return False, f"Error: {e}"
    
    def display_game(self, force=False):
        """Display current game state"""
        # Don't refresh if updates are paused (unless forced)
        if self.pause_updates and not force:
            return
        
        with self.display_lock:
            state = self.get_status()
            if not state:
                return
            
            self.clear_screen()
            
            print("=" * 70)
            print(f"  SUECA - Player: {self.player_name}")
            print("=" * 70)
            print()
            
            # Game info
            print(f"Players: {state['player_count']}/4  |  ", end="")
            
            # Show phase-specific status
            if state['phase'] == 'waiting':
                print("Game: WAITING FOR PLAYERS")
            elif state['phase'] == 'deck_cutting':
                print("Game: DECK CUTTING  |  ", end="")
                print(f"NORTH player ({state['north_player']}) must cut the deck!")
            elif state['phase'] == 'trump_selection':
                print("Game: TRUMP SELECTION  |  ", end="")
                print(f"WEST player ({state['west_player']}) must choose trump!")
            elif state['phase'] == 'playing':
                print(f"Round: {state['current_round']}/10  |  ", end="")
                if state['trump']:
                    # Convert trump card to visual representation
                    try:
                        trump_num = int(state['trump'])
                        trump_display = CardMapper.get_card(trump_num)
                    except:
                        trump_display = state['trump']
                    print(f"Trump: {trump_display}")
                else:
                    print()
            elif state['phase'] == 'finished':
                print("Game: FINISHED!")
            else:
                print(f"Game: {state['phase'].upper()}")
            
            print()
            
            # Players list
            if state['players']:
                print("PLAYERS:")
                for p in state['players']:
                    marker = ">>> " if p['name'] == self.player_name else "    "
                    print(f"{marker}{p['name']:15} ({p['position']:5}) - {p['cards_left']} cards")
                print()
            
            # Teams
            if state['teams']['team1']:
                print(f"Team 1 (N/S): {', '.join(state['teams']['team1'])}", end="")
                if state.get('team_scores'):
                    print(f" - {state['team_scores']['team1']} points")
                else:
                    print()
                print(f"Team 2 (E/W): {', '.join(state['teams']['team2'])}", end="")
                if state.get('team_scores'):
                    print(f" - {state['team_scores']['team2']} points")
                else:
                    print()
                print()
            
            # Current turn indicator
            if state['phase'] == 'playing' and state.get('current_player'):
                print(f">>> TURN: {state['current_player']}", end="")
                if state['current_player'] == self.player_name:
                    print(" (YOU!)", end="")
                if state.get('round_suit'):
                    print(f"  |  Round suit: {state['round_suit']}", end="")
                print()
                print()
            
            # Current round
            if state['round_plays']:
                print("CARDS ON TABLE:")
                for play in state['round_plays']:
                    # Convert card to visual representation
                    try:
                        card_num = int(play['card'])
                        card_display = CardMapper.get_card(card_num)
                    except:
                        card_display = play['card']
                    
                    position_str = f"({play.get('position', '?')})" if play.get('position') else ""
                    print(f"  {play['player']:15} {position_str:7} -> {card_display}")
                print()
            
            # My hand
            self.my_hand = self.get_hand()
            if self.my_hand:
                print("YOUR HAND:")
                for i, card_str in enumerate(self.my_hand, 1):
                    # Convert card number to visual representation
                    try:
                        card_num = int(card_str)
                        card_display = CardMapper.get_card(card_num)
                    except:
                        card_display = card_str
                    print(f"  [{i}] {card_display}")
                print()
            
            # Commands
            print("-" * 70)
            if state['phase'] == 'deck_cutting' and state['north_player'] == self.player_name:
                print("YOU are NORTH! Type a number (1-40) to cut the deck, or 'quit' to exit")
            elif state['phase'] == 'deck_cutting':
                print(f"Waiting for {state['north_player']} (NORTH) to cut the deck...")
                print("Type 'quit' to exit")
            elif state['phase'] == 'trump_selection' and state['west_player'] == self.player_name:
                print("YOU are WEST! Type 'top' or 'bottom' to select trump card, or 'quit' to exit")
            elif state['phase'] == 'trump_selection':
                print(f"Waiting for {state['west_player']} (WEST) to select trump...")
                print("Type 'quit' to exit")
            elif state['phase'] == 'playing':
                if state.get('current_player') == self.player_name and self.my_hand:
                    print("YOUR TURN! Type card number to play (e.g., '1') or 'quit' to exit")
                    if state.get('round_suit'):
                        print(f"Note: You must follow suit {state['round_suit']} if you have it!")
                elif self.my_hand:
                    print(f"Waiting for {state.get('current_player', '?')} to play...")
                    print("Type 'quit' to exit")
                else:
                    print("Type 'quit' to exit")
            elif state['phase'] == 'finished':
                team1_score = state.get('team_scores', {}).get('team1', 0)
                team2_score = state.get('team_scores', {}).get('team2', 0)
                if team1_score > team2_score:
                    print(f"🏆 TEAM 1 WINS! ({team1_score} vs {team2_score})")
                elif team2_score > team1_score:
                    print(f"🏆 TEAM 2 WINS! ({team2_score} vs {team1_score})")
                else:
                    print(f"TIE! ({team1_score} vs {team2_score})")
                print("Type 'quit' to exit")
            else:
                print("Type 'quit' to exit")
            print("> ", end="", flush=True)
    
    def auto_update_thread(self):
        """Thread that auto-updates the display"""
        while self.running:
            try:
                if not self.pause_updates:
                    self.display_game()
                time.sleep(2)
            except:
                pass
    
    def run(self):
        """Main client loop"""
        self.clear_screen()
        print("=" * 70)
        print("  SUECA")
        print("=" * 70)
        print()
        
        # Check server
        print("Connecting to server...")
        if not self.get_status():
            print("[ERROR] Cannot connect to server!")
            print("        Make sure the server is running: python3 server.py")
            return
        
        print("[OK] Connected\n")
        
        # Get player name
        self.player_name = input("Enter your name: ").strip()
        if not self.player_name:
            print("[ERROR] Name required!")
            return
        
        # Join game
        success, message = self.join_game(self.player_name)
        if not success:
            print(f"[ERROR] {message}")
            return
        
        print(f"[OK] {message}")
        print("\nWhen 4 players join:")
        print("  1. NORTH player cuts the deck (choose index 1-40)")
        print("  2. WEST player selects trump (choose 'top' or 'bottom')")
        print("  3. Cards are dealt and game starts!")
        print("\nYour hand will update automatically every 2 seconds.\n")
        time.sleep(2)
        
        # Start auto-update thread
        update_thread = Thread(target=self.auto_update_thread, daemon=True)
        update_thread.start()
        
        # Main input loop
        try:
            while self.running:
                # Check current state to decide if we should pause updates
                state = self.get_status()
                if state:
                    # Pause updates when it's my turn to do something
                    is_my_action = (
                        (state.get('phase') == 'deck_cutting' and state.get('north_player') == self.player_name) or
                        (state.get('phase') == 'trump_selection' and state.get('west_player') == self.player_name) or
                        (state.get('phase') == 'playing' and state.get('current_player') == self.player_name)
                    )
                    
                    # If it's my action, pause updates and show one last refresh
                    if is_my_action:
                        self.pause_updates = True
                        time.sleep(0.1)  # Small delay to ensure thread doesn't interfere
                        self.display_game(force=True)  # Force one last update before input
                
                user_input = input().strip().lower()
                
                if user_input == 'quit':
                    self.running = False
                    print("\nGoodbye!")
                    break
                
                # Check game state
                if not state:
                    continue
                
                # Handle deck cutting phase
                if state.get('phase') == 'deck_cutting':
                    if state.get('north_player') == self.player_name:
                        if user_input.isdigit():
                            cut_index = int(user_input)
                            if 1 <= cut_index <= 40:
                                success, message = self.cut_deck(cut_index)
                                with self.display_lock:
                                    if success:
                                        print(f"\n[SUCCESS] {message}")
                                        self.pause_updates = False  # Resume updates
                                    else:
                                        print(f"\n[ERROR] {message}")
                                    print("> ", end="", flush=True)
                            else:
                                with self.display_lock:
                                    print("\n[ERROR] Cut index must be between 1 and 40")
                                    print("> ", end="", flush=True)
                        else:
                            with self.display_lock:
                                print("\n[ERROR] Please type a number between 1 and 40")
                                print("> ", end="", flush=True)
                    continue
                
                # Handle trump selection phase
                if state.get('phase') == 'trump_selection':
                    if state.get('west_player') == self.player_name:
                        if user_input in ['top', 'bottom']:
                            success, message = self.select_trump(user_input)
                            with self.display_lock:
                                if success:
                                    print(f"\n[SUCCESS] {message}")
                                    self.pause_updates = False  # Resume updates
                                else:
                                    print(f"\n[ERROR] {message}")
                                print("> ", end="", flush=True)
                        else:
                            with self.display_lock:
                                print("\n[ERROR] Please type 'top' or 'bottom'")
                                print("> ", end="", flush=True)
                    continue
                
                # Try to play card by number
                if user_input.isdigit():
                    # Check if it's player's turn
                    if state.get('current_player') != self.player_name:
                        with self.display_lock:
                            print(f"\n[ERROR] Not your turn! Wait for {state.get('current_player', '?')}")
                            print("> ", end="", flush=True)
                        continue
                    
                    idx = int(user_input) - 1
                    if 0 <= idx < len(self.my_hand):
                        card = self.my_hand[idx]
                        success, message = self.play_card(card)
                        if success:
                            self.pause_updates = False  # Resume updates after successful play
                        else:
                            with self.display_lock:
                                print(f"\n[ERROR] {message}")
                                print("> ", end="", flush=True)
                        # If success, next update will show the change
                    else:
                        with self.display_lock:
                            print("\n[ERROR] Invalid card number!")
                            print("> ", end="", flush=True)
                
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
        
        self.running = False


if __name__ == '__main__':
    client = GameClient()
    client.run()
