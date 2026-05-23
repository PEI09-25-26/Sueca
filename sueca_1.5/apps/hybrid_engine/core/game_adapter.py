"""Adapter helpers that perform hybrid-specific operations on hybrid game objects.

These functions keep hybrid-specific logic inside the hybrid_engine package so
the hybrid service owns its gameplay workflow.
"""
from typing import Tuple
import logging
import threading
from apps.hybrid_engine.card_mapper import CardMapper

logger = logging.getLogger(__name__)


def play_card_hybrid_capture(game, player_id, card_str) -> Tuple[bool, str]:
    """Perform a hybrid-style capture play on the provided `game` instance.

    This mirrors the previous `play_card_hybrid_capture` method that lived inside
    the virtual engine, but keeps the implementation within hybrid_engine.
    """
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

    # Keep MQTT/state consumers in sync after every accepted play.
    if len(game.round_plays) == 4:
        game.current_player = None
        game.round_resolving = True
        game.round_timer = threading.Timer(1.69, game._finish_round)
        game.round_timer.start()

    game._push_state('card_played')
    return True, f'Played {CardMapper.get_card(card)}'
