from swu_engine.game import Game
from swu_engine.player import Player
from swu_engine.card import Card
from swu_engine.cardbundle import CardBundle
from swu_engine.base import Base

if __name__ == "__main__":
    g = Game()

    p1 = Player(1, "Alice")
    p2 = Player(2, "Bob")
    g.add_player(p1)
    g.add_player(p2)

    p1.base = Base("Yavin IV", 30)
    p2.base = Base("Death Star", 30)

    def blaster_effect(game, player, targets):
        game.deal_damage(p2.base, 2)
    blaster = Card("Blaster Shot", "Back", cost=1, card_type="event", effect_fn=blaster_effect)

    p1.hand.append(CardBundle(blaster, owner_id=p1.get_player_id()))

    print("\n-- START --")
    g.show_board()

    g.turn_manager.current_phase_index = g.turn_manager.phases.index(next(p for p in g.turn_manager.phases if p.name == "Main"))

    actions = g.rules.get_legal_actions(g, p1)
    action = [a for a in actions if "Blaster Shot" in a.description][0]
    action.execute({})

    print("\n-- END --")
    g.show_board()
