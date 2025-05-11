import json
import os
import pygame
from datetime import datetime
from typing import List, Dict, TypedDict

from pybg.constants import ASSETS_DIR
from pybg.core.events import EVENT_GAME
from pybg.core.logger import logger
from pybg.modules.base_module import BaseModule


class MoveEntry(TypedDict):
    timestamp: str
    game_id: str
    message: str


class MatchHistoryEntry(TypedDict):
    created: str
    moves: List[MoveEntry]


class HistoryManager(BaseModule):
    category = "History"
    match_history_path = f"{ASSETS_DIR}/match_history.json"

    def __init__(self, shell):
        self.shell = shell
        self.matches: Dict[str, MatchHistoryEntry] = {}
        self.match_refs: List[str] = []
        self.current_match_index: int = 0
        self.current_move_index: int = 0
        self.load_from_file()

    def record_move(self, match_ref: str, game_id: str, message: str = ""):
        now = datetime.now().isoformat()

        if match_ref not in self.matches:
            self.matches[match_ref] = {"created": now, "moves": []}
            self.match_refs.append(match_ref)

        self.matches[match_ref]["moves"].append(
            {"timestamp": now, "game_id": game_id, "message": message}
        )
        self.current_move_index = len(self.matches[match_ref]["moves"]) - 1
        self.save_to_file(f"{ASSETS_DIR}/match_history.json")

    def get_current_match_ref(self) -> str:
        if not self.match_refs:
            return ""
        return self.match_refs[self.current_match_index]

    # def get_current_state(self) -> tuple[list[str], str]:
    #     match_ref = self.get_current_match_ref()
    #     entry = self.matches.get(match_ref)
    #     if not entry or not entry["moves"]:
    #         return [""], ""
    #     move = entry["moves"][self.current_move_index]
    #     return move["game_id"].split(":"), move["message"]

    def update_view_to_current_move(self):
        match_ref = self.get_current_match_ref()
        if match_ref not in self.matches:
            return

        move = self.matches[match_ref]["moves"][self.current_move_index]
        pos_id, match_id = move["game_id"].split(":")

        # Update the game board
        self.shell.game.position = self.shell.game.position.decode(pos_id)
        self.shell.game.match = self.shell.game.match.decode(match_id)

        # Build move log
        moves = self.matches[match_ref]["moves"]
        lines = [f"LOG for Match {match_ref[:8]} (Moves: {len(moves)}):\n"]
        for i, m in enumerate(moves):
            prefix = "> " if i == self.current_move_index else "  "
            lines.append(
                f"{prefix}{i + 1:2d}. {m['message']}"
            )  # | {m['game_id']} | {m['timestamp']}")

        return self.shell.update_output_text("\n".join(lines), show_board=True)

    def next_match(self):
        if not self.match_refs:
            return
        if self.current_match_index < len(self.match_refs) - 1:
            self.current_match_index += 1
            self.current_move_index = 0

    def next_move(self):
        if not self.match_refs:
            return
        match_ref = self.get_current_match_ref()
        if self.current_move_index < len(self.matches[match_ref]["moves"]) - 1:
            self.current_move_index += 1
            self.update_view_to_current_move()

    def previous_move(self):
        logger.debug(f"next move")
        if not self.match_refs:
            return
        if self.current_move_index > 0:
            self.current_move_index -= 1
            self.update_view_to_current_move()

    def previous_match(self):
        if not self.match_refs:
            return
        if self.current_match_index > len(self.match_refs) - 1:
            self.current_match_index -= 1
            self.current_move_index = 0

    def delete_current_match(self):
        match_ref = self.get_current_match_ref()
        if match_ref in self.matches:
            del self.matches[match_ref]
            self.match_refs.remove(match_ref)
            self.current_match_index = max(0, self.current_match_index - 1)
            self.current_move_index = 0

    def save_to_file(self, path: str):
        with open(path, "w") as f:
            json.dump(
                {
                    "matches": self.matches,
                    "match_refs": self.match_refs,
                    "current_match_index": self.current_match_index,
                    "current_move_index": self.current_move_index,
                },
                f,
            )

    def load_from_file(self):
        path = self.match_history_path
        if not os.path.exists(path) or os.stat(path).st_size == 0:
            # Safeguard against empty or missing file
            self.matches = {}
            self.match_refs = []
            self.current_match_index = 0
            self.current_move_index = 0
            return

        with open(path, "r") as f:
            try:
                data = json.load(f)
                self.matches = data.get("matches", {})
                self.match_refs = data.get("match_refs", [])
                self.current_match_index = data.get("current_match_index", 0)
                self.current_move_index = data.get("current_move_index", 0)
            except json.JSONDecodeError:
                print(
                    "Warning: match_history.json is invalid JSON. Starting with empty history."
                )
                self.matches = {}
                self.match_refs = []
                self.current_match_index = 0
                self.current_move_index = 0

    def cmd_history(self, args):

        self.shell.active_module = "history"

        # Try to use current match_ref if there's an active game
        current_ref = getattr(self.shell.game, "ref", None)

        if current_ref and current_ref in self.matches:
            self.current_match_index = self.match_refs.index(current_ref)
            self.current_move_index = len(self.matches[current_ref]["moves"]) - 1
            return self.update_view_to_current_move()

        # Otherwise, activate browser from the top
        if not self.match_refs:
            return self.shell.update_output_text(
                "No match history available.", show_board=True
            )

        self.current_match_index = 0
        self.current_move_index = 0
        self.load_from_file()
        return self.shell.update_output_text(
            "History browser activated. Use up/down and left/right to navigate.",
            show_board=True,
        )

    def cmd_goto(self, args):
        if len(args) != 1 or not args[0].isdigit():
            return self.shell.update_output_text(
                "Usage: goto <move_number>", show_board=False
            )

        move_index = int(args[0]) - 1
        if (
            not self.get_current_match_ref()
            or self.get_current_match_ref() not in self.matches
        ):
            return self.shell.update_output_text(
                "No match history found.", show_board=False
            )

        if 0 <= move_index < len(self.matches[self.get_current_match_ref()]):
            self.current_move_index = move_index
            self.load_from_file()
        else:
            return self.shell.update_output_text(
                "Invalid move number.", show_board=False
            )

    def cmd_delete_history(self, args):
        self.delete_current_match()
        return self.shell.update_output_text("Deleted current match.")

    def cmd_save_history(self, args):
        self.save_to_file(f"{ASSETS_DIR}/match_history.json")
        return self.shell.update_output_text("Match history saved.")

    def handle_event(self, event):
        # Handle game events (regardless of mode)
        if event.type == EVENT_GAME:
            logger.debug(f"recording game event {event}")
            self.record_move(
                match_ref=event.dict["match_ref"],
                game_id=event.dict["game_id"],
                message=event.dict.get("message", ""),
            )
            return  # ✅ Done, exit early

        # Only handle keys if we're in history mode
        if self.shell.active_module != "history":
            return

        # Handle arrow keys
        if event.type == pygame.KEYDOWN:
            logger.debug(f"HISTORY KEY: {event.key}")
            if event.key == pygame.K_UP:
                self.previous_move()
            elif event.key == pygame.K_DOWN:
                self.next_move()
            elif event.key == pygame.K_LEFT:
                self.previous_match()
            elif event.key == pygame.K_RIGHT:
                self.next_match()

    def register(self):
        return (
            {
                "history": self.cmd_history,
                "goto": self.cmd_goto,
                "delete_history": self.cmd_delete_history,
                "save_history": self.cmd_save_history,
            },
            {},
            {
                "history": "Show all recorded moves in the current match",
                "goto": "Jump to the nth move in the current match",
                "delete_history": "Delete the current match history",
                "save_history": "Save match history to file",
            },
        )


def register(shell):
    mod = HistoryManager(shell)
    shell.history_module = mod  # 👈 make it accessible to other modules/shell
    return mod
