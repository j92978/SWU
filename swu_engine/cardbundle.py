from swu_engine.card import Card

class CardBundle:
    def __init__(self, primary_card: Card, owner_id: int, secondary_cards=None, tokens=None):
        self.primary_card = primary_card
        self.owner_id = owner_id
        self.secondary_cards = secondary_cards or []
        self.tokens = tokens or []
        self.upgrades: list[CardBundle] = []
        self.damage = 0
        self.exhausted = False
        self.attack_buff = 0
        self.health_buff = 0
        self.temp_keywords: set[str] = set()
        self.peekers: set[int] = set()

    def effective_attack(self):
        return self.primary_card.attack + self.attack_buff

    def effective_health(self):
        return self.primary_card.health + self.health_buff

    def has_keyword(self, keyword: str):
        return keyword in self.primary_card.keywords or keyword in self.temp_keywords

    def ready(self):
        self.exhausted = False

    def exhaust(self):
        self.exhausted = True

    def get_default_arena(self) -> str:
        """
        Ask the primary card (or token) for its default arena.
        """
        if self.primary_card:
            return self.primary_card.get_default_arena()
        elif self.tokens:
            return self.tokens[0].get_default_arena()
        return "Ground Arena"