"""Decision maker for AverageAgent"""

import random

from ...card_analyzer import CardAnalyzer
from ...card_mapper import CardMapper


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
        if self.state.current_round <= 4:
            for card in legal_plays:
                if (CardMapper.get_card_rank(card) == "A" and CardMapper.get_card_suit(card) != self.state.trump_suit):
                    return card
        if self.state.current_round >= 8:
            return CardAnalyzer.get_highest_card(legal_plays, self.state.trump_suit, self.state.lead_suit,)
        if non_trumps:
            sorted_cards = sorted(
                non_trumps,
                key=lambda card: CardAnalyzer.get_card_strength(card, self.state.trump_suit, self.state.lead_suit),
            )
            return sorted_cards[len(sorted_cards) // 2]
        return CardAnalyzer.get_lowest_card(trumps)

    def choose_middle_card(self, legal_plays):
        non_trumps = [c for c in legal_plays if CardMapper.get_card_suit(c) != self.state.trump_suit]
        trick_points = self.state.get_trick_points()
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
                scoring_cards = [c for c in non_trumps if CardAnalyzer.get_card_value(c) > 0]
                if len(scoring_cards) <= 2:
                    card_pool = scoring_cards if scoring_cards else (non_trumps if non_trumps else legal_plays)
                    return CardAnalyzer.get_highest_card(card_pool)
                else:
                    sorted_cards = sorted(scoring_cards, key=lambda c: CardAnalyzer.get_card_value(c))
                    index = max(0, len(sorted_cards) - 3)
                    return sorted_cards[index]
            else:
                winning_card = CardAnalyzer.get_lowest_winning_card(
                    legal_plays,
                    self.state.current_trick,
                    self.state.trump_suit,
                    self.state.lead_suit,
                )
                if winning_card is None:
                    if non_trumps:
                        return CardAnalyzer.get_lowest_card(non_trumps)
                if winning_card is not None:
                    return winning_card
        else:
            if self.state.is_partner_winning():
                if non_trumps:
                    return CardAnalyzer.get_lowest_card(non_trumps)
                return CardAnalyzer.get_lowest_card(legal_plays)
        return CardAnalyzer.get_lowest_card(legal_plays)

    def choose_trump_selection(self):
        return random.choice(["top", "bottom"])

    def choose_deck_cut(self):
        return random.randint(1, 40)
