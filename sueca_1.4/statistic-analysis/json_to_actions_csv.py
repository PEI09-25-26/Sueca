#!/usr/bin/env python3
"""
Fetch player actions from server and convert to CSV with hand_before and legal_moves
"""
import requests
import csv
import sys
from pathlib import Path


def fetch_actions_from_server(game_id, server_url="http://127.0.0.1:5000"):
    """Fetch actions from server endpoint"""
    try:
        response = requests.get(f"{server_url}/api/actions/{game_id}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get('actions', [])
        else:
            print(f"Server returned {response.status_code}: {response.text}")
            return []
    except Exception as e:
        print(f"Error fetching actions from server: {e}")
        return []


def save_actions_to_csv(actions, output_csv):
    """Save actions to CSV with all fields"""
    
    if not actions:
        print("No actions to save")
        return False
    
    # CSV columns - flatten nested structures
    fieldnames = [
        'timestamp',
        'round_number',
        'player',
        'position',
        'hand_before',
        'legal_moves',
        'chosen_card',
        'cards_in_trick',
        'position_in_trick',
        'lead_suit',
        'trump'
    ]
    
    # Write CSV
    with open(output_csv, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for action in actions:
            row = {
                'timestamp': action.get('timestamp', ''),
                'round_number': action.get('round_number', ''),
                'player': action.get('player', ''),
                'position': action.get('position', ''),
                'hand_before': action.get('hand_before', ''),  # Already JSON from agent
                'legal_moves': action.get('legal_moves', ''),
                'chosen_card': action.get('chosen_card', ''),
                'cards_in_trick': action.get('cards_in_trick', ''),
                'position_in_trick': action.get('position_in_trick', ''),
                'lead_suit': action.get('lead_suit', ''),
                'trump': action.get('trump', '')
            }
            writer.writerow(row)
    
    print(f"✓ Saved {len(actions)} actions to: {output_csv}")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 json_to_actions_csv.py <game_id> [output.csv]")
        print("Example: python3 json_to_actions_csv.py AD9FB5 game_actions.csv")
        sys.exit(1)
    
    game_id = sys.argv[1]
    output_csv = sys.argv[2] if len(sys.argv) > 2 else f"{game_id}_actions.csv"
    
    print(f"Fetching actions for game {game_id}...")
    actions = fetch_actions_from_server(game_id)
    
    if not actions:
        print("No actions found")
        sys.exit(1)
    
    success = save_actions_to_csv(actions, output_csv)
    sys.exit(0 if success else 1)
