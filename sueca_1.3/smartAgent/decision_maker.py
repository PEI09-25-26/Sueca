"""Decision maker for AverageAgent"""

import random

from card_analyzer import CardAnalyzer
from card_mapper import CardMapper


class DecisionMaker:
    """Implements simple heuristic decision making for average AI."""

    def __init__(self, game_state_tracker):
        self.state = game_state_tracker

    def choose_card(self, hand):
        if not hand:
            return None

        legal_plays = CardAnalyzer.get_legal_plays(hand, self.state.lead_suit)

        if len(legal_plays) == 1:
            return legal_plays[0]

        num_played = len(self.state.current_trick)
        if num_played == 0:
            return self.choose_lead_card(legal_plays)
        if num_played == 3:
            return self.choose_last_card(legal_plays)
        return self.choose_middle_card(legal_plays)

    def choose_lead_card(self, legal_plays):
        non_trumps = [c for c in legal_plays if CardMapper.get_card_suit(c) != self.state.trump_suit]
        trumps = [c for c in legal_plays if CardMapper.get_card_suit(c) == self.state.trump_suit]
        danger_suits = set()
        for suit in CardMapper.SUITS:
            for opp in self.state.opponents:
                if self.state.is_player_void(opp, suit):
                    danger_suits.add(suit)
        safe_non_trumps = [c for c in non_trumps if CardMapper.get_card_suit(c) not in danger_suits]
        danger_non_trumps = [c for c in non_trumps if CardMapper.get_card_suit(c) in danger_suits]
        partner_safe_non_trumps = [c for c in safe_non_trumps if not self.state.is_player_void(self.state.partner_id, CardMapper.get_card_suit(c))]
        preferred_cards = partner_safe_non_trumps if partner_safe_non_trumps else safe_non_trumps
        if self.state.current_round <= 4:
            ace = self.find_safe_ace(preferred_cards)
            if ace:
                return ace
        if self.state.current_round >= 8:
            if preferred_cards:
                high = CardAnalyzer.get_highest_card(
                    preferred_cards,
                    self.state.trump_suit,
                    self.state.lead_suit,
                )
                if CardMapper.get_card_points(high) > 0:
                    return high
            else:
                high = CardAnalyzer.get_highest_card(
                    safe_non_trumps if safe_non_trumps else non_trumps,
                    self.state.trump_suit,
                    self.state.lead_suit,
                )
                if CardMapper.get_card_points(high) > 0:
                    return high
        if preferred_cards:
            for card in preferred_cards:
                suit = CardMapper.get_card_suit(card)
                rank = CardMapper.get_card_rank(card)
                
                if rank == "7" and self.state.is_ace_gone(suit):
                    return card
            ace = self.find_safe_ace(preferred_cards)
            if ace:
                return ace
            sorted_cards = sorted(
                preferred_cards,
                key=lambda card: CardAnalyzer.get_card_strength(card, self.state.trump_suit, self.state.lead_suit),
            )
            zero_point_cards = [c for c in sorted_cards if CardMapper.get_card_points(c) == 0]
            if zero_point_cards:
                return zero_point_cards[len(zero_point_cards) // 2]
            return sorted_cards[len(sorted_cards) // 2]
        elif danger_non_trumps:
            return CardAnalyzer.get_lowest_card(danger_non_trumps)
        return CardAnalyzer.get_lowest_card(trumps)

    def choose_middle_card(self, legal_plays):
        non_trumps = [c for c in legal_plays if CardMapper.get_card_suit(c) != self.state.trump_suit]
        trick_points = self.state.get_trick_points()
        for p in self.state.get_players_after_self():
            if p in self.state.opponents:
                opp = p
        danger_suits = []
        for suit in CardMapper.SUITS:
            if self.state.is_player_void(opp, suit) and suit not in danger_suits:
                danger_suits.append(suit)
        if self.state.is_partner_winning():
            if non_trumps:
                return CardAnalyzer.get_lowest_card(non_trumps)
            return CardAnalyzer.get_lowest_card(legal_plays)
        if trick_points >= 10:
            if non_trumps:
                winning_card = CardAnalyzer.get_lowest_winning_card(
                    non_trumps,
                    self.state.current_trick,
                    self.state.trump_suit,
                    self.state.lead_suit,
                )
                if winning_card:
                    return winning_card
                else:
                    winning_card = CardAnalyzer.get_lowest_winning_card(
                        legal_plays,
                        self.state.current_trick,
                        self.state.trump_suit,
                        self.state.lead_suit,
                    )
                    if winning_card:
                        return winning_card
            else:
                winning_card = CardAnalyzer.get_lowest_winning_card(
                    legal_plays,
                    self.state.current_trick,
                    self.state.trump_suit,
                    self.state.lead_suit,
                )
                if winning_card:
                    return winning_card
        return CardAnalyzer.get_lowest_card(legal_plays)

    def choose_last_card(self, legal_plays):
        trick_points = self.state.get_trick_points()
        non_trumps = [c for c in legal_plays if CardMapper.get_card_suit(c) != self.state.trump_suit]
        if trick_points >= 10:
            if self.state.is_partner_winning():
                if non_trumps:
                    return CardAnalyzer.get_highest_card(non_trumps)
                return CardAnalyzer.get_highest_card(legal_plays)
            else:
                if non_trumps:
                    winning_card = winning_card = CardAnalyzer.get_highest_winning_card(
                        non_trumps,
                        self.state.current_trick,
                        self.state.trump_suit,
                        self.state.lead_suit,
                    )
                    if winning_card:
                        return winning_card
                winning_card = CardAnalyzer.get_highest_winning_card(
                    legal_plays,
                    self.state.current_trick,
                    self.state.trump_suit,
                    self.state.lead_suit,
                )
                if winning_card:
                    return winning_card
                else:
                    if non_trumps:
                        return CardAnalyzer.get_lowest_card(non_trumps)
        elif trick_points >= 5:
            if self.state.is_partner_winning():
                if non_trumps:
                    return CardAnalyzer.get_lowest_card(non_trumps)
                return CardAnalyzer.get_lowest_card(legal_plays)
        return CardAnalyzer.get_lowest_card(legal_plays)

    def choose_trump_selection(self):
        return random.choice(["top", "bottom"])

    def choose_deck_cut(self):
        return random.randint(1, 40)

    def find_safe_ace(cards):
        for c in cards:
            if CardMapper.get_card_rank(c) == "A":
                return c
        return None