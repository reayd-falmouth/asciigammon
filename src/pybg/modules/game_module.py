import traceback
from typing import Tuple

from pybg.agents.factory import create_agent
from pybg.core.board import BoardError
from pybg.core.logger import logger
from pybg.core.player import PlayerType
from pybg.gnubg.match import Resign
from pybg.modules.base_module import BaseModule
from pybg.variants import AceyDeucey, Backgammon, Hypergammon, Nackgammon


class GameModule(BaseModule):
    category = "Game"

    def __init__(self, shell):
        self.shell = shell

    def guard_game(self):
        if not self.shell.game:
            raise ValueError("Start a game first with 'new'.")
        else:
            self.shell.active_module = "game"

    def parse_moves(self, move_args) -> Tuple[Tuple[int, int], ...]:
        if not move_args:
            raise BoardError(
                "You must specify at least one move in the format `source/dest`."
            )

        # Expecting input like ['13/12', '12/11']
        moves = []
        for arg in move_args:
            if "/" not in arg:
                raise BoardError(
                    f"Invalid move format: '{arg}'. Expected format: source/dest.\n\n"
                )
            try:
                source_str, dest_str = arg.split("/")
                source = int(source_str) - 1
                dest = int(dest_str) - 1
                moves.append((source, dest))
            except ValueError:
                raise BoardError(
                    f"Invalid numbers in move: '{arg}'. Must be integers like 13/12.\n\n"
                )

        # Validate against legal moves
        legal_plays = self.shell.game.generate_plays()
        legal_move_sets = [
            tuple((m.source, m.destination) for m in play.moves) for play in legal_plays
        ]

        if tuple(moves) not in legal_move_sets:
            raise BoardError(
                f"Illegal move sequence: {' '.join(move_args)}\n\nLegal moves:\n"
            )

        return tuple(moves)

    def cmd_new(self, args):
        s = self.shell
        s.current_match_ref = s.history_module.get_current_match_ref()
        game_class = {
            "backgammon": Backgammon,
            "nackgammon": Nackgammon,
            "acey-deucey": AceyDeucey,
            "hypergammon": Hypergammon,
        }.get(s.settings["variant"], Backgammon)

        s.game = game_class()
        s.game.match.length = (
            s.settings["match_length"] if s.settings["game_mode"] == "match" else 0
        )
        s.game.auto_doubles = bool(s.settings["autodoubles"])
        s.game.jacoby = bool(s.settings["jacoby"])
        s.game.start()
        s.player0_agent = create_agent(
            s.settings["player_agent"], PlayerType.ZERO, s.game
        )
        s.player1_agent = create_agent(
            s.settings["opponent_agent"], PlayerType.ONE, s.game
        )
        s.sound_manager.play_sound("roll")
        s.active_module = "game"
        return s.update_output_text(show_board=True)

    def cmd_debug(self, args):
        s = self.shell
        s.guard_game()
        m, p = s.game.match, s.game.position
        debug_lines = [
            "DEBUG OUTPUT\n\nMatch State",
            f"  Player perspective: {m.player.name}",
            f"  Turn              : {m.turn.name}",
            f"  Cube holder       : {m.cube_holder.name}",
            f"  Cube value        : {m.cube_value}",
            f"  Game state        : {m.game_state.name}",
            f"  Double pending?   : {m.double}",
            f"  Dice              : {m.dice}",
            f"  Match length      : {m.length}",
            f"  Score (P0)        : {m.player_0_score}",
            f"  Score (P1)        : {m.player_1_score}",
            "",
            "Position State",
            f"  Player bar        : {p.player_bar}",
            f"  Player off        : {p.player_off}",
            f"  Opponent bar      : {p.opponent_bar}",
            f"  Opponent off      : {p.opponent_off}",
            f"  Board points      : {p.board_points}",
            "",
            f"Legal Actions: {s.game.valid_actions()}",
            f"Action Mask Indices: {[i for i,v in enumerate(s.game.action_mask()) if v]}",
        ]
        return s.update_output_text("\n".join(debug_lines), show_board=False)

    def cmd_roll(self, args):
        self.shell.guard_game()
        self.shell.game.roll()
        # self.shell.log_current_state(
        #     f"{self.shell.game.match.turn.name} rolled {self.shell.game.match.dice}"
        # )
        return self.shell.update_output_text(show_board=True)

    def cmd_move(self, args):
        s = self.shell
        self.guard_game()
        try:
            moves = self.parse_moves(args)
            s.game.play(moves)
            # s.log_current_state(f"{s.game.match.turn.name} moved {moves}")
        except Exception as e:
            logger.error("Move error:\n" + traceback.format_exc())
            return f"Invalid move: {e}"
        return s.update_output_text(show_board=True)

    def cmd_double(self, args):
        return self._basic("double")

    def cmd_take(self, args):
        return self._basic("take")

    def cmd_drop(self, args):
        return self._basic("drop")

    def cmd_accept(self, args):
        return self._basic("accept")

    def cmd_reject(self, args):
        return self._basic("reject")

    def cmd_resign(self, args):
        s = self.shell
        s.guard_game()
        if args and args[0] in ("single", "gammon", "backgammon"):
            resign_map = {
                "single": Resign.SINGLE_GAME,
                "gammon": Resign.GAMMON,
                "backgammon": Resign.BACKGAMMON,
            }
            s.game.resign(resign_map[args[0]])
            return s.update_output_text(show_board=True)
        raise ValueError("Usage: resign [single|gammon|backgammon]")

    def cmd_show(self, args):
        return self.shell.update_output_text(show_board=True)

    def _basic(self, cmd):
        self.shell.guard_game()
        getattr(self.shell.game, cmd)()
        # self.shell.log_current_state(f"{self.shell.game.match.turn.name} {cmd}s")
        return self.shell.update_output_text(show_board=True)

    def register(self):
        return (
            {
                "new": self.cmd_new,
                "debug": self.cmd_debug,
                "roll": self.cmd_roll,
                "move": self.cmd_move,
                "double": self.cmd_double,
                "take": self.cmd_take,
                "drop": self.cmd_drop,
                "accept": self.cmd_accept,
                "reject": self.cmd_reject,
                "resign": self.cmd_resign,
                "show": self.cmd_show,
            },
            {},
            {
                "new": "Start a new game with current settings",
                "roll": "Roll the dice",
                "move": "Move checkers (e.g. move 6/1 8/2)",
                "double": "Offer the doubling cube",
                "take": "Accept a double",
                "drop": "Decline a double",
                "accept": "Accepts a resignation",
                "reject": "Rejects a resignation",
                "resign": "Resign (single, gammon, backgammon)",
                "debug": "Debug current game state",
                "show": "Prints the board to screen",
            },
        )


def register(shell):
    return GameModule(shell)
