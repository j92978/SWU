class Token:
    def __init__(self, token_info: str, attack: int = None, health: int = None,
                 keywords: list[str] = None, arenas: list[str] = None,
                 token_type: str = "counter"):
        """
        token_type = "counter" (attached to a bundle)
                   = "unit" (acts as its own unit in an arena)
        """
        self.token_info = token_info
        self.attack = attack
        self.health = health
        self.keywords = keywords or []
        self.arenas = arenas or ["Ground Arena"]
        self.token_type = token_type

    def get_default_arena(self) -> str:
        if self.arenas:
            arena_key = self.arenas[0].lower()
            if "ground" in arena_key:
                return "Ground Arena"
            elif "space" in arena_key:
                return "Space Arena"
        return "Ground Arena"
