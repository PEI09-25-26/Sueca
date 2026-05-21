"""Decision maker for WeakAgent, ported from sueca_1.3 heuristics."""

import random

from ...card_analyzer import CardAnalyzer
from ...card_mapper import CardMapper


class DecisionMaker:
    """Implements simple heuristic decision making for weak AI."""

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
        if self.state.current_round >= 8:
            return CardAnalyzer.get_highest_card(
                legal_plays,
                self.state.trump_suit,
                self.state.lead_suit,
            )

        trumps = []
        non_trumps = []
        for card in legal_plays:
            if CardMapper.get_card_suit(card) == self.state.trump_suit:
                trumps.append(card)
            else:
                non_trumps.append(card)

        if non_trumps:
            sorted_cards = sorted(
                non_trumps,
                key=lambda card: CardAnalyzer.get_card_strength(
                    card,
                    self.state.trump_suit,
                    self.state.lead_suit,
                ),
            )
            return sorted_cards[len(sorted_cards) // 2]

        return CardAnalyzer.get_lowest_card(trumps)

    def choose_middle_card(self, legal_plays):
        if self.state.is_partner_winning():
            return CardAnalyzer.get_lowest_card(legal_plays)

        trick_points = self.state.get_trick_points()
        if trick_points >= 10:
            winning_card = CardAnalyzer.get_lowest_winning_card(
                legal_plays,
                self.state.current_trick,
                self.state.trump_suit,
                self.state.lead_suit,
            )
            if winning_card is not None:
                return winning_card

        return CardAnalyzer.get_lowest_card(legal_plays)

    def choose_last_card(self, legal_plays):
        if self.state.is_partner_winning():
            return CardAnalyzer.get_lowest_card(legal_plays)

        trick_points = self.state.get_trick_points()
        # As last player, only contest expensive tricks.
        if trick_points < 10:
            return CardAnalyzer.get_lowest_card(legal_plays)

        winning_card = CardAnalyzer.get_lowest_winning_card(
            legal_plays,
            self.state.current_trick,
            self.state.trump_suit,
            self.state.lead_suit,
        )
        if winning_card is not None:
            return winning_card

        return CardAnalyzer.get_lowest_card(legal_plays)

    def choose_trump_selection(self):
        return random.choice(["top", "bottom"])

    def choose_deck_cut(self):
        return random.randint(1, 40)
