# hooks.py

# --- Hook function definitions ---

def refresh_resources(turn_manager, game, *_):
    """Ready all exhausted resources at the start of each round."""
    for player in game.players:
        for res in player.resources:
            res.exhausted = False
    print("All resources refreshed.")


def ready_all_units(turn_manager, game, *_):
    """Ready all units at the start of each round."""
    for player in game.players:
        for zone in player.get_board().zones:
            if zone.get_name() in ("Ground Arena", "Space Arena"):
                for pile in zone.get_piles():
                    for bundle in pile.get_bundles():
                        bundle.exhausted = False
    print("All units readied.")


def clean_up_delayed_effects(turn_manager, game, *_):
    """Clear delayed effects at the end of the round."""
    if hasattr(game, "delayed_effects"):
        game.delayed_effects.clear()
        print("Delayed effects cleared.")


def draw_at_start_of_turn(turn_manager, player, game, *_):
    """Each player draws 1 card at the start of their turn."""
    if hasattr(game, "draw_cards"):
        game.draw_cards(player, 1)
        print(f"{player.get_name()} draws 1 card at the start of their turn.")

def ready_leaders(turn_manager, game, *_):
    """At the start of each round, ready all leaders."""
    for player in game.players:
        leader_zone = player.get_board().find_zone("Leader")
        if leader_zone:
            for pile in leader_zone.get_piles():
                for bundle in pile.get_bundles():
                    bundle.exhausted = False
                    print(f"{player.get_name()}'s leader is ready.")

def mulligan(turn_manager, game, *_):
    """Round 1: each player may mulligan (redraw hand)."""
    if turn_manager.round_number == 1:
        for player in game.players:
            if hasattr(player, "hand") and player.hand:
                count = len(player.hand)
                while player.hand:
                    game.move_to_discard(player, player.hand.pop(0))
                game.draw_cards(player, count)
                print(f"{player.get_name()} mulligans and redraws {count} cards.")

def discard_at_end_of_turn(turn_manager, player, game, *_):
    """Each player discards 1 card at the end of their turn if they have any."""
    if hasattr(player, "hand") and player.hand:
        discarded = player.hand.pop(0)
        game.move_to_discard(player, discarded)
        print(f"{player.get_name()} discards 1 card at the end of their turn.")


def enforce_hand_limit(turn_manager, player, game, *_):
    """At end of turn, enforce a maximum hand size of 7 cards."""
    limit = 7
    while len(player.hand) > limit:
        discarded = player.hand.pop(0)  # discard the first card
        game.move_to_discard(player, discarded)
        print(f"{player.get_name()} discards down to {limit} card limit.")

# --- Hook registry ---

HOOK_REGISTRY = {}

HOOK_REGISTRY.update({
    "refresh_resources": {
        "fn": refresh_resources,
        "timing": "start_of_round",
    },
    "ready_all_units": {
        "fn": ready_all_units,
        "timing": "start_of_round",
    },
    "clean_up_delayed_effects": {
        "fn": clean_up_delayed_effects,
        "timing": "end_of_round",
    },
    "draw_at_start_of_turn": {
        "fn": draw_at_start_of_turn,
        "timing": "start_of_turn",
    },
    "discard_at_end_of_turn": {
        "fn": discard_at_end_of_turn,
        "timing": "end_of_turn",
    },
    "mulligan": {
        "fn": mulligan,
        "timing": "start_of_round"
    },
    "ready_leaders": {
        "fn": ready_leaders,
        "timing": "start_of_round"
    },
        "enforce_hand_limit": {
            "fn": enforce_hand_limit,
            "timing": "end_of_turn"
    },
})


# --- Hook helpers ---

def get_hooks_by_timing(timing: str):
    """Return all registered hook functions for a given timing."""
    return [entry["fn"] for entry in HOOK_REGISTRY.values() if entry["timing"] == timing]


def register(name: str, fn, timing: str):
    """Register a new hook dynamically."""
    HOOK_REGISTRY[name] = {"fn": fn, "timing": timing}
