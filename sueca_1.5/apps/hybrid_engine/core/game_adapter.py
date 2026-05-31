"""Adapter helpers that perform hybrid-specific operations on hybrid game objects.

These functions keep hybrid-specific logic inside the hybrid_engine package so
the hybrid service owns its gameplay workflow.
"""
from typing import Tuple
import logging
from apps.hybrid_engine.card_mapper import CardMapper
from apps.hybrid_engine.core.game_core import EVENT_DISPATCHER

from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def play_card_hybrid_capture(game, player_id, card_str, force_renuncia=False) -> Tuple[bool, str]:
    """Perform a hybrid-style capture play on the provided `game` instance.

    This mirrors the previous `play_card_hybrid_capture` method that lived inside
    the virtual engine, but keeps the implementation within hybrid_engine.
    """
    card = None
    trick_complete = False

    with game._play_lock:
        player = game.get_player(player_id)
        if not player:
            return False, 'Player not found'

        if game.round_resolving or len(game.round_plays) >= 4:
            return False, 'Round resolving, wait for next turn'

        if game.current_player != player:
            waiting_for = game.current_player.player_name if game.current_player else 'next player'
            return False, f'Not your turn! Waiting for {waiting_for}'

        if any(play.get('player_id') == player.player_id for play in game.round_plays):
            return False, 'You already played this round'

        try:
            card = int(card_str)
        except (TypeError, ValueError):
            return False, 'Invalid card'

        if force_renuncia:
            # End the game immediately and give 4 points to the innocent team
            game.phase = 'finished'
            game.game_started = False
            
            innocent_team_idx = 1 if player in game.teams[0] else 0
            
            # Opposing team gets 4 match points
            game.match_points['team1' if innocent_team_idx == 0 else 'team2'] += 4
            
            match_entry = {
                'match_number': game.current_match_number,
                'winner_team': 'team1' if innocent_team_idx == 0 else 'team2',
                'winner_label': 'Team 1 (N/S)' if innocent_team_idx == 0 else 'Team 2 (E/W)',
                'team_scores': {'team1': game.team_scores[0], 'team2': game.team_scores[1]},
                'finished_at': datetime.now(timezone.utc).isoformat(),
            }
            game.match_history.append(match_entry)
            # Firestore stats publishing exists in the virtual engine GameState
            # but may not be present in all GameState implementations used
            # by hybrid_engine. Guard the call to avoid an AttributeError.
            if hasattr(game, "_publish_match_stats"):
                try:
                    game._publish_match_stats(match_entry)
                except Exception:
                    logger.exception('Failed to publish match stats for game %s', game.game_id)
            
            # Notify everyone
            game._push_state('renuncia')
            return True, f'Renúncia penalizada. {match_entry["winner_label"]} ganhou o jogo!'

        # Normal play continues if no renuncia
        if card in player.hand:
            player.hand.remove(card)

        game.round_plays.append({
            'player_id': player.player_id,
            'player_name': player.player_name,
            'card': str(card),
            'position': str(player.position),
        })

        if len(game.round_plays) == 1:
            game.round_suit = CardMapper.get_card_suit(card)

        logger.info('%s played %s in game %s', player.player_name, CardMapper.get_card(card), game.game_id)

        current_index = game.turn_order.index(player)
        if current_index + 1 < len(game.turn_order):
            game.current_player = game.turn_order[current_index + 1]

        trick_complete = len(game.round_plays) == 4
        if trick_complete:
            game._schedule_round_resolution()

    event = {
        'type': 'card_played',
        'player': player.player_name,
        'player_id': player.player_id,
        'card': str(card),
        'state': game.get_state(),
        'game_id': game.game_id,
    }
    EVENT_DISPATCHER.dispatch(event)

    # Keep MQTT/state consumers in sync after every accepted play.
    game._push_state('card_played')
    return True, f'Played {CardMapper.get_card(card)}'
