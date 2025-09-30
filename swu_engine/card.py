class Card:
    def __init__(self, name, back_info, token_info: str, card_type="unit", cost=0, subtype=None,
                 aspects=None, leader_attack=0, leader_health=0, leader_subtype=None,
                 leader_ability_fn=None, extra_cost_fn=None, effect_fn=None, attack:int=None, health: int=None,
                 keywords: list[str] = None, arenas: list[str] = None, **kwargs):
        self.name = name
        self.back_info = back_info
        self.cost = cost
        self.card_type = card_type
        self.subtype = subtype
        self.attack = attack
        self.health = health
        self.aspects = aspects or []
        self.keywords = set(keywords or [])
        self.leader_attack = leader_attack
        self.leader_health = leader_health
        self.leader_subtype = leader_subtype
        self.leader_ability_fn = leader_ability_fn
        self.extra_cost_fn = extra_cost_fn
        self.effect_fn = effect_fn
        self.token_info = token_info
        self.attack = attack
        self.health = health
        self.keywords = keywords or []
        # Normalize arenas to ["Ground Arena"] or ["Space Arena"]
        if arenas:
            self.arenas = [
                "Ground Arena" if a.lower() == "ground" else
                "Space Arena" if a.lower() == "space" else a
                for a in arenas
            ]
        else:
            self.arenas = ["Ground Arena"]  # default fallback

    def get_default_arena(self) -> str:
        """
        Return the primary arena for this card, if any.
        Units usually specify Ground or Space; defaults to Ground Arena.
        """
        if hasattr(self, "arenas") and self.arenas:
            arena_key = self.arenas[0].lower()
            if "ground" in arena_key:
                return "Ground Arena"
            elif "space" in arena_key:
                return "Space Arena"
        return "Ground Arena"