from swu_engine.cardbundle import CardBundle

class Pile:
    def __init__(self, pile_id: str):
        self.pile_id = pile_id
        self.bundles: list[CardBundle] = []

    def add_bundle(self, bundle: CardBundle):
        self.bundles.append(bundle)

    def remove_bundle(self, bundle: CardBundle):
        if bundle in self.bundles:
            self.bundles.remove(bundle)

    def get_bundles(self):
        return self.bundles


class Zone:
    def __init__(self, zone_id: str, owner_id: int, name: str = "", visibility: str = "public"):
        """
        visibility = "public", "hidden_owner", or "hidden_all"
        - public       : all players can see contents (e.g. discard, exile, arenas)
        - hidden_owner : only the owner can see (e.g. hand, deck)
        - hidden_all   : no one sees contents until revealed (e.g. face-down resources/events if SWU uses them)
        """
        self.zone_id = zone_id
        self.owner_id = owner_id
        self.name = name
        self.visibility = visibility
        self.piles: list[Pile] = []

    def add_pile(self, pile: Pile):
        self.piles.append(pile)

    def get_piles(self):
        return self.piles

    def get_name(self):
        return self.name


class Board:
    def __init__(self, board_id: str, owner_id: int):
        self.board_id = board_id
        self.owner_id = owner_id
        self.zones: list[Zone] = []
        self.zones.append(Zone("leader", owner_id, "Leader", "public"))

    def add_zone(self, zone: Zone):
        self.zones.append(zone)

    def get_zones(self):
        return self.zones

    def find_zone(self, zone_name: str) -> 'Zone | None':
        """Find a zone on this board by name."""
        for z in self.zones:
            if z.get_name().lower() == zone_name.lower():
                return z
        return None

    def move_to_zone(self, bundle: 'CardBundle', from_zone: 'Zone', to_zone: 'Zone'):
        """Move a card bundle between zones (removes from one, adds to another)."""
        for pile in from_zone.get_piles():
            if bundle in pile.get_bundles():
                pile.remove_bundle(bundle)
                # put into first pile of target zone (create if none exist)
                if not to_zone.get_piles():
                    to_zone.add_pile(Pile(f"{to_zone.zone_id}_pile"))
                to_zone.get_piles()[0].add_bundle(bundle)
                return True
        return False

    def move_to_pile(self, bundle: 'CardBundle', from_pile: 'Pile', to_pile: 'Pile'):
        """Move a card bundle between two specific piles."""
        if bundle in from_pile.get_bundles():
            from_pile.remove_bundle(bundle)
            to_pile.add_bundle(bundle)
            return True
        return False
