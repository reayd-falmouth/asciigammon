import json
import os
import pygame
from copy import deepcopy
from datetime import datetime
from typing import List, Dict, TypedDict

from pybg.agents.factory import create_agent
from pybg.constants import ASSETS_DIR
from pybg.core.board import Board
from pybg.core.events import EVENT_GAME
from pybg.core.player import PlayerType
from pybg.modules.base_module import BaseModule
from pybg.variants import Backgammon, Nackgammon, AceyDeucey, Hypergammon


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
        self.original_game = None

    def record_move(self, match_ref: str, game_id: str, message: str = ""):
        now = datetime.now().isoformat()

        if match_ref not in self.matches:
            self.matches[match_ref] = {
                "created": now,
                "moves": [],
                "settings": deepcopy(self.shell.settings),  # ✅ Save settings snapshot
            }
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

    def update_view_to_current_move(self):
        match_ref = self.get_current_match_ref()
        if match_ref not in self.matches:
            return

        move = self.matches[match_ref]["moves"][self.current_move_index]
        pos_id, match_id = move["game_id"].split(":")

        if self.shell.game is None or not isinstance(self.shell.game, Board):
            self.shell.game = Board()

        self.shell.game.position = self.shell.game.position.decode(pos_id)
        self.shell.game.match = self.shell.game.match.decode(match_id)
        self.shell.game.ref = match_ref

        # Build move log
        moves = self.matches[match_ref]["moves"]
        created_at = self.matches[match_ref]["created"]
        lines = [
            f"LOG for Match {match_ref[:8]} (Moves: {len(moves)}):\n Started: {created_at}\n"
        ]
        for i, m in enumerate(moves):
            prefix = "> " if i == self.current_move_index else "  "
            lines.append(f"{prefix}{i + 1:2d}. {m['message']}")

        return self.shell.update_output_text("\n".join(lines), show_board=True)

    def next_move(self):
        if not self.match_refs:
            return
        match_ref = self.get_current_match_ref()
        if self.current_move_index < len(self.matches[match_ref]["moves"]) - 1:
            self.current_move_index += 1
            self.update_view_to_current_move()

    def previous_move(self):
        if not self.match_refs:
            return
        if self.current_move_index > 0:
            self.current_move_index -= 1
            self.update_view_to_current_move()

    def next_match(self):
        if not self.match_refs:
            return
        if self.current_match_index < len(self.match_refs) - 1:
            self.current_match_index += 1
            self.current_move_index = 0
            self.shell.game = None  # reset the game object to recreate the new one
            self.update_view_to_current_move()  # <- update board view

    def previous_match(self):
        if not self.match_refs:
            return
        if self.current_match_index > 0:
            self.current_match_index -= 1
            self.current_move_index = 0
            self.shell.game = None  # reset the game object to recreate the new one
            self.update_view_to_current_move()  # <- update board view

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

        if self.shell.game:
            self.original_game = deepcopy(self.shell.game)

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
        self.current_move_index = 0
        self.shell.game = None  # reset the game object to recreate the new one
        return self.update_view_to_current_move()

    def cmd_save_history(self, args):
        self.save_to_file(f"{ASSETS_DIR}/match_history.json")
        return self.shell.update_output_text("Match history saved.")

    def cmd_delete(self, args):
        if self.shell.active_module != "history":
            return self.shell.update_output_text(
                "The 'delete' command only works in history mode.", show_board=False
            )

        match_id = self.get_current_match_ref()
        if not match_id:
            return self.shell.update_output_text(
                "No match selected to delete.", show_board=False
            )

        self.delete_current_match()
        self.save_to_file(self.match_history_path)
        return self.shell.update_output_text(
            f"Deleted current match {match_id[:8]}.", show_board=True
        )

    def handle_event(self, event):
        # Handle game events (regardless of mode)
        if event.type == EVENT_GAME:
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
            if event.key == pygame.K_UP:
                self.previous_move()
            elif event.key == pygame.K_DOWN:
                self.next_move()
            elif event.key == pygame.K_LEFT:
                self.previous_match()
            elif event.key == pygame.K_RIGHT:
                self.next_match()
            elif event.key == pygame.K_ESCAPE:
                return self.exit_history_mode()

    def exit_history_mode(self):
        if self.original_game:
            self.shell.game = deepcopy(self.original_game)
        self.shell.active_module = None
        self.original_game = None
        return self.shell.update_output_text(show_board=True)

    def cmd_exit(self, args):
        self.exit_history_mode()

    def cmd_play(self, args):
        match_ref = self.get_current_match_ref()
        if not match_ref or match_ref not in self.matches:
            return self.shell.update_output_text("No match loaded.", show_board=True)

        # Trim future moves
        current = self.current_move_index
        if current < len(self.matches[match_ref]["moves"]) - 1:
            self.matches[match_ref]["moves"] = self.matches[match_ref]["moves"][
                : current + 1
            ]
            self.save_to_file(self.match_history_path)

        # Restore settings
        settings = self.matches[match_ref].get("settings", self.shell.settings)

        game_class = {
            "backgammon": Backgammon,
            "nackgammon": Nackgammon,
            "acey-deucey": AceyDeucey,
            "hypergammon": Hypergammon,
        }.get(settings["variant"], Backgammon)

        self.shell.game = game_class()
        self.shell.game.match.length = (
            settings["match_length"] if settings["game_mode"] == "match" else 0
        )
        self.shell.game.auto_doubles = bool(settings.get("autodoubles", False))
        self.shell.game.jacoby = bool(settings.get("jacoby", False))

        # Load the board state from history
        move = self.matches[match_ref]["moves"][current]
        pos_id, match_id = move["game_id"].split(":")
        self.shell.game.position = self.shell.game.position.decode(pos_id)
        self.shell.game.match = self.shell.game.match.decode(match_id)
        self.shell.game.ref = match_ref

        # Recreate agents
        self.shell.player0_agent = create_agent(
            settings["player_agent"], PlayerType.ZERO, self.shell.game
        )
        self.shell.player1_agent = create_agent(
            settings["opponent_agent"], PlayerType.ONE, self.shell.game
        )

        self.shell.active_module = "game"

        return self.shell.update_output_text(
            "Resumed play from history.", show_board=True
        )

    def cmd_clear(self, args):
        confirm = args[0] if args else None
        if confirm != "yes":
            return self.shell.update_output_text(
                "This will delete all history. Type `clear yes` to confirm.",
                show_board=False,
            )

        self.matches.clear()
        self.match_refs.clear()
        self.current_match_index = 0
        self.current_move_index = 0
        self.save_to_file(self.match_history_path)
        return self.shell.update_output_text("All history cleared.", show_board=False)

    def cmd_export(self, args):
        import csv
        import tkinter as tk
        from tkinter import filedialog

        # Use Tkinter's file dialog in a hidden root window
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes("-topmost", 1)  # Bring dialog to front

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Export Match History As",
            initialdir=os.getcwd(),
            initialfile="match_history_export.csv",
        )

        if not file_path:
            return self.shell.update_output_text("Export cancelled.", show_board=False)

        try:
            with open(file_path, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["match_id", "timestamp", "game_id", "message"])
                for match_id, data in self.matches.items():
                    for move in data["moves"]:
                        writer.writerow(
                            [
                                match_id,
                                move["timestamp"],
                                move["game_id"],
                                move["message"],
                            ]
                        )
            return self.shell.update_output_text(
                f"Exported history to {file_path}", show_board=False
            )
        except Exception as e:
            return self.shell.update_output_text(
                f"Export failed: {e}", show_board=False
            )

    def register(self):
        return (
            {
                "history": self.cmd_history,
                "delete": self.cmd_delete,
                "play": self.cmd_play,
                "clear": self.cmd_clear,
                "export": self.cmd_export,
            },
            {},
            {
                "history": "Show all recorded moves in the current match",
                "delete": "Delete the current match (only in history mode)",
                "play": "Starts a game at current match and position, (erases history from this point)",
                "clear": "Resets all the history. Type `clear yes` to confirm.",
                "export": "Exports the history to a CSV file",
            },
        )


def register(shell):
    mod = HistoryManager(shell)
    shell.history_module = mod  # 👈 make it accessible to other modules/shell
    return mod
