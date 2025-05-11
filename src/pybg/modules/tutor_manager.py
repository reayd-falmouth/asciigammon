# src/pybg/modules/tutor_manager.py

import pygame
from typing import List, Tuple

from pybg.core.events import EVENT_GAME
from pybg.modules.base_module import BaseModule
from pybg.gnubg.pub_eval import pubeval_x
from pybg.gnubg.match import GameState
from pybg.core.logger import logger
from pybg.core.board import Play
from copy import deepcopy


class TutorManager(BaseModule):
    category = "Tutor"

    def __init__(self, shell):
        self.shell = shell
        self.evaluated_plays: List[Tuple[float, Play]] = []
        self.current_hint_index: int = 0
        self.max_hint_moves: int = 0
        self.tutor_mode: str = "regular"
        self.suppress_enter = (
            True  # fix for a race condition with the hint and apply hint functions
        )
        self.original_position = None

    def evaluate_and_sort_plays(self) -> None:
        plays = self.shell.game.generate_plays()
        self.evaluated_plays.clear()

        for play in plays:
            pos_array = play.position.to_array()
            is_race = play.position.classify().name == "RACE"
            score = pubeval_x(is_race, pos_array)
            self.evaluated_plays.append((score, play))

        self.evaluated_plays.sort(reverse=True, key=lambda x: x[0])
        self.evaluated_plays = self.evaluated_plays[: self.max_hint_moves]
        self.current_hint_index = 0

    def format_play_moves(self, play: Play) -> str:
        def format_point(p: int) -> str:
            return "bar" if p == -1 else "off" if p == 0 else str(p)

        return " ".join(
            f"{format_point(m.source + 1)}/{format_point(m.destination + 1)}"
            for m in play.moves
        )

    def cmd_hint(self, args):
        s = self.shell

        if not s.game:
            return "There is no game started. Type `new` to start a game."

        s.active_module = "tutor"

        self.original_position = deepcopy(self.shell.game.position)

        # Check if user typed a number after "hint"
        self.max_hint_moves = (
            int(args[0])
            if args and args[0].isdigit()
            else s.settings.get("hint_top_n", 5)
        )

        if s.game.match.player != s.game.player.player_type:
            message = "It's not your turn!"
            return self.shell.update_output_text(message, show_board=True)
        if s.game.match.game_state == GameState.RESIGNED:
            message = f"Your opponent has offered to resign a {s.game.match.resign.phrase}, accept or reject?"
            return self.shell.update_output_text(message, show_board=True)
        if s.game.match.game_state == GameState.DOUBLED:
            message = (
                f"Cube offered at {s.game.match.cube_value}, take, drop or redouble?"
            )
            return self.shell.update_output_text(message, show_board=True)
        if s.game.match.game_state == GameState.ON_ROLL:
            message = "Roll, double or resign?"
            return self.shell.update_output_text(message, show_board=True)
        if s.game.match.game_state == GameState.TAKE:
            message = "Double accepted, roll or resign?"
            return self.shell.update_output_text(message, show_board=True)
        if s.game.match.game_state == GameState.ROLLED:
            self.evaluate_and_sort_plays()
        return self.render_current_hint()

    def render_current_hint(self):
        if not self.evaluated_plays:
            return self.shell.update_output_text("No hints available.", show_board=True)

        # Restore original position before previewing
        if self.original_position:
            self.shell.game.position = deepcopy(self.original_position)

        lines = ["HINTS (use Up/Down keys to navigate):\n"]
        for i, (score, play) in enumerate(self.evaluated_plays):
            moves_str = " ".join(
                f"{m.source + 1}/{m.destination + 1}" for m in play.moves
            )
            prefix = "> " if i == self.current_hint_index else "  "
            suffix = " *" if i == 0 else ""
            lines.append(f"{prefix}{i+1:2d}. {moves_str:<15} {score:+.3f}{suffix}")

        # Temporarily apply the board state without committing
        play: Play = self.evaluated_plays[self.current_hint_index][1]
        self.shell.game.position = play.position
        return self.shell.update_output_text("\n".join(lines), show_board=True)

    def apply_current_hint(self):
        if not self.evaluated_plays:
            return self.shell.update_output_text("No hint to apply.", show_board=True)

        score, play = self.evaluated_plays[self.current_hint_index]
        self.shell.game.play([(m.source, m.destination) for m in play.moves])
        self.shell.active_module = None
        return self.shell.update_output_text(show_board=True)

    def next_hint(self):
        if not self.evaluated_plays:
            return
        if self.current_hint_index < len(self.evaluated_plays) - 1:
            self.current_hint_index += 1
            return self.render_current_hint()

    def previous_hint(self):
        if not self.evaluated_plays:
            return
        if self.current_hint_index > 0:
            self.current_hint_index -= 1
            return self.render_current_hint()

    def exit_hint_mode(self):
        if self.original_position:
            self.shell.game.position = deepcopy(self.original_position)
        self.shell.active_module = None
        self.original_position = None
        return self.shell.update_output_text(show_board=True)

    def handle_event(self, event):
        if self.shell.active_module != "tutor":
            return

        if event.type == pygame.KEYDOWN:
            if self.suppress_enter and event.key == pygame.K_RETURN:
                self.suppress_enter = False  # Skip this Enter key
                return
            if event.key == pygame.K_UP:
                return self.previous_hint()
            elif event.key == pygame.K_DOWN:
                return self.next_hint()
            # elif event.key == pygame.K_RETURN:
            #     return self.apply_current_hint()
            elif event.key == pygame.K_ESCAPE:
                return self.exit_hint_mode()

    def cmd_tutor_mode(self, args):
        valid_modes = {"regular", "tutor", "training", "competition"}
        if not args or args[0] not in valid_modes:
            return self.shell.update_output_text(
                "Usage: tutor_mode [regular|tutor|training|competition]",
                show_board=False,
            )
        self.tutor_mode = args[0]
        return self.shell.update_output_text(
            f"Tutor mode set to: {self.tutor_mode}", show_board=False
        )

    def register(self):
        return (
            {
                "hint": self.cmd_hint,
                "tutor_mode": self.cmd_tutor_mode,
            },
            {},
            {
                "hint": "Enter interactive hint browsing mode",
                "tutor_mode": "Set hint mode: regular, tutor, training, competition",
            },
        )


def register(shell):
    mod = TutorManager(shell)
    shell.tutor_manager = mod  # Make it globally accessible
    return mod
