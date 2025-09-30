from swu_engine.board import Board
from swu_engine.cardbundle import CardBundle

class Player:
    def __init__(self, player_id: int, name: str, isAI: bool = False):
        self.player_id = player_id
        self.name = name
        self.isAI = isAI
        self.board = Board(board_id=f"board_{player_id}", owner_id=player_id)

        self.deck: list[CardBundle] = []
        self.hand: list[CardBundle] = []
        self.resources: list[CardBundle] = []
        self.discard_pile: list[CardBundle] = []
        self.exile_pile: list[CardBundle] = []

        self.leader = None
        self.base = None
        self.top_deck_revealed: bool = False

    def get_board(self):
        return self.board

    def get_player_id(self):
        return self.player_id

    def get_name(self):
        return self.name

    def available_resources(self):
        return [r for r in self.resources if not r.exhausted]

    def get_leader_bundle(self) -> 'CardBundle | None':
        leader_zone = self.board.find_zone("Leader")
        if leader_zone and leader_zone.get_piles():
            for pile in leader_zone.get_piles():
                for b in pile.get_bundles():
                    return b
        return None

    def mulligan(self):
        """
        Shuffle current hand back into deck, draw same number of cards.
        Should only be allowed once per game.
        """
        raise NotImplementedError("Player.mulligan() not yet implemented")

    # 🔹 keep these INSIDE the same class
    def can_pay_for(self, game, card) -> bool:
        ready_resources = [b for b in self.resources if not getattr(b, "exhausted", False)]
        return len(ready_resources) >= getattr(card, "cost", 0)

    def pay_for(self, game, card) -> bool:
        cost = getattr(card, "cost", 0)
        ready_resources = [b for b in self.resources if not getattr(b, "exhausted", False)]
        if len(ready_resources) < cost:
            return False
        for b in ready_resources[:cost]:
            b.exhausted = True
        return True
