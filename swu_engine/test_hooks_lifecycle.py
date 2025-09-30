import unittest
from swu_engine.game import Game
from swu_engine.player import Player
from swu_engine.card import Card
from swu_engine.cardbundle import CardBundle


class TestHooksLifecycle(unittest.TestCase):
    def setUp(self):
        self.game = Game()
        self.player1 = Player(1, "Alice")
        self.player2 = Player(2, "Bob")
        self.game.add_player(self.player1)
        self.game.add_player(self.player2)

        # Give each player some dummy cards in hand
        for i in range(5):
            c1 = Card(name=f"AliceCard{i}", back_info="Back", token_info="", card_type="unit", cost=1, arenas=["Ground"])
            c2 = Card(name=f"BobCard{i}", back_info="Back", token_info="", card_type="unit", cost=1, arenas=["Ground"])
            self.player1.hand.append(CardBundle(primary_card=c1, owner_id=self.player1.player_id))
            self.player2.hand.append(CardBundle(primary_card=c2, owner_id=self.player2.player_id))

    def test_mulligan_and_ready_leaders(self):
        self.game.turn_manager.next_phase()  # triggers start_of_round
        self.assertEqual(len(self.player1.hand), 5)
        self.assertEqual(len(self.player2.hand), 5)

    def test_auto_draw_and_discard(self):
        hand_before = len(self.player1.hand)
        self.game.turn_manager.next_phase()  # main
        self.game.turn_manager.next_phase()  # combat
        self.game.turn_manager.next_phase()  # end -> end_of_turn hooks
        hand_after = len(self.player1.hand)
        self.assertGreaterEqual(hand_after, hand_before)

    def test_enforce_hand_limit(self):
        for i in range(5):
            c = Card(name=f"Extra{i}", back_info="Back", token_info="", card_type="unit", cost=1, arenas=["Ground"])
            self.player1.hand.append(CardBundle(primary_card=c, owner_id=self.player1.player_id))

        self.game.turn_manager.phase_index = len(self.game.phases) - 1  # jump to End
        self.game.turn_manager.next_phase()  # triggers end_of_turn
        self.assertLessEqual(len(self.player1.hand), 7)
