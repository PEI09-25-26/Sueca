"""Shared hybrid coordinator hooks to avoid circular imports between route modules."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional

from apps.hybrid_engine.core.hybrid_game_coordinator import HybridGameCoordinator

if TYPE_CHECKING:
    from apps.hybrid_engine.core.hybrid_referee import HybridReferee

hybrid_coordinator: Optional[HybridGameCoordinator] = None
hybrid_referee: Optional["HybridReferee"] = None
_push_hybrid_state_fn: Optional[Callable] = None


def configure(
    coordinator: HybridGameCoordinator,
    push_state_fn: Callable,
    referee: Optional["HybridReferee"] = None,
) -> None:
    global hybrid_coordinator, hybrid_referee, _push_hybrid_state_fn
    hybrid_coordinator = coordinator
    hybrid_referee = referee
    _push_hybrid_state_fn = push_state_fn


def reset_renunciation_tracking(game_id: str) -> None:
    """Clear suit-void history when a new match starts or the game is fully reset."""
    if hybrid_referee is not None:
        hybrid_referee.reset_game(game_id)


def assign_trump_to_dealer(game) -> None:
    """Add captured trump to the dealer/selector virtual hand when hybrid deal starts."""
    if hybrid_coordinator is None or game is None or game.trump_card is None:
        return

    selector = game._get_player_by_position(game._current_dealer_position())
    if not selector:
        return

    hybrid_coordinator.assign_trump_to_selector(
        game.game_id,
        int(game.trump_card),
        selector.player_id,
    )


def after_trump_captured(game, host_player_id: str) -> None:
    """Prepare hybrid deal phase after host captures trump (no auto-deal for bots)."""
    if hybrid_coordinator is None or game is None:
        return

    game_id = game.game_id
    room = hybrid_coordinator.get_room_state(game_id)
    registered_virtual_ids = [
        pid
        for pid, role in room.player_roles.items()
        if role == "virtual" and game.get_player(pid) is not None and pid != host_player_id
    ]
    room = hybrid_coordinator.reset_deal(
        game_id=game_id,
        host_player_id=host_player_id,
        virtual_player_ids=registered_virtual_ids,
        cards_per_virtual=room.cards_per_virtual or 10,
    )

    assign_trump_to_dealer(game)
    room = hybrid_coordinator.get_room_state(game_id)

    if _push_hybrid_state_fn is not None:
        _push_hybrid_state_fn(game, room)
