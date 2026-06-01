"""Hybrid game coordinator.

Keeps hybrid-only runtime state by game room:
- roles (real/virtual) and host
- virtual dealing progress (10 cards each)
- pending virtual card waiting for host physical confirmation

This module is intentionally simple and stateful for fast iteration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, List, Optional


@dataclass
class PendingVirtualPlay:
    player_id: str
    card_id: int


@dataclass
class HybridRoomState:
    game_id: str
    host_player_id: Optional[str] = None
    player_roles: Dict[str, str] = field(default_factory=dict)  # player_id -> real|virtual
    cards_per_virtual: int = 10
    virtual_order: List[str] = field(default_factory=list)
    virtual_hands: Dict[str, List[int]] = field(default_factory=dict)
    pending_virtual_play: Optional[PendingVirtualPlay] = None


class HybridGameCoordinator:
    def __init__(self) -> None:
        self._lock = Lock()
        self._rooms: Dict[str, HybridRoomState] = {}

    def _get_room(self, game_id: str) -> HybridRoomState:
        room = self._rooms.get(game_id)
        if room is None:
            room = HybridRoomState(game_id=game_id)
            self._rooms[game_id] = room
        return room

    def register_player(self, game_id: str, player_id: str, role: str, is_host: bool) -> HybridRoomState:
        role = (role or "real").strip().lower()
        if role not in ("real", "virtual"):
            role = "real"

        with self._lock:
            room = self._get_room(game_id)
            room.player_roles[player_id] = role
            if is_host:
                room.host_player_id = player_id
            return room

    def get_room_state(self, game_id: str) -> HybridRoomState:
        with self._lock:
            return self._get_room(game_id)

    def reset_deal(self, game_id: str, host_player_id: str, virtual_player_ids: List[str], cards_per_virtual: int) -> HybridRoomState:
        with self._lock:
            room = self._get_room(game_id)
            room.host_player_id = host_player_id
            room.cards_per_virtual = max(1, int(cards_per_virtual))
            room.virtual_order = list(dict.fromkeys(virtual_player_ids))
            room.virtual_hands = {pid: [] for pid in room.virtual_order}
            room.pending_virtual_play = None

            for pid in room.virtual_order:
                room.player_roles[pid] = "virtual"
            if host_player_id:
                room.player_roles[host_player_id] = "real"

            return room

    def deal_next_target(self, game_id: str) -> Optional[str]:
        with self._lock:
            room = self._get_room(game_id)
            for pid in room.virtual_order:
                if len(room.virtual_hands.get(pid, [])) < room.cards_per_virtual:
                    return pid
            return None

    def add_deal_card(self, game_id: str, target_player_id: str, card_id: int) -> tuple[bool, str, HybridRoomState]:
        with self._lock:
            room = self._get_room(game_id)
            if target_player_id not in room.virtual_hands:
                return False, "Target is not configured as virtual", room

            hand = room.virtual_hands[target_player_id]
            if len(hand) >= room.cards_per_virtual:
                return False, "Target already has all cards", room

            all_cards = [c for cards in room.virtual_hands.values() for c in cards]
            if card_id in all_cards:
                return False, "Card already assigned to another virtual player", room

            hand.append(int(card_id))
            return True, "Card assigned", room

    def get_player_hand(self, game_id: str, player_id: str) -> List[int]:
        with self._lock:
            room = self._get_room(game_id)
            return list(room.virtual_hands.get(player_id, []))

    def select_virtual_card(self, game_id: str, player_id: str, card_id: int) -> tuple[bool, str, HybridRoomState]:
        with self._lock:
            room = self._get_room(game_id)
            if player_id not in room.virtual_hands:
                return False, "Only virtual players can select cards", room

            hand = room.virtual_hands.get(player_id, [])
            if int(card_id) not in hand:
                return False, "Card not available in virtual hand", room

            if room.pending_virtual_play is not None:
                return False, "There is already a pending virtual play", room

            room.pending_virtual_play = PendingVirtualPlay(player_id=player_id, card_id=int(card_id))
            return True, "Card selected. Waiting host confirmation", room

    def get_pending_virtual_play(self, game_id: str) -> Optional[PendingVirtualPlay]:
        with self._lock:
            room = self._get_room(game_id)
            if room.pending_virtual_play is None:
                return None
            return PendingVirtualPlay(
                player_id=room.pending_virtual_play.player_id,
                card_id=room.pending_virtual_play.card_id,
            )

    def confirm_play_success(self, game_id: str, player_id: str, card_id: int) -> HybridRoomState:
        with self._lock:
            room = self._get_room(game_id)

            if player_id in room.virtual_hands:
                hand = room.virtual_hands[player_id]
                if int(card_id) in hand:
                    hand.remove(int(card_id))

            if room.pending_virtual_play is not None:
                if room.pending_virtual_play.player_id == player_id and room.pending_virtual_play.card_id == int(card_id):
                    room.pending_virtual_play = None

            return room

    def to_payload(self, room: HybridRoomState, players_by_id: Dict[str, dict]) -> dict:
        payload_roles = {pid: "real" for pid in players_by_id.keys()}
        payload_roles.update(room.player_roles)

        # Before deal reset, virtual_order can still be empty even when players are
        # already registered as virtual. Expose those players so clients do not
        # treat dealing as completed prematurely.
        virtual_ids = list(room.virtual_order)
        if not virtual_ids:
            virtual_ids = [
                pid for pid, role in payload_roles.items()
                if role == "virtual" and pid in players_by_id
            ]

        virtual_players = []
        for pid in virtual_ids:
            pmeta = players_by_id.get(pid, {})
            hand = room.virtual_hands.get(pid, [])
            virtual_players.append({
                "player_id": pid,
                "player_name": pmeta.get("name", "Unknown"),
                "position": pmeta.get("position", ""),
                "cards": hand,
                "cards_count": len(hand),
            })

        pending = None
        if room.pending_virtual_play is not None:
            pmeta = players_by_id.get(room.pending_virtual_play.player_id, {})
            pending = {
                "player_id": room.pending_virtual_play.player_id,
                "player_name": pmeta.get("name", "Unknown"),
                "position": pmeta.get("position", ""),
                "card_id": room.pending_virtual_play.card_id,
            }

        return {
            "game_id": room.game_id,
            "host_player_id": room.host_player_id,
            "cards_per_virtual": room.cards_per_virtual,
            "virtual_order": virtual_ids,
            "player_roles": payload_roles,
            "virtual_players": virtual_players,
            "pending_virtual_play": pending,
            "deal_done": all(vp["cards_count"] >= room.cards_per_virtual for vp in virtual_players) if virtual_players else True,
        }
