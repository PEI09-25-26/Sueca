"""In-process match simulator for fast, headless batch runs.

This runs the `GameState` directly in-process using the existing decision makers
from each agent package and returns structured data suitable for extraction.
"""
from typing import List, Dict, Any
import uuid
import time

from ..card_mapper import CardMapper
from copy import deepcopy

from .game_core import GameState


_DEFAULT_BOTS = [
    {"name": "Rita", "position": "NORTH", "difficulty": "random"},
    {"name": "Alyssa", "position": "EAST", "difficulty": "weak"},
    {"name": "Ava", "position": "SOUTH", "difficulty": "average"},
    {"name": "Serana", "position": "WEST", "difficulty": "random"},
]


def _decision_maker_for(difficulty, tracker):
    difficulty = (difficulty or "random").lower()
    if difficulty.startswith("weak"):
        from ..agents.weak_agent.decision_maker import DecisionMaker as WeakDecision

        return WeakDecision(tracker)
    if difficulty.startswith("average"):
        from ..agents.average_agent.decision_maker import DecisionMaker as AvgDecision

        return AvgDecision(tracker)
    if difficulty.startswith("smart"):
        from ..agents.smart_agent.decision_maker import DecisionMaker as SmartDecision

        return SmartDecision(tracker)

    # default/random
    from ..agents.random_agent.decision_maker import DecisionMaker as RandDecision

    return RandDecision(tracker)


