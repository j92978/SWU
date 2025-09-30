# turn_manager.py
from swu_engine import hooks

class TurnManager:
    def __init__(self, players, phases, game_ref):
        self.players = players
        self.phases = phases
        self.phase_index = 0
        self.round_number = 1
        self.initiative_player_index = 0
        self.current_player_index = 0
        self.game_ref = game_ref

    def get_current_player(self):
        return self.players[self.current_player_index]

    def get_initiative_player(self):
        return self.players[self.initiative_player_index]

    def get_current_phase(self):
        return self.phases[self.phase_index]

    def open_priority_window(self, game, phase_name):
        print(f"Priority window opened during {phase_name} phase.")

    def next_phase(self):
        """Advance to the next phase, handling turn/round transitions and hooks."""
        self.phase_index += 1

        if self.phase_index >= len(self.phases):
            # End of player's turn
            self.phase_index = 0

            # 🔹 End-of-turn hooks
            for fn in hooks.get_hooks_by_timing("end_of_turn"):
                fn(self, self.get_current_player(), self.game_ref)

            # Move to next player
            self.current_player_index = (self.current_player_index + 1) % len(self.players)

            # If we wrapped back to initiative player, round ends
            if self.current_player_index == self.initiative_player_index:
                # 🔹 End-of-round hooks
                for fn in hooks.get_hooks_by_timing("end_of_round"):
                    fn(self, self.game_ref)

                # Flip initiative
                self.initiative_player_index = (self.initiative_player_index + 1) % len(self.players)
                self.current_player_index = self.initiative_player_index

                # Increment round
                self.round_number += 1
                print(f"--- New Round {self.round_number} ---")
                print(f"Initiative passes to {self.get_initiative_player().get_name()}")

                # 🔹 Start-of-round hooks
                for fn in hooks.get_hooks_by_timing("start_of_round"):
                    fn(self, self.game_ref)

            # 🔹 Start-of-turn hooks
            for fn in hooks.get_hooks_by_timing("start_of_turn"):
                fn(self, self.get_current_player(), self.game_ref)

        phase = self.get_current_phase()

        if phase.name in ("Main", "Combat"):
            self.open_priority_window(self.game_ref, phase.name)

        return self.get_current_phase()
