from typing import Callable
from swu_engine.cardbundle import CardBundle
from swu_engine.base import Base

class Requirement:
    def __init__(self, req_type: str, description: str, validator_fn: Callable, min_targets=1, max_targets=1):
        self.req_type = req_type
        self.description = description
        self.validator_fn = validator_fn
        self.min_targets = min_targets
        self.max_targets = max_targets


class Action:
    def __init__(self, player_id: int, description: str, requirements: list[Requirement], execute_fn: Callable, follow_up_fn: Callable = None):
        self.player_id = player_id
        self.description = description
        self.requirements = requirements
        self.execute_fn = execute_fn
        self.follow_up_fn = follow_up_fn

    def get_requirements(self):
        return self.requirements

    def execute(self, targets: dict):
        result = self.execute_fn(targets)
        if self.follow_up_fn:
            self.follow_up_fn(targets, result)  # pass result if main fn returns something
        return result


class RulesEngine:
    def __init__(self):
        pass

    def get_legal_actions(self, game: 'Game', player: 'Player') -> list[Action]:
        """
        Return all legal actions available to a player during their turn.
        Currently: play any card from hand.
        """
        actions = []
        for bundle in list(player.hand):
            card = bundle.primary_card
            desc = f"Play {card.name} (cost {card.cost}, type {card.card_type})"
            actions.append(Action(
                player_id=player.get_player_id(),
                description=desc,
                requirements=[],
                execute_fn=lambda targets, b=bundle: game.play_card(player, b, extra_targets=targets)
            ))
        return actions


    def can_player_see(self, player: 'Player', bundle: 'CardBundle') -> bool:
        """Check if a player can see a given bundle."""
        # Find the zone the bundle belongs to
        zone = None
        for p in player.get_board().get_zones():
            for pile in p.get_piles():
                if bundle in pile.get_bundles():
                    zone = p
                    break

        # Default: if we can’t locate zone, fall back to True
        if not zone:
            return True

        # Arenas are always public
        if zone.get_name() in ("Ground Arena", "Space Arena"):
            return True

        # Public zones
        if zone.visibility == "public":
            return True

        # Owner-only zones (hand, deck)
        if zone.visibility == "hidden_owner":
            return bundle.owner_id == player.get_player_id()

        # Fully hidden zones (resources face-down)
        if zone.visibility == "hidden_all":
            return player.get_player_id() in getattr(bundle, "peekers", set())

        return True



    def grant_peek_permission(self, viewer: 'Player', bundle: CardBundle):
        bundle.peekers.add(viewer.get_player_id())
        print(f"{viewer.get_name()} is granted peek permission for {bundle.primary_card.name}.")

    # ---------- Validators ----------
    @staticmethod
    def _unit_in_play(game, bundle):
        return isinstance(bundle, CardBundle) and getattr(bundle.primary_card, "card_type", None) == "unit"

    @staticmethod
    def _damage_target_ok(game, target):
        return isinstance(target, Base) or (
            isinstance(target, CardBundle)
            and getattr(target.primary_card, "card_type", None) == "unit"
        )

    # ---------- Action Generators ----------
    def create_damage_action(self, game, player, amount: int, description: str = None) -> Action:
        desc = description or f"Deal {amount} damage"
        req = Requirement("target", desc, lambda g, p, t: self._damage_target_ok(g, t), 1, 1)
        return Action(
            player.get_player_id(),
            desc,
            [req],
            lambda targets, r=req: game.deal_damage(targets[r][0], amount)
        )

    def create_heal_action(self, game, player, amount: int, description: str = None) -> Action:
        desc = description or f"Heal {amount} damage"
        req = Requirement("target", desc, lambda g, p, t: isinstance(t, CardBundle) and t.damage > 0, 1, 1)
        return Action(
            player.get_player_id(),
            desc,
            [req],
            lambda targets, r=req: game.heal_unit(targets[r][0], amount)
        )

    def create_discard_action(self, game, player, description: str = "Discard a card from hand") -> Action:
        req = Requirement("target", description, lambda g, p, b: b in player.hand, 1, 1)
        return Action(
            player.get_player_id(),
            description,
            [req],
            lambda targets, r=req: game.discard_card_from_hand(player, targets[r][0])
        )

    def create_draw_action(self, game, player, amount: int = 1, description: str = None) -> Action:
        desc = description or f"Draw {amount} card(s)"
        return Action(
            player.get_player_id(),
            desc,
            [],
            lambda targets: game.draw_cards(player, amount)
        )

    def create_token_action(self, player: 'Player', token: 'Token') -> Action:
        """
        Create a token and put it directly into play under the player's control.
        Arena is determined automatically via CardBundle.get_default_arena().
        Automatically forces token_type="unit" since these are in-play tokens.
        """

        # 🔹 Ensure token acts as a unit in play
        token.token_type = "unit"

        # Build description string
        desc_parts = [token.token_info]
        atk = getattr(token, "attack", None)
        hp = getattr(token, "health", None)
        if atk is not None and hp is not None:
            desc_parts.append(f"{atk}/{hp}")
        kws = getattr(token, "keywords", None)
        if kws:
            desc_parts.append(", ".join(kws))
        desc = f"Create token ({' '.join(desc_parts)})"

        def execute_fn(targets):
            from swu_engine.cardbundle import CardBundle
            from swu_engine.board import Pile
            bundle = CardBundle(primary_card=None, owner_id=player.get_player_id(), tokens=[token])

            zone_name = bundle.get_default_arena()
            arena = player.get_board().find_zone(zone_name)
            if arena:
                if not arena.get_piles():
                    arena.add_pile(Pile(f"{arena.zone_id}_pile"))
                arena.get_piles()[0].add_bundle(bundle)
                print(f"{player.get_name()} creates a token in the {zone_name}: {token.token_info}")
            return True

        return Action(
            player.get_player_id(),
            desc,
            [],
            execute_fn
        )


    def create_buff_action(self, game, player, amount_attack: int = 0, amount_health: int = 0,
                           keywords: list[str] = None, description: str = None,
                           duration_phase: str = None) -> Action:
        desc = description or f"Buff a unit +{amount_attack}/+{amount_health}"
        req = Requirement("target", desc,
                          lambda g, p, b: isinstance(b, CardBundle) and b.primary_card.card_type == "unit", 1, 1)

        def _apply_buff(targets, r=req):
            bundle = targets[r][0]
            bundle.attack_buff += amount_attack
            bundle.health_buff += amount_health
            if keywords:
                bundle.temp_keywords.update(keywords)
            print(f"{bundle.primary_card.name} buffed: +{amount_attack}/+{amount_health} {keywords or ''}")
            # Register revert
            if duration_phase:
                def _revert_buff(g: 'Game', bundle=bundle):
                    bundle.attack_buff -= amount_attack
                    bundle.health_buff -= amount_health
                    if keywords:
                        bundle.temp_keywords.difference_update(keywords)
                    print(f"{bundle.primary_card.name}'s temporary buff expired.")

                game.register_delayed_effect(duration_phase, _revert_buff)

        return Action(player.get_player_id(), desc, [req], _apply_buff)

    def create_debuff_action(self, game, player, amount_attack: int = 0, amount_health: int = 0,
                             remove_keywords: list[str] = None, description: str = None,
                             duration_phase: str = None) -> Action:
        desc = description or f"Debuff a unit -{amount_attack}/-{amount_health}"
        req = Requirement("target", desc, lambda g, p, b: isinstance(b, CardBundle) and b.primary_card.card_type == "unit", 1, 1)

        def _apply_debuff(targets, r=req):
            bundle = targets[r][0]
            bundle.attack_buff -= amount_attack
            bundle.health_buff -= amount_health
            if remove_keywords:
                bundle.temp_keywords.difference_update(remove_keywords)
            print(f"{bundle.primary_card.name} debuffed: -{amount_attack}/-{amount_health} remove {remove_keywords or ''}")
            if duration_phase:
                def _revert_debuff(g: 'Game', bundle=bundle):
                    bundle.attack_buff += amount_attack
                    bundle.health_buff += amount_health
                    print(f"{bundle.primary_card.name}'s temporary debuff expired.")
                game.register_delayed_effect(duration_phase, _revert_debuff)

        return Action(player.get_player_id(), desc, [req], _apply_debuff)

    def create_add_keyword_action(self, game, player, keyword: str, description: str = None,
                                  duration_phase: str = None) -> Action:
        desc = description or f"Give unit {keyword}"
        req = Requirement("target", desc, lambda g, p, b: isinstance(b, CardBundle) and b.primary_card.card_type == "unit", 1, 1)

        def _apply_kw(targets, r=req):
            bundle = targets[r][0]
            bundle.temp_keywords.add(keyword)
            print(f"{bundle.primary_card.name} gains keyword {keyword}")
            if duration_phase:
                def _revert_kw(g: 'Game', bundle=bundle):
                    if keyword in bundle.temp_keywords:
                        bundle.temp_keywords.remove(keyword)
                        print(f"{bundle.primary_card.name} loses temporary keyword {keyword}")
                game.register_delayed_effect(duration_phase, _revert_kw)

        return Action(player.get_player_id(), desc, [req], _apply_kw)

    def create_remove_keyword_action(self, game, player, keyword: str, description: str = None,
                                     duration_phase: str = None) -> Action:
        desc = description or f"Remove keyword {keyword}"
        req = Requirement("target", desc, lambda g, p, b: isinstance(b, CardBundle) and b.primary_card.card_type == "unit", 1, 1)

        def _remove_kw(targets, r=req):
            bundle = targets[r][0]
            if keyword in bundle.temp_keywords:
                bundle.temp_keywords.remove(keyword)
                print(f"{bundle.primary_card.name} loses keyword {keyword}")
            if duration_phase:
                def _revert_kw(g: 'Game', bundle=bundle):
                    bundle.temp_keywords.add(keyword)
                    print(f"{bundle.primary_card.name} regains temporary keyword {keyword}")
                game.register_delayed_effect(duration_phase, _revert_kw)

        return Action(player.get_player_id(), desc, [req], _remove_kw)

    @staticmethod
    def _can_attack(game, attacker, defender, attacking_player):
        # must be a unit in play and not exhausted
        if attacker.primary_card.card_type != "unit" or attacker.exhausted:
            return False

        # defender must be a base or a unit
        if not isinstance(defender, (CardBundle, Base)):
            return False

        # arena match check
        atk_type = getattr(attacker.primary_card, "subtype", None)
        if isinstance(defender, CardBundle):
            def_type = getattr(defender.primary_card, "subtype", None)
            if atk_type == "ground" and def_type == "space":
                return False
            if atk_type == "space" and def_type == "ground":
                return False
        elif isinstance(defender, Base):
            if atk_type not in ("ground", "space"):
                return False

        # sentinel restriction: must attack enemy sentinels first
        enemy = [p for p in game.players if p.get_player_id() != attacking_player.get_player_id()][0]
        sentinels = []
        for z in enemy.get_board().get_zones():
            for p in z.get_piles():
                for b in p.get_bundles():
                    if b.has_keyword("Sentinel"):
                        sentinels.append(b)
        if sentinels:
            if isinstance(defender, Base) or (isinstance(defender, CardBundle) and not defender.has_keyword("Sentinel")):
                return False

        return True


    def create_attack_action(self, game, player, attacker) -> Action:
        desc = f"Attack with {attacker.primary_card.name}"
        req = Requirement(
            "target",
            desc,
            lambda g, p, target: self._can_attack(g, attacker, target, player),
            1, 1
        )

        def _do_attack(targets, r=req):
            defender = targets[r][0]
            attacker.exhaust()
            target_name = getattr(defender, "name", getattr(defender.primary_card, "name", "target"))
            print(f"{attacker.primary_card.name} attacks {target_name}!")
            game.resolve_combat(attacker, defender)

        return Action(player.get_player_id(), desc, [req], _do_attack)

    def create_shuffle_action(self, game, player, description: str = "Shuffle your deck") -> Action:
        return Action(
            player.get_player_id(),
            description,
            [],
            lambda targets: game.shuffle_deck(player)
        )

    def create_reveal_action(self, game, player, description: str = "Reveal a card") -> Action:
        req = Requirement("target", description, lambda g, p, b: isinstance(b, CardBundle), 1, 1)
        return Action(
            player.get_player_id(),
            description,
            [req],
            lambda targets, r=req: game.reveal_card(targets[r][0])
        )

    def create_peek_action(self, game, player, description: str = "Peek at a card") -> Action:
        req = Requirement("target", description, lambda g, p, b: isinstance(b, CardBundle), 1, 1)
        return Action(
            player.get_player_id(),
            description,
            [req],
            lambda targets, r=req: game.peek_card(player, targets[r][0])
        )

    def create_search_action(self, game, player, match_fn, max_targets: int = 1,
                             description: str = "Search your deck") -> Action:
        req = Requirement(
            "target",
            description,
            lambda g, p, b: isinstance(b, CardBundle) and b in player.deck and match_fn(b),
            1,
            max_targets
        )
        return Action(
            player.get_player_id(),
            description,
            [req],
            lambda targets, r=req: game.search_deck(player, targets[r])
        )
    def create_mill_and_reveal_action(self, game, player, amount: int = 1,
                                      condition_fn=None, followup_fn=None,
                                      description: str = None) -> Action:
        """
        Mill and reveal cards, with optional conditional follow-up.
        - condition_fn(card_bundle) -> bool
        - followup_fn(game, player, card_bundle) -> None
        """
        desc = description or f"Mill and reveal top {amount} card(s)"
        return Action(
            player.get_player_id(),
            desc,
            [],
            lambda targets: game.mill_and_reveal(player, amount,
                                                condition_fn=condition_fn,
                                                followup_fn=followup_fn)
        )

    def create_mill_action(self, game, player, amount: int, description: str = None,
                           follow_up_fn: Callable = None) -> Action:
        desc = description or f"Mill {amount} cards"
        return Action(
            player.get_player_id(),
            desc,
            [],
            lambda targets: game.mill_cards(player, amount),
            follow_up_fn=follow_up_fn
        )

    def get_response_actions(self, game: 'Game', player: 'Player') -> list[Action]:
        """
        Return all legal response actions available to a player.
        Example: play an event with Ambush from hand.
        """
        responses = []

        # Check for Ambush cards in hand
        for bundle in list(player.hand):
            card = bundle.primary_card
            if "Ambush" in getattr(card, "keywords", []):
                desc = f"Play {card.name} with Ambush"
                responses.append(Action(
                    player_id=player.get_player_id(),
                    description=desc,
                    requirements=[],
                    execute_fn=lambda targets, b=bundle: game.play_card(player, b, extra_targets=targets)
                ))

        return responses

    def execute_response_action(self, game: 'Game', player: 'Player', action: dict) -> bool:
        """
        Execute a response action chosen during a priority window.
        Response actions include Ambush, interrupts, triggered abilities, etc.
        Returns True if an action was successfully executed.
        """
        if action["type"] == "ambush":
            bundle = action["card"]
            card = bundle.primary_card

            # Place unit in the arena
            arena = game._ensure_arena(player, card.subtype or "ground")
            if not arena.get_piles():
                arena.add_pile(game.Pile(f"{arena.zone_id}_pile"))
            arena.get_piles()[0].add_bundle(bundle)
            print(f"{card.name} enters play with Ambush!")

            # Immediately offer attack option
            legal_targets = []
            for opp in game.players:
                if opp.get_player_id() == player.get_player_id():
                    continue
                for zone_name in ("Ground Arena", "Space Arena"):
                    z = opp.get_board().find_zone(zone_name)
                    if z:
                        for pile in z.get_piles():
                            for t in pile.get_bundles():
                                legal_targets.append(t)
                if opp.base:
                    legal_targets.append(opp.base)

            if legal_targets:
                target = legal_targets[0]  # selection logic / UI later
                print(f"{card.name} (Ambush) attacks {getattr(target, 'name', target.primary_card.name)} immediately!")
                game.deal_damage(target, card.attack)
                bundle.exhaust()  # Ambush attack still exhausts the unit
            else:
                print(f"{card.name} had no legal Ambush targets.")

            return True

        # Other response action types go here later
        return False

    def create_ambush_response_action(self, bundle: 'CardBundle'):
        """
        Create a response action dict for playing an Ambush unit from hand.
        """
        return {
            "type": "ambush",
            "card": bundle,
            "description": f"Play {bundle.primary_card.name} with Ambush",
        }

    def apply_aspect_penalty(self, player, card):
        """
        Apply aspect penalty if the card’s aspects do not match player’s resources.
        Typically: +1 cost per missing aspect.
        """
        raise NotImplementedError("apply_aspect_penalty() not yet implemented")

    def handle_keyword(self, keyword, source_bundle, context):
        """
        Dispatch keyword resolution.
        Example: Sentinel (restrict attack), Overwhelm (excess dmg to base),
                 Restore (heal base), Ambush (flash-speed play).
        """
        raise NotImplementedError("handle_keyword() not yet implemented")
#

