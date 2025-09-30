class Base:
    def __init__(self, name: str, health: int = 30):
        self.name = name
        self.max_health = health
        self.health = health

    def take_damage(self, amount: int):
        self.health = max(0, self.health - max(0, amount))

    def heal(self, amount: int):
        self.health = min(self.max_health, self.health + amount)

    def is_defeated(self):
        return self.health <= 0
