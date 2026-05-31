"""Shared hybrid coordinator hooks to avoid circular imports between route modules."""

from __future__ import annotations

from typing import Callable, Optional

from apps.hybrid_engine.core.hybrid_game_coordinator import HybridGameCoordinator

hybrid_coordinator: Optional[HybridGameCoordinator] = None
_push_hybrid_state_fn: Optional[Callable] = None


def configure(coordinator: HybridGameCoordinator, push_state_fn: Callable) -> None:
    global hybrid_coordinator, _push_hybrid_state_fn
    hybrid_coordinator = coordinator
    _push_hybrid_state_fn = push_state_fn


def after_trump_dealt(game) -> None:
    if hybrid_coordinator is None or game is None:
        return
    room = hybrid_coordinator.sync_bot_hands_from_game(game.game_id, game)
    room = hybrid_coordinator.maybe_auto_finalize_bot_deal(game.game_id)
    if _push_hybrid_state_fn is not None:
        _push_hybrid_state_fn(game, room)
