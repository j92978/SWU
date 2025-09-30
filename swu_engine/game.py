from swu_engine.player import Player
from swu_engine.base import Base
from swu_engine.turn_manager import TurnManager
from swu_engine.rules_engine import RulesEngine
from swu_engine.cardbundle import CardBundle
from swu_engine.board import Zone, Pile
import random

class Game:
    def __init__(self):
        self.players: list[Player] = []
        self.phases = [
            type("Phase", (), {"name": "Start"})(),
            type("Phase", (), {"name": "Main"})(),
            type("Phase", (), {"name": "Combat"})(),
            type("Phase", (), {"name": "End"})(),
        ]
        self.turn_manager = TurnManager(self.players, self.phases, self)  # 🔹 now has reference back to Game
        self.rules = RulesEngine()
        self.delayed_effects: list[tuple[str, dict]] = []

    def add_player(self, player: Player):
        self.players.append(player)

        # Put leader in Leader zone if defined
        if hasattr(player, "leader") and player.leader:
            leader_zone = player.get_board().find_zone("Leader")
            if leader_zone:
                # Make sure zone is empty (1 leader max)
                if not leader_zone.get_piles():
                    leader_pile = Pile("leader_pile")
                    leader_zone.add_pile(leader_pile)
                if player.leader not in leader_zone.get_piles()[0].get_bundles():
                    leader_zone.get_piles()[0].add_bundle(player.leader)

    def get_player_by_id(self, pid: int):
        return next((p for p in self.players if p.get_player_id() == pid), None)

    def get_active_player(self):
        return self.turn_manager.get_active_player(self)

    def register_delayed_effect(self, trigger_phase: str, effect_fn, **kwargs):
        self.delayed_effects.append((trigger_phase, {"fn": effect_fn, "kwargs": kwargs}))
        print(f"Delayed effect registered for {trigger_phase}.")

    def play_card(self, player: Player, bundle: CardBundle, extra_targets=None):
        card = bundle.primary_card
        if not player.can_pay_for(self, card) or not player.pay_for(self, card):
            return False

        # Hand → Arena/Discard/Resources
        hand_zone = player.get_board().find_zone("Hand")
        if bundle in player.hand:
            player.hand.remove(bundle)  # keep internal list synced

        if card.card_type == "unit":
            zone_name = bundle.get_default_arena()
            arena = player.get_board().find_zone(zone_name)
            if not arena.get_piles():
                from swu_engine.board import Pile
                arena.add_pile(Pile(f"{arena.zone_id}_pile"))
            arena.get_piles()[0].add_bundle(bundle)
            print(f"{card.name} enters the {arena.get_name()}.")


        elif card.card_type == "event":
            print(f"{player.get_name()} plays event {card.name}.")
            if card.effect_fn:
                if getattr(card.effect_fn, "requires_target", False):
                    card.effect_fn(self, player, extra_targets or {})
                else:
                    card.effect_fn(self, player, {})
            discard_zone = player.get_board().find_zone("Discard")
            player.get_board().move_to_zone(bundle, hand_zone, discard_zone)
            player.discard_pile.append(bundle)   # keep discard list synced
            print(f"{card.name} is moved to discard.")

        elif card.card_type == "upgrade":
            print(f"{player.get_name()} plays upgrade {card.name} (attach via action).")
            # implement attachment logic here later

        elif card.card_type == "resource":
            res_zone = player.get_board().find_zone("Resources")
            player.get_board().move_to_zone(bundle, hand_zone, res_zone)
            player.resources.append(bundle)   # keep resource list synced
            print(f"{player.get_name()} places a resource ({card.name}).")

        return True

    def show_board(self):
        print("=== Board State ===")

        # Show initiative holder
        if hasattr(self.turn_manager, "get_initiative_player"):
            init_player = self.turn_manager.get_initiative_player()
            round_num = getattr(self.turn_manager, "round_number", "?")
            print(f"Round {round_num} – Initiative: {init_player.get_name()}")


        for p in self.players:
            print(f"\n{p.get_name()}:")

            if p.base:
                base_name = p.base.name
                base_hp = p.base.health
                base_max = p.base.max_health
                base_dmg = base_max - base_hp
                print(f"  Base: {base_name} (HP {base_hp}/{base_max}, DMG {base_dmg})")
            else:
                print("  Base: None")

            # Leader (always visible via Player getter)
            leader_bundle = p.get_leader_bundle()
            if leader_bundle:
                leader_card = leader_bundle.primary_card
                status = "Exhausted" if leader_bundle.exhausted else "Ready"
                atk = leader_bundle.effective_attack()
                hp = leader_bundle.effective_health()
                dmg = leader_bundle.damage
                kw = ", ".join(list(leader_bundle.temp_keywords) + list(leader_card.keywords))
                kw_str = f" Keywords: {kw}" if kw else ""
                print(
                    f"  Leader: {leader_card.name} "
                    f"(ATK {atk}, HP {hp}, DMG {dmg}) [{status}]{kw_str}"
                )
            else:
                print("  Leader: (none)")

            # Hand
            hand_zone = Zone("hand", p.player_id, "Hand", "hidden_owner")
            pile = Pile("hand_pile")
            for b in p.hand:
                pile.add_bundle(b)
            hand_zone.add_pile(pile)
            print(" ", self._format_zone(p, hand_zone, p))

            # Deck
            deck_zone = Zone("deck", p.player_id, "Deck", "hidden_owner")
            deck_pile = Pile("deck_pile")
            for b in p.deck:
                deck_pile.add_bundle(b)
            deck_zone.add_pile(deck_pile)

            if p.top_deck_revealed and p.deck:
                top_card = p.deck[0].primary_card.name
                print(f"  Deck:\n    - {top_card} (revealed)")
                if len(p.deck) > 1:
                    print(f"    + {len(p.deck) - 1} more card(s) (hidden)")
            else:
                print(" ", self._format_zone(p, deck_zone, p))


            # Discard
            discard_zone = Zone("discard", p.player_id, "Discard", "public")
            discard_pile = Pile("discard_pile")
            for b in p.discard_pile:
                discard_pile.add_bundle(b)
            discard_zone.add_pile(discard_pile)
            print(" ", self._format_zone(p, discard_zone, p))

            # Exile
            exile_zone = Zone("exile", p.player_id, "Exile", "public")
            exile_pile = Pile("exile_pile")
            for b in p.exile_pile:
                exile_pile.add_bundle(b)
            exile_zone.add_pile(exile_pile)
            print(" ", self._format_zone(p, exile_zone, p))
            # Resources
            res_zone = Zone("resources", p.player_id, "Resources", "hidden_all")
            res_pile = Pile("resource_pile")
            for b in p.resources:
                res_pile.add_bundle(b)
            res_zone.add_pile(res_pile)
            print(" ", self._format_zone(p, res_zone, p))

            # Arenas
            for z in p.get_board().get_zones():
                if z.get_name() in ("Ground Arena", "Space Arena"):
                    print(f"  {z.get_name()}:")
                    any_units = False
                    for pile in z.get_piles():
                        for b in pile.get_bundles():
                            any_units = True
                            status = "Exhausted" if b.exhausted else "Ready"
                            atk = b.effective_attack()
                            hp = b.effective_health()
                            dmg = b.damage
                            kw = ", ".join(list(b.temp_keywords) + list(b.primary_card.keywords))
                            kw_str = f" Keywords: {kw}" if kw else ""
                            print(
                                f"    - {b.primary_card.name} "
                                f"(ATK {atk}, HP {hp}, DMG {dmg}) [{status}]{kw_str}"
                            )
                    if not any_units:
                        print("    (empty)")

    def deal_damage(self, target, amount: int):
        if isinstance(target, Base):
            target.take_damage(amount)
            print(f"{target.name} takes {amount} damage (health={target.health}).")
        elif isinstance(target, CardBundle):
            target.damage += amount
            print(f"{target.primary_card.name} takes {amount} damage (damage={target.damage}).")

    def heal_unit(self, bundle: CardBundle, amount: int):
        healed = min(amount, bundle.damage)
        bundle.damage -= healed
        print(f"{bundle.primary_card.name} heals {healed} damage (damage={bundle.damage}).")

    def discard_card_from_hand(self, player: Player, bundle: CardBundle):
        if bundle not in player.hand:
            print(f"{bundle.primary_card.name} not in {player.get_name()}'s hand.")
            return False
        hand_zone = player.get_board().find_zone("Hand")
        discard_zone = player.get_board().find_zone("Discard")
        player.get_board().move_to_zone(bundle, hand_zone, discard_zone)
        player.hand.remove(bundle)          # keep list synced
        player.discard_pile.append(bundle)  # keep list synced
        print(f"{player.get_name()} discards {bundle.primary_card.name}.")
        return True

    def move_to_discard(self, player: 'Player', bundle: 'CardBundle'):
        """Move a card bundle to the player's discard pile and sync zones."""
        discard_zone = player.get_board().find_zone("Discard")
        if discard_zone is None:
            discard_zone = Zone("discard", player.get_player_id(), "Discard", "public")
            player.get_board().add_zone(discard_zone)

        # Ensure pile exists
        if not discard_zone.get_piles():
            discard_zone.add_pile(Pile("discard_pile"))

        # Add to discard zone
        discard_zone.get_piles()[0].add_bundle(bundle)

        # Track in player's discard list
        if bundle not in player.discard_pile:
            player.discard_pile.append(bundle)

        print(f"{bundle.primary_card.name} moved to discard pile of {player.get_name()}.")

    def draw_cards(self, player: Player, amount: int):
        deck_zone = player.get_board().find_zone("Deck")
        hand_zone = player.get_board().find_zone("Hand")
        for _ in range(min(amount, len(player.deck))):
            b = player.deck.pop(0)
            player.top_deck_revealed = False
            hand_zone.get_piles()[0].add_bundle(b)
            player.hand.append(b)  # keep list synced
            print(f"{player.get_name()} draws {b.primary_card.name}.")
            self.update_top_deck_reveal(player)
        if amount > len(player.deck):
            print(f"{player.get_name()} has no more cards to draw.")
        return True

    def create_token(self, player: Player, name: str, attack: int, health: int):
        from swu_engine.card import Card
        token_card = Card(name, "Token Back", cost=0, card_type="unit", attack=attack, health=health)
        token_bundle = CardBundle(token_card, owner_id=player.get_player_id())
        # Simplified: put directly into player's discard pile or future arena logic
        player.discard_pile.append(token_bundle)
        print(f"{player.get_name()} creates a {name} token.")
        return token_bundle

    def exile_card(self, player: Player, bundle: CardBundle):
        exile_zone = player.get_board().find_zone("Exile")
        moved = False
        for z in player.get_board().get_zones():
            for p in z.get_piles():
                if bundle in p.get_bundles():
                    player.get_board().move_to_zone(bundle, z, exile_zone)
                    player.exile_pile.append(bundle)  # keep list synced
                    moved = True
                    break
            if moved: break
        if not moved:
            for coll_name, coll in [
                ("hand", player.hand),
                ("deck", player.deck),
                ("discard_pile", player.discard_pile),
                ("resources", player.resources),
            ]:
                if bundle in coll:
                    coll.remove(bundle)
                    exile_zone.get_piles()[0].add_bundle(bundle)
                    player.exile_pile.append(bundle)  # keep list synced
                    moved = True
                    break
        print(f"{bundle.primary_card.name} is exiled from {player.get_name()}.")
        return True

    def return_to_hand(self, bundle: CardBundle):
        owner = self.get_player_by_id(bundle.owner_id)
        if owner:
            if bundle in owner.discard_pile:
                owner.discard_pile.remove(bundle)
            owner.hand.append(bundle)
            print(f"{bundle.primary_card.name} is returned to {owner.get_name()}'s hand.")

    def destroy_unit(self, bundle: CardBundle):
        owner = self.get_player_by_id(bundle.owner_id)
        for z in owner.get_board().get_zones():
            if z.get_name() in ("Ground Arena", "Space Arena"):
                for p in z.get_piles():
                    if bundle in p.get_bundles():
                        discard_zone = owner.get_board().find_zone("Discard")
                        owner.get_board().move_to_zone(bundle, z, discard_zone)
                        owner.discard_pile.append(bundle)  # keep list synced
                        print(f"{bundle.primary_card.name} is destroyed and moved to discard.")
                        return True
        return False

    def mill_cards(self, player: Player, amount: int):
        deck_zone = player.get_board().find_zone("Deck")
        discard_zone = player.get_board().find_zone("Discard")
        for _ in range(min(amount, len(player.deck))):
            bundle = player.deck.pop(0)
            player.top_deck_revealed = False
            discard_zone.get_piles()[0].add_bundle(bundle)
            player.discard_pile.append(bundle)  # keep list synced
            print(f"{player.get_name()} mills {bundle.primary_card.name}.")
            self.update_top_deck_reveal(player)
        return True

    def resolve_combat(self, attacker: CardBundle, defender):
        """Resolve a combat between attacker (unit) and defender (unit or base)."""
        atk_card = attacker.primary_card
        atk_power = attacker.effective_attack()
        atk_health = attacker.effective_health()

        # Defender stats
        if isinstance(defender, CardBundle):  # defending unit
            def_card = defender.primary_card
            def_power = defender.effective_attack()
            def_health = defender.effective_health()

            print(f"{atk_card.name} ({atk_power}/{atk_health}) fights {def_card.name} ({def_power}/{def_health})")

            # simultaneous damage
            defender.damage += atk_power
            attacker.damage += def_power

            print(f"{def_card.name} takes {atk_power} damage (total {defender.damage})")
            print(f"{atk_card.name} takes {def_power} damage (total {attacker.damage})")

            # check defeat for each
            self._check_defeat(defender)
            self._check_defeat(attacker)

        elif isinstance(defender, Base):
            print(f"{atk_card.name} ({atk_power}/{atk_health}) attacks {defender.name}!")
            defender.take_damage(atk_power)
            print(f"{defender.name} takes {atk_power} damage (health={defender.health})")
            self._check_base_defeat()

        else:
            print("Invalid defender for combat.")

    def shuffle_deck(self, player: Player):
        import random
        random.shuffle(player.deck)
        print(f"{player.get_name()} shuffles their deck.")

    def reveal_card(self, bundle: CardBundle):
        print(f"Revealed: {bundle.primary_card.name}")
        return True

    def peek_card(self, player: Player, bundle: CardBundle):
        # grant temporary peek permission
        bundle.peekers.add(player.get_player_id())
        print(f"{player.get_name()} peeks at {bundle.primary_card.name}.")
        return True

    def search_deck(self, player: Player, results: list[CardBundle]):
        deck_zone = player.get_board().find_zone("Deck")
        hand_zone = player.get_board().find_zone("Hand")
        for b in list(results):
            if b in player.deck:
                player.deck.remove(b)
                hand_zone.get_piles()[0].add_bundle(b)
                player.hand.append(b)  # keep list synced
                print(f"{player.get_name()} finds {b.primary_card.name}.")
                self.update_top_deck_reveal(player)
        return True

    def mill_and_reveal(self, player: Player, amount: int = 1,
                        condition_fn=None, followup_fn=None):
        for _ in range(min(amount, len(player.deck))):
            card_bundle = player.deck.pop(0)
            player.discard_pile.append(card_bundle)
            print(f"{player.get_name()} mills {card_bundle.primary_card.name}.")
            print(f"Revealed: {card_bundle.primary_card.name}")

            # Conditional follow-up
            if condition_fn and condition_fn(card_bundle):
                print(f"Condition met for {card_bundle.primary_card.name}.")
                if followup_fn:
                    followup_fn(self, player, card_bundle)
        return True

    def return_unit_to_hand(self, bundle: CardBundle):
        owner = self.get_player_by_id(bundle.owner_id)
        for z in owner.get_board().get_zones():
            if z.get_name() in ("Ground Arena", "Space Arena"):
                for p in z.get_piles():
                    if bundle in p.get_bundles():
                        hand_zone = owner.get_board().find_zone("Hand")
                        owner.get_board().move_to_zone(bundle, z, hand_zone)
                        owner.hand.append(bundle)  # keep list synced
                        bundle.damage = 0
                        bundle.exhausted = False
                        print(f"{bundle.primary_card.name} is returned to {owner.get_name()}'s hand.")
                        return True
        return False

    def detach_upgrade(self, target_bundle: CardBundle, upgrade_bundle: CardBundle):
        if upgrade_bundle in target_bundle.upgrades:
            target_bundle.upgrades.remove(upgrade_bundle)
            owner = self.get_player_by_id(upgrade_bundle.owner_id)
            discard_zone = owner.get_board().find_zone("Discard")
            discard_zone.get_piles()[0].add_bundle(upgrade_bundle)
            owner.discard_pile.append(upgrade_bundle)  # keep list synced
            print(
                f"{upgrade_bundle.primary_card.name} detached from "
                f"{target_bundle.primary_card.name} and discarded."
            )
            return True
        return False

    def _format_zone(self, owner: Player, zone: Zone, viewer: Player):
        """Format zone contents based on visibility rules."""
        total = sum(len(p.get_bundles()) for p in zone.get_piles())

        # Arenas are always public (cards fully visible)
        if zone.get_name() in ("Ground Arena", "Space Arena"):
            card_names = [b.primary_card.name for pile in zone.get_piles() for b in pile.get_bundles()]
            if card_names:
                return f"{zone.get_name()}:\n" + "\n".join(
                    f"    - {name}" for name in card_names
                )
            else:
                return f"{zone.get_name()}: (empty)"

        # Fully hidden zones (e.g., resources face-down)
        if zone.visibility == "hidden_all":
            return f"{zone.get_name()}: {total} cards (hidden)"

        # Owner-only zones (hand, deck)
        if zone.visibility == "hidden_owner":
            if viewer.get_player_id() == owner.get_player_id():
                card_names = [b.primary_card.name for pile in zone.get_piles() for b in pile.get_bundles()]
                if card_names:
                    return f"{zone.get_name()}:\n" + "\n".join(
                        f"    - {name}" for name in card_names
                    )
                return f"{zone.get_name()}: (empty)"
            else:
                return f"{zone.get_name()}: {total} cards (hidden)"

        # Public zones (discard, exile, etc.)
        card_names = [b.primary_card.name for pile in zone.get_piles() for b in pile.get_bundles()]
        if card_names:
            return f"{zone.get_name()}:\n" + "\n".join(
                f"    - {name}" for name in card_names
            )
        return f"{zone.get_name()}: (empty)"

    def update_top_deck_reveal(self, player: Player):
        """
        Keeps top deck reveal state consistent.
        - If top_deck_revealed is True but deck is empty, reset to False.
        - If top_deck_revealed is True and deck has cards, re-affirm reveal.
        """
        if not player.deck:
            if player.top_deck_revealed:
                player.top_deck_revealed = False
                print(f"{player.get_name()}'s deck is empty, top card reveal cleared.")
            return

        if player.top_deck_revealed:
            print(f"{player.get_name()}'s top card remains revealed: {player.deck[0].primary_card.name}")

    def remove_resource(self, player: Player, bundle: CardBundle, to_zone_name: str = "Discard"):
        """
        Remove a resource from the resource zone and move it to another zone.
        By default, resources go to discard, but this can be changed with to_zone_name.
        """
        if bundle not in player.resources:
            print(f"{bundle.primary_card.name} is not in {player.get_name()}'s resources.")
            return False

        res_zone = player.get_board().find_zone("Resources")
        target_zone = player.get_board().find_zone(to_zone_name)

        if res_zone and target_zone:
            player.resources.remove(bundle)             # keep list synced
            player.get_board().move_to_zone(bundle, res_zone, target_zone)

            # Update target list for discard/exile
            if to_zone_name.lower() == "discard":
                player.discard_pile.append(bundle)
            elif to_zone_name.lower() == "exile":
                player.exile_pile.append(bundle)

            print(f"{player.get_name()} removes resource {bundle.primary_card.name} → {to_zone_name}.")
            return True

        print(f"Failed to move {bundle.primary_card.name} from resources to {to_zone_name}.")
        return False

    def validate_decks(self):
        """
        Validate all players’ decks against SWU rules using Deck.validate().
        """
        raise NotImplementedError("Game.validate_decks() not yet implemented")

    def offer_mulligan_phase(self):
        """
        Offer mulligan choice to each player at game start.
        Integrate with Player.mulligan() and Deck.mulligan().
        """
        raise NotImplementedError("Game.offer_mulligan_phase() not yet implemented")

    def combat_phase(self):
        """
        Manage combat declarations:
        - Active player chooses attackers
        - Defending player assigns blockers (Sentinel rules enforced)
        - Call resolve_combat()
        """
        raise NotImplementedError("Game.combat_phase() not yet implemented")