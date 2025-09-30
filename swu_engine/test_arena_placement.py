import unittest

from swu_engine.game import Game
from swu_engine.player import Player
from swu_engine.card import Card
from swu_engine.token import Token
from swu_engine.cardbundle import CardBundle


class TestArenaPlacement(unittest.TestCase):
    def setUp(self):
        self.game = Game()
        self.player = Player(1, "Alice", isAI=False)
        self.game.add_player(self.player)

        # 🔹 Give Alice dummy resources so play_card() will succeed
        for i in range(5):
            res_card = Card(
                name=f"Resource{i}",
                back_info="ResBack",
                token_info="",
                card_type="resource",
                cost=0,
            )
            res_bundle = CardBundle(primary_card=res_card, owner_id=self.player.get_player_id())
            self.player.resources.append(res_bundle)

    def test_ground_unit_placement(self):
        ground_card = Card(
            name="Stormtrooper",
            back_info="Stormtrooper Back",
            token_info="",
            card_type="unit",
            cost=2,
            arenas=["Ground"],
        )
        bundle = CardBundle(primary_card=ground_card, owner_id=self.player.get_player_id())
        self.game.play_card(self.player, bundle)

        ground_zone = self.player.get_board().find_zone("Ground Arena")
        self.assertTrue(
            any(b.primary_card.name == "Stormtrooper" for p in ground_zone.get_piles() for b in p.get_bundles())
        )

    def test_space_unit_placement(self):
        space_card = Card(
            name="TIE Fighter",
            back_info="TIE Back",
            token_info="",
            card_type="unit",
            cost=2,
            arenas=["Space"],
        )
        bundle = CardBundle(primary_card=space_card, owner_id=self.player.get_player_id())
        self.game.play_card(self.player, bundle)

        space_zone = self.player.get_board().find_zone("Space Arena")
        self.assertTrue(
            any(b.primary_card.name == "TIE Fighter" for p in space_zone.get_piles() for b in p.get_bundles())
        )

    def test_ground_token_placement(self):
        token = Token(token_info="Clone Trooper", attack=1, health=1, keywords=["Sentinel"], arenas=["Ground"])
        action = self.game.rules.create_token_action(self.player, token)
        action.execute({})

        ground_zone = self.player.get_board().find_zone("Ground Arena")
        self.assertTrue(
            any(any(t.token_info == "Clone Trooper" for t in b.tokens) for p in ground_zone.get_piles() for b in p.get_bundles())
        )

    def test_space_token_placement(self):
        token = Token(token_info="TIE Fighter Token", attack=2, health=2, arenas=["Space"])
        action = self.game.rules.create_token_action(self.player, token)
        action.execute({})

        space_zone = self.player.get_board().find_zone("Space Arena")
        self.assertTrue(
            any(any(t.token_info == "TIE Fighter Token" for t in b.tokens) for p in space_zone.get_piles() for b in p.get_bundles())
        )

    def test_counter_token_attached(self):
        # Attach a shield counter to Luke
        luke = Card(
            name="Luke Skywalker",
            back_info="Luke Back",
            token_info="",
            card_type="unit",
            cost=6,
            arenas=["Ground"],
        )
        bundle = CardBundle(primary_card=luke, owner_id=self.player.get_player_id())
        shield = Token(token_info="Shield", token_type="counter")
        bundle.tokens.append(shield)

        ground_zone = self.player.get_board().find_zone("Ground Arena")
        ground_zone.get_piles()[0].add_bundle(bundle)

        self.assertTrue(
            any(t.token_info == "Shield" and t.token_type == "counter"
                for p in ground_zone.get_piles()
                for b in p.get_bundles()
                for t in b.tokens)
        )