def simulate_match(game_number: int, bots: List[Dict[str, Any]] = None, fast_mode: bool = True) -> Dict[str, Any]:
    from ..positions import Positions
    bots_payload = bots or _DEFAULT_BOTS
    game_id = f"INPROC_{uuid.uuid4().hex[:6].upper()}"

    game = GameState(game_id)
    game.set_fast_mode(fast_mode)

    # Rotate starting player: Game 1 -> South, Game 2 -> East, Game 3 -> North, Game 4 -> West (and repeat)
    rotation = [Positions.SOUTH, Positions.EAST, Positions.NORTH, Positions.WEST]
    game.starting_player_position = rotation[(game_number - 1) % 4]

    # Add players
    for b in bots_payload:
        name = b.get("name")
        pos = b.get("position")
        game.add_player(name, pos)

    # Create trackers and decision makers per player name
    trackers = {}
    decision_makers = {}
    for p in game.players:
        from ..game_state_tracker import GameStateTracker

        t = GameStateTracker()
        t.player_name = p.player_name
        trackers[p.player_name] = t
        # Map difficulty by name
        entry = next((x for x in bots_payload if x.get("name") == p.player_name), None)
        diff = entry.get("difficulty") if entry else "random"
        decision_makers[p.player_name] = _decision_maker_for(diff, t)

    timeline = []
    action_data = []
    round_data = {}

    # Deck cutting
    if game.phase == "deck_cutting":
        cutter_pos = game._current_cutter_position()
        cutter = next((pl for pl in game.players if pl.position == cutter_pos), None)
        if cutter:
            dm = decision_makers.get(cutter.player_name)
            if dm:
                cut = dm.choose_deck_cut() if hasattr(dm, "choose_deck_cut") else 1
                game.cut_deck(cutter.player_id, cut)
                timeline.append({"ts": time.time(), "phase": game.phase, "event": "deck_cut"})

    # Trump selection
    if game.phase == "trump_selection":
        dealer_pos = game._current_dealer_position()
        dealer = next((pl for pl in game.players if pl.position == dealer_pos), None)
        if dealer:
            dm = decision_makers.get(dealer.player_name)
            choice = dm.choose_trump_selection() if hasattr(dm, "choose_trump_selection") else "top"
            game.select_trump(dealer.player_id, choice)
            timeline.append({"ts": time.time(), "phase": game.phase, "event": "trump_selected", "choice": choice})

    # Play until finished
    while game.phase != "finished":
        state = deepcopy(game.get_state())
        # initialize round entry at start of a round
        current_round = int(state.get("current_round") or 0)
        round_key = f"round_{current_round}" if current_round else None
        if round_key and round_key not in round_data:
            round_data[f"round_{current_round}"] = {
                "points": None,
                "team_scores_before": deepcopy(state.get("team_scores", {})),
                "team_scores_after": None,
                "cards_played": [],
                "bot_perception": {},
                "reasoning_protocol": {},
                "round_suit": state.get("round_suit"),
                "winner_team": None,
                "winner_player": None,
                "winner_id": None,
            }
        # Find current player
        cur_name = state.get("current_player_name") or state.get("current_player")
        if not cur_name:
            # Avoid infinite loop
            break

        player = next((pl for pl in game.players if pl.player_name == cur_name), None)
        if not player:
            break

        # Update tracker and hand
        t = trackers.get(player.player_name)
        if t:
            t.update_from_state(state, player.player_name)
            t.update_my_hand([str(c) for c in player.hand])

        dm = decision_makers.get(player.player_name)
        if not dm:
            break

        # snapshot hand (ints) and lead/trump
        hand_before = list(t.my_hand) if t and getattr(t, "my_hand", None) is not None else []
        lead_suit = t.lead_suit if t and getattr(t, "lead_suit", None) is not None else state.get("round_suit")

        # compute legal moves similar to server rules
        def _compute_legal_moves_local(hand, lead):
            hand = list(hand or [])
            if not hand or not lead:
                return hand
            suited = [c for c in hand if CardMapper.get_card_suit(c) == lead]
            return suited if suited else hand

        legal_moves = _compute_legal_moves_local(hand_before, lead_suit)

        card = dm.choose_card(t.my_hand)
        if card is None:
            # No legal play — bail
            break

        # Play card
        game.play_card(player.player_id, str(card))

        # keep round state aligned with the round before the play, even if the game finishes immediately
        round_number = current_round
        round_plays_before = deepcopy(state.get("round_plays", []))
        position_in_trick = len(round_plays_before)
        cards_before = deepcopy(round_plays_before)

        # record action in a DataGatherer-friendly shape
        action = {
            "game_id": game_id,
            "round": round_number,
            "player": player.player_name,
            "position": str(player.position),
            "card": str(card),
            "cards_in_trick": cards_before,
            "position_in_trick": position_in_trick,
            "lead_suit": lead_suit if lead_suit is not None else state.get("round_suit"),
            "trump": state.get("trump_suit"),
            "team_scores": {"team1": game.team_scores[0], "team2": game.team_scores[1]},
            "hand_before": deepcopy(hand_before),
            "legal_moves": deepcopy(legal_moves),
        }
        action_data.append(action)

        # Update round_data cards_played and store the full play context for the round
        if round_key and round_key in round_data:
            round_data[round_key]["cards_played"].append(action)
            round_data[round_key]["actions"] = round_data[round_key]["cards_played"]
            round_data[round_key]["last_cards_before"] = cards_before

        # Check if the round finished right after playing the card (e.g. 4th card played)
        new_state = game.get_state()
        new_round = int(new_state.get("current_round") or 0)

        if (new_round > current_round) or (new_state.get("phase") == "finished" and current_round == 10):
            finished_round_key = f"round_{current_round}"
            if finished_round_key in round_data:
                rd = round_data[finished_round_key]
                # Set intermediate scores
                rd["team_scores_after"] = deepcopy(new_state.get("team_scores", {}))

                # Capture winner metadata from GameState
                if game.last_winner:
                    rd["winner_player"] = game.last_winner.player_name
                    rd["winner_id"] = game.last_winner.player_id

                # Derive points and team winner
                before = rd.get("team_scores_before") or {}
                after = rd.get("team_scores_after") or {}
                t1_before = int(before.get("team1", 0) or 0)
                t2_before = int(before.get("team2", 0) or 0)
                t1_after = int(after.get("team1", 0) or 0)
                t2_after = int(after.get("team2", 0) or 0)

                delta_t1 = t1_after - t1_before
                delta_t2 = t2_after - t2_before

                if delta_t1 > delta_t2:
                    rd["winner_team"] = "team1"
                    rd["points"] = delta_t1
                elif delta_t2 > delta_t1:
                    rd["winner_team"] = "team2"
                    rd["points"] = delta_t2
                else:
                    # In Sueca, even if 0 points are scored, a team wins the trick.
                    # If we have winner_player, we can infer the team.
                    if game.last_winner:
                        from ..positions import Positions
                        p_pos = game.last_winner.position
                        if p_pos in [Positions.NORTH, Positions.SOUTH]:
                            rd["winner_team"] = "team1"
                        else:
                            rd["winner_team"] = "team2"
                    rd["points"] = 0

        timeline.append({"ts": time.time(), "phase": game.phase, "event": "card_played", "player": player.player_name, "card": str(card)})

    # Finalize
    final_state = deepcopy(game.get_state())
    last_match = game.match_history[-1] if game.match_history else {}
    final_scores = deepcopy(final_state.get("team_scores")) if isinstance(final_state.get("team_scores"), dict) else {
        "team1": game.team_scores[0],
        "team2": game.team_scores[1],
    }
    winner_team = last_match.get("winner_team")
    winner_label = last_match.get("winner_label")
    if not winner_team:
        if final_scores.get("team1", 0) > final_scores.get("team2", 0):
            winner_team = "team1"
            winner_label = "Team 1 (N/S)"
        elif final_scores.get("team2", 0) > final_scores.get("team1", 0):
            winner_team = "team2"
            winner_label = "Team 2 (E/W)"
        else:
            winner_team = "draw"
            winner_label = "draw"

    # Fallback finalization for any rounds that might have missed their 'after' scores
    for round_key, rd in round_data.items():
        if rd.get("team_scores_after") is None:
            rd["team_scores_after"] = deepcopy(final_scores)
            # Try to derive something if missing
            if rd.get("points") is None:
                before = rd.get("team_scores_before") or {}
                after = rd.get("team_scores_after") or {}
                t1_before = int(before.get("team1", 0) or 0)
                t2_before = int(before.get("team2", 0) or 0)
                t1_after = int(after.get("team1", 0) or 0)
                t2_after = int(after.get("team2", 0) or 0)
                rd["points"] = max(t1_after - t1_before, t2_after - t2_before)

    result = {
        "game_data": {
            "game_number": game_number,
            "game_id": game_id,
            "final_scores": final_scores,
            "matches_played": final_state.get("matches_played", 0),
            "rounds_played": len(round_data),
            "winner_team": winner_team,
            "winner_label": winner_label,
            "match_number": last_match.get("match_number"),
            "finished_at": last_match.get("finished_at"),
            "trump_card": str(game.trump_card) if game.trump_card is not None else None,
            "trump_card_suit": game.trump_suit,
            "phase": final_state.get("phase"),
            "player_names": [p.player_name for p in game.players],
            "timeline": timeline,
        },
        "round_data": round_data,
        "action_data": action_data,
        "match_history": list(game.match_history),
    }

    return result
