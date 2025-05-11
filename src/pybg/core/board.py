import time

import enum
import gymnasium as gym
import json
import numpy as np
import random
from copy import deepcopy
from gymnasium import spaces
from typing import Any, TypeVar
from typing import List, NamedTuple, Optional, Tuple
from uuid import uuid4

from pybg.core.events import post_game_event
from pybg.core.logger import logger
from pybg.core.player import Player, PlayerType
from pybg.gnubg.match import GameState, Match, Resign
from pybg.gnubg.position import Position

ObsType = TypeVar("ObsType")


POINTS = 24
POINTS_PER_QUADRANT = int(POINTS / 4)
CHECKERS = 15

ASCII_BOARD_HEIGHT = 11
ASCII_MAX_CHECKERS = 5
ASCII_13_24 = "+13-14-15-16-17-18------19-20-21-22-23-24-+"
ASCII_12_01 = "+12-11-10--9--8--7-------6--5--4--3--2--1-+"

STARTING_MATCH_ID = "MAAAAAAAAAAA"

# Backgammon board settings
BACKGAMMON_STARTING_POSITION_ID = "4HPwATDgc/ABMA"
BACKGAMMON_STARTING_MATCH_ID = "cAgAAAAAAAAA"

# Nackgammon board settings
NACKGAMMON_STARTING_POSITION_ID = "4Dl4ADbgOXgANg"
NACKGAMMON_STARTING_MATCH_ID = "cAgAAAAAAAAA"

# AceyDeucy board settings
ACEYDEUCY_STARTING_POSITION_ID = "AAAA/38AAAD/fw"
ACEYDEUCY_STARTING_MATCH_ID = "cAgAAAAAAAAA"


class BoardError(Exception):
    pass


class MoveState(enum.Enum):
    BEAR_OFF = enum.auto()
    ENTER_FROM_BAR = enum.auto()
    DEFAULT = enum.auto()


class Move(NamedTuple):
    pips: int
    source: Optional[int]
    destination: Optional[int]


class Play(NamedTuple):
    moves: Tuple[Move, ...]
    position: Position


# gym.Env
class Board(gym.Env):
    checkers: int = CHECKERS
    player: Player = Player.ZERO
    player0: Player = Player.ZERO
    player1: Player = Player.ONE

    def __init__(
        self,
        position_id: str = BACKGAMMON_STARTING_POSITION_ID,
        match_id: str = STARTING_MATCH_ID,
        bet: int = 0,
        auto_doubles: bool = False,
        beavers: bool = False,
        jacoby: bool = False,
        cont: bool = False,
        ref: Optional[str] = None,  # ✅ NEW
    ):
        self.ref = ref if ref is not None else str(uuid4())  # ✅ FIX
        self.position: Position = Position.decode(position_id)
        self.match: Match = Match.decode(match_id)
        self.starting_position_id: str = position_id
        self.bet = bet
        self.auto_doubles = auto_doubles
        self.beavers = beavers
        self.jacoby = jacoby

        # Reinforcement learning
        lower_bound = np.array(
            [
                1,
            ]
            * 2
            + [
                0,
            ]
            * 52
        )
        upper_bound = np.array(
            [
                6,
            ]
            * 2
            + [
                15,
            ]
            * 4
            + [
                item
                for sublist in [
                    [2, 15],
                ]
                * 24
                for item in sublist
            ]
        )
        self.observation_space = spaces.Box(
            low=lower_bound,
            high=upper_bound,
            dtype=np.float32,
        )
        self.actions = self.all_actions()
        self.action_count = len(self.actions)
        if cont:
            self.action_space = spaces.Box(
                low=np.array([-int((self.action_count / 2) - 1)]),
                high=np.array([int((self.action_count / 2) - 1)]),
                dtype=np.float32,
            )
        else:
            self.action_space = spaces.Discrete(self.action_count)

        # Debug info.
        self.invalid_actions_taken = 0
        self.time_elapsed = 0

    def generate_plays(self, partial: bool = False) -> List[Play]:
        """
        Generate and return legal plays.

        If `partial` is True, return all partial plays too (not just max-length).
        """

        def generate(
            position: Position,
            dice: Tuple[int, ...],
            die: int = 0,
            moves: Tuple[Move, ...] = (),
            plays: List[Play] = [],
        ) -> List[Play]:
            if die < len(dice):
                pips = dice[die]

                if position.player_bar > 0:
                    new_position, destination = position.enter(pips)
                    if new_position:
                        generate(
                            new_position,
                            dice,
                            die + 1,
                            moves + (Move(pips, -1, destination),),
                            plays,
                        )
                elif sum(position.player_home()) + position.player_off == self.checkers:
                    for point in range(POINTS_PER_QUADRANT):
                        new_position, destination = position.off(point, pips)
                        if new_position:
                            generate(
                                new_position,
                                dice,
                                die + 1,
                                moves + (Move(pips, point, destination),),
                                plays,
                            )
                else:
                    for point in range(len(position.board_points)):
                        new_position, destination = position.move(point, pips)
                        if new_position:
                            generate(
                                new_position,
                                dice,
                                die + 1,
                                moves + (Move(pips, point, destination),),
                                plays,
                            )

            plays.append(Play(moves, position))
            return plays

        if not any(d > 0 for d in self.match.dice):
            return []

        doubles = self.match.dice[0] == self.match.dice[1]
        dice = self.match.dice * 2 if doubles else self.match.dice

        plays = generate(self.position, dice)
        if not doubles:
            plays += generate(self.position, dice[::-1])

        if not partial and len(plays) > 0:
            max_moves = max(len(p.moves) for p in plays)
            plays = [p for p in plays if len(p.moves) == max_moves]

        # Deduplicate by final position
        seen = set()
        unique_plays = []
        for play in sorted(plays, key=lambda p: hash(p.position)):
            h = hash(play.position)
            if h not in seen:
                seen.add(h)
                unique_plays.append(play)

        return unique_plays

    def start(self, length: int = 3) -> None:
        """
        Starts the match, optionally includes an integer value to determine the length.

        """
        # First roll is done automatically.
        self.first_roll()

        post_game_event(
            "first_roll",
            match_ref=self.ref,
            game_id=self.encode(),
            message=f"player{self.match.turn} wins first roll, with {self.match.dice}",
        )

        # Diced rolled so game state is set to rolled.
        self.match.game_state = GameState.ROLLED

    def roll(self) -> Tuple[int, int]:
        """

        Returns:

        """
        if self.match.dice != (0, 0):
            raise BoardError(f"Dice have already been rolled: {self.match.dice}")

        self.match.dice = (
            random.SystemRandom().randrange(1, 6),
            random.SystemRandom().randrange(1, 6),
        )

        self.match.game_state = GameState.ROLLED

        post_game_event(
            "roll",
            match_ref=self.ref,
            game_id=self.encode(),
            message=f"player{self.match.turn} rolls {self.match.dice}",
        )

        return self.match.dice

    def first_roll(self) -> Tuple[int, int]:
        """

        Returns:

        """
        while True:
            self.match.dice = (
                random.SystemRandom().randrange(1, 6),
                random.SystemRandom().randrange(1, 6),
            )
            if self.match.dice[0] != self.match.dice[1]:
                break

        if self.match.dice[0] > self.match.dice[1]:
            self.match.player = Player.ZERO
            self.match.turn = Player.ZERO
        else:
            self.match.player = Player.ONE
            self.match.turn = Player.ONE

        self.match.game_state = GameState.ROLLED

        return self.match.dice

    def play(self, moves: Tuple[Tuple[Optional[int], Optional[int]], ...]) -> None:
        """
        Execute a partial or full play.

        Args:
            moves: sequence of (source, destination) tuples.

        Raises:
            BoardError: if the partial play is invalid.
        """
        legal_plays = self.generate_plays(partial=True)

        if not legal_plays:
            post_game_event(
                "move",
                match_ref=self.ref,
                game_id=self.encode(),
                message=f"player{self.match.turn} has no legal moves from dice {self.match.dice}",
            )
            self.end_turn()
            return

        # Convert to Move objects to compare
        def to_moves(seq):
            return tuple(
                Move(abs(s - d) if s is not None and d is not None else 0, s, d)
                for s, d in seq
            )

        requested_moves = to_moves(moves)

        # Filter for any legal play that starts with this sequence
        matching_play = next(
            (
                play
                for play in legal_plays
                if play.moves[: len(requested_moves)] == requested_moves
            ),
            None,
        )

        if matching_play:
            # Apply each move in order to reach that intermediate position
            new_position = self.position
            for s, d in moves:
                new_position = new_position.apply_move(s, d)
            self.position = new_position

            # End the turn if it's a complete match
            if len(requested_moves) == len(matching_play.moves):
                if self.position.player_off == self.checkers:
                    self.match.game_state = GameState.GAME_OVER
                formatted_moves = " ".join(
                    f"{'bar' if m.source == -1 else m.source + 1}/{'off' if m.destination == -1 else m.destination + 1}"
                    for m in matching_play.moves
                )
                message = f"player{self.match.turn} moved {formatted_moves}"
                post_game_event(
                    "move", match_ref=self.ref, game_id=self.encode(), message=message
                )
                self.end_turn()
        else:
            raise BoardError(
                f"Invalid move sequence: {moves}, legal moves {legal_plays}"
            )

    def double(self) -> None:
        if (
            self.match.player == self.match.turn
            and self.match.game_state == GameState.ON_ROLL
            and (
                self.match.cube_holder == self.match.player
                or self.match.cube_holder == Player.CENTERED
            )
        ):
            self.match.cube_value *= 2
            self.match.double = True
            self.match.game_state = GameState.DOUBLED
            post_game_event(
                "double",
                match_ref=self.ref,
                game_id=self.encode(),
                message=f"player{self.match.turn} doubles to {self.match.cube_value}",
            )
            self.match.swap_turn()
        else:
            logger.debug("Double failed validation")
            if self.match.cube_holder != self.match.player:
                raise BoardError("You cannot double until you hold the cube.")
            else:
                raise BoardError("You cannot double right now.")

    def redouble(self) -> None:
        """
        Redoubles a double (called a beaver), only available on money sessions.

        Returns:
            None
        """
        if (
            self.match.turn != self.match.cube_holder
            and self.match.game_state == GameState.DOUBLED
        ):
            self.match.cube_value = self.match.cube_value * 2
            self.take()
            post_game_event(
                "redouble",
                match_ref=self.ref,
                game_id=self.encode(),
                message=f"player{self.match.turn} redoubles to {self.match.cube_value}",
            )
        else:
            raise BoardError("Cannot redouble: it's not your turn")

    def drop(self) -> None:
        """
        Drops a double.

        Returns:
            None
        """
        if (
            self.match.turn != self.match.cube_holder
            and self.match.game_state == GameState.DOUBLED
        ):
            post_game_event(
                "drop",
                match_ref=self.ref,
                game_id=self.encode(),
                message=f"player{self.match.turn} drops the cube at value {self.match.cube_value}",
            )
            self.update_score(
                int(self.match.cube_value / 2),
                int(Resign.SINGLE_GAME),
                int(self.match.player),
            )
            self.end_game()
        else:
            raise BoardError("No double to drop")

    def accept(self) -> None:
        """
        Accepts a resignation.

        Returns:
            None
        """
        if (
            self.match.player == self.match.turn
            and self.match.game_state == GameState.RESIGNED
        ):
            post_game_event(
                "accept",
                match_ref=self.ref,
                game_id=self.encode(),
                message=f"player{self.match.turn} accepts the cube at value {self.match.cube_value}",
            )
            self.update_score(
                int(self.match.cube_value),
                int(self.match.resign),
                self.match.player,
            )
            self.end_game()
        else:
            raise BoardError("No resignation to accept")

    def reject(self) -> None:
        """
        Rejects an offered resignation.

        Returns:
            None
        """
        if (
            self.match.player == self.match.turn
            and self.match.game_state == GameState.RESIGNED
        ):
            self.position = self.position.swap_players()
            self.match.swap_players()
            self.match.game_state = GameState.REJECTED
            post_game_event(
                "reject",
                match_ref=self.ref,
                game_id=self.encode(),
                message=f"player{self.match.turn} rejects {self.match.resign}",
            )
        else:
            raise BoardError("No resignation to reject")

    def take(self) -> None:
        logger.debug(
            f"Taking - player: {self.match.player}, turn: {self.match.turn}, cube_holder: {self.match.cube_holder}"
        )
        if (
            self.match.turn != self.match.cube_holder
            and self.match.game_state == GameState.DOUBLED
        ):

            self.match.cube_holder = self.match.turn
            self.match.reset_dice()
            self.match.game_state = GameState.ON_ROLL
            logger.debug(
                f"Double accepted - new turn: {self.match.turn}, cube_holder: {self.match.cube_holder}"
            )
            post_game_event(
                "take",
                match_ref=self.ref,
                game_id=self.encode(),
                message=f"player{self.match.turn} takes the cube at {self.match.cube_value}",
            )
            self.match.swap_turn()

        else:
            raise BoardError("No double to take")

    def end_turn(self) -> None:
        """
        Ends a turn.
        """
        if self.match.game_state == GameState.GAME_OVER:
            self.update_score(
                self.match.cube_value,
                self.multiplier(),
                self.match.player,
            )
            self.end_game()
        else:
            self.position = self.position.swap_players()
            self.match.swap_players()
            self.match.reset_dice()
            self.match.game_state = GameState.ON_ROLL

    def resign(self, resign: Resign) -> None:
        """
        Resigns the game based on a resignation/multiplier.

        Returns:
            None
        """
        if resign is not None:
            self.match.resign = resign
            self.match.game_state = GameState.RESIGNED
            post_game_event(
                "resign",
                match_ref=self.ref,
                game_id=self.encode(),
                message=f"player{self.match.turn} resigns a {self.match.resign}",
            )
            self.position = self.position.swap_players()
            self.match.swap_players()
        else:
            raise BoardError(
                "You must specify resignation: single, gammon or backgammon..."
            )

    def end_game(self) -> None:
        """
        Test to see if the game is finished.

        Returns:
            None
        """
        if self.match.player_0_score >= self.match.length:
            self.match.game_state = GameState.GAME_OVER
            post_game_event(
                "end_game",
                match_ref=self.ref,
                game_id=self.encode(),
                message=f"player{self.match.player} wins with {self.match.player_0_score} points",
            )
        elif self.match.player_1_score >= self.match.length:
            self.match.game_state = GameState.GAME_OVER
            post_game_event(
                "end_game",
                match_ref=self.ref,
                game_id=self.encode(),
                message=f"player{self.match.player} wins with {self.match.player_1_score} points",
            )
        else:
            self.reset()

    def update_score(self, cube: int, multiplier: int, winner: int) -> None:
        """
        Updates the match score.

        Returns:
            None
        """
        score = self.calculate_score(cube, multiplier)

        if winner == 0:
            self.match.player_0_score += score
        else:
            self.match.player_1_score += score

    def multiplier(self) -> Resign:
        """
        Calculates the multiplier based on the board position.
        """
        # If all the players checkers are off then the
        # game is over and a multiplier may be awarded.
        if self.position.player_off == self.checkers:
            # If the opponent has borne off a checker then it's a single game.
            if self.position.opponent_off > 0:
                multiplier = Resign.SINGLE_GAME
            # Otherwise if 0 checkers are borne off and there is one left
            # in the home board it's a backgammon (opponent is negative).
            elif (
                sum(self.position.opponent_home()) < 0 or self.position.opponent_bar > 0
            ):
                multiplier = Resign.BACKGAMMON
            # All other cases are a gammon.
            else:
                multiplier = Resign.GAMMON
            return multiplier
        # If the player has not borne off ALL checkers then it's a resignation
        # and requires the player to concede a multiplier.
        else:
            raise BoardError(
                "Checkers are still on the board, what do you resign, single, gammon or backgammon?"
            )

    @staticmethod
    def calculate_score(cube: int, multiplier: int) -> int:
        """

        Args:
            cube:
            multiplier:

        Returns:
            int
        """
        return int(cube) * int(multiplier)

    def to_json(self) -> str:
        """

        Returns:

        """
        return json.dumps(
            {
                "position": self.position.__dict__,
                "match": self.match.__dict__,
            }
        )

    def encode(self) -> str:
        """

        Returns:

        """
        return f"{self.position.encode()}:{self.match.encode()}"

    def is_player_home(self) -> bool:
        """
        Calculates whether a players checkers are in the home board.

        """
        # The players home board can be found by slicing the board by the quadrant size i.e. the first 6 points.
        home_board: Tuple[int, ...] = self.position.board_points[:POINTS_PER_QUADRANT]

        # Then return a tuple with all the players, but not the opponents points.
        total_checkers = (
            sum(tuple(point if point > 0 else 0 for point in home_board))
            + self.position.player_off
        )

        if total_checkers == 15:
            return True

        return False

    def is_opponent_home(self) -> bool:
        """
        Calculates whether an opponents checkers are in their home board.

        """
        # The opponent home board can be found by slicing the board by the quadrant size i.e. the last 6 points.
        home_board: Tuple[int, ...] = self.position.board_points[
            POINTS - POINTS_PER_QUADRANT :
        ]

        # Then return a tuple with all the players, but not the opponents points.
        total_checkers = (
            abs(sum(tuple(point if point < 0 else 0 for point in home_board)))
            + self.position.opponent_off
        )

        if total_checkers == 15:
            return True

        return False

    @staticmethod
    def all_actions() -> List[Tuple[str, int, int]]:
        actions = []
        sources = list(range(0, 24))
        targets = list(range(0, 24))
        homes = list(range(0, 6))

        # 'move's and 'hit's
        for i in sources:
            for j in targets:
                if 6 >= (j - i) > 0:
                    actions.append(("move", j, i))

        # bar and off
        for j in homes:
            actions.append(("move", "bar", j))
            actions.append(("move", j, "off"))

        # Resign actions
        for r in ["single", "gammon", "backgammon"]:
            actions.append(("accept", r))
            actions.append(("reject", r))
            actions.append(("resign", r))

        # Roll, or double actions
        actions.append("roll")
        actions.append("double")
        actions.append("take")
        actions.append("drop")
        actions.append("redouble")

        return actions

    def valid_actions(self) -> List[Tuple[str, int, int]]:
        """
        Returns:
            list: A list of all valid actions (tuples), no reward shaping applied.
        """
        actions = []

        # A player is always allowed to resign at any time
        for r in ["single", "gammon", "backgammon"]:
            actions.append(("resign", r))
            if self.match.game_state == GameState.RESIGNED:
                actions.append(("accept", r))
                actions.append(("reject", r))

        # If the Game state is on roll then they may roll the dice
        if self.match.game_state == GameState.ON_ROLL:
            actions.append("roll")

            # ...if they own the cube, or it is centered they can double.
            if (
                self.match.cube_holder == self.match.turn
                or self.match.cube_holder == PlayerType.CENTERED
            ):
                actions.append("double")

        # If a cube has been offered, they can take, drop or redouble (know as beaver)
        if self.match.game_state == GameState.DOUBLED:
            actions.append("take")
            actions.append("drop")
            actions.append("redouble")
            return actions  # ✅ ADD THIS EARLY RETURN

        # Check for the legal moves and append these to the actions.
        legal_plays: List[Play] = self.generate_plays()

        seen_moves = set()
        for play in legal_plays:
            for move in play.moves:
                action = ("move", move.source, move.destination)
                if action not in seen_moves:
                    seen_moves.add(action)
                    actions.append(action)

        return actions

    def action_mask(self):
        """
        Returns a boolean array of length len(ALL_ACTIONS),
        where each True means the action is currently legal.
        """
        legal_action_mask = np.zeros(self.action_count, dtype=bool)

        for action in self.valid_actions():
            try:
                idx = self.actions.index(action)
                legal_action_mask[idx] = True
            except ValueError:
                pass

        return legal_action_mask

    def get_observation(self):
        match = self.match
        position = self.position

        obs = []

        # Dice
        obs.append(match.dice[0] if len(match.dice) > 0 else 0)
        obs.append(match.dice[1] if len(match.dice) > 1 else 0)

        # Hits and bear offs
        obs.append(position.opponent_bar)  # white bar
        obs.append(position.player_bar)  # black bar
        obs.append(position.opponent_off)  # white borne off
        obs.append(position.player_off)  # black borne off

        # Points: loop over 24 points
        for p in position.board_points:
            if p > 0:
                obs.append(1)  # black
                obs.append(p)
            elif p < 0:
                obs.append(2)  # white
                obs.append(abs(p))
            else:
                obs.append(0)
                obs.append(0)

        if not isinstance(obs, np.ndarray):
            obs = np.array(obs)
        obs = obs.reshape(1, -1)

        return obs

    def render(self, mode="human"):
        """Renders the board. 'w' is player1 and 'b' is player2."""
        if mode == "human":
            print(str(self))

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[ObsType, dict[str, Any]]:
        """Restarts the game."""

        self.position = Position.decode(self.starting_position_id)
        self.first_roll()
        self.match.game_state = GameState.ROLLED
        self.match.cube_value = 1
        self.match.cube_holder = PlayerType.CENTERED
        self.match.double = False

        return np.array(self.get_observation(), dtype=np.float32), {}

    def step(self, action_index):
        """
        Executes the player's action, then gives the opponent their turn
        if the game is not over.
        """
        # 🎯 Convert from Box space to Discrete index if needed
        if isinstance(self.action_space, spaces.Box):
            action_index += int(self.action_count / 2)
            action_index = int(action_index)

        # 🧠 Convert index to action tuple/string
        action = self.actions[action_index]

        # ⚙️ Apply the player's action
        reward = self.apply_action(action)

        # 🛑 If the move was illegal, do NOT proceed to opponent turn
        if reward < 0:
            return self.get_observation(), reward, False, False, self.get_info()

        # 🏁 Check if game is over after player's move
        done = self.match.game_state == GameState.GAME_OVER
        if done:
            return self.get_observation(), reward, True, False, self.get_info()

        # 🔁 Switch to opponent
        self.end_turn()

        # 🎯 Opponent picks an action *appropriate to the game state*
        opponent_action_index = self.opponent.make_decision(
            self.get_observation(), self.action_mask()
        )

        if isinstance(self.action_space, spaces.Box):
            opponent_action_index += int(self.action_count / 2)
            opponent_action_index = int(opponent_action_index)

        opponent_action = self.actions[opponent_action_index]

        # 🧠 Apply opponent's chosen action
        self.apply_action(opponent_action)

        # 🔚 Check again if the game has ended after opponent's move
        done = self.match.game_state == GameState.GAME_OVER

        return self.get_observation(), reward, done, False, self.get_info()

    def apply_action(self, action):
        """
        Given a valid action tuple, applies it to the board.
        Returns a reward (default: 0, or -10 for invalid moves).
        """
        try:
            if isinstance(action, tuple):
                if action[0] == "move":
                    logger.debug(f"action move tuple {action}")
                    self.play(((action[1], action[2]),))
                elif action[0] == "resign":
                    self.resign(Resign[action[1].upper()])
                elif action[0] == "accept":
                    self.accept()
                elif action[0] == "reject":
                    self.reject()
                else:
                    raise BoardError(f"Unknown action: {action}")
            elif isinstance(action, str):
                if action == "roll":
                    self.roll()
                elif action == "double":
                    self.double()
                elif action == "take":
                    self.take()
                elif action == "drop":
                    self.drop()
                elif action == "redouble":
                    self.redouble()
                elif action == "pass":
                    self.end_turn()
                else:
                    raise BoardError(f"Unknown string action: {action}")
            return 0  # No shaped reward by default
        except BoardError as e:
            logger.warning(f"Invalid action attempted: {action} | {e}")
            self.invalid_actions_taken += 1
            return -10

    def get_info(self):
        """Returns useful info for debugging, etc."""

        return {
            "time elapsed": time.time() - self.time_elapsed,
            "invalid actions taken": self.invalid_actions_taken,
        }

    def __repr__(self):
        """

        Returns:

        """
        position_id: str = self.position.encode()
        match_id: str = self.match.encode()
        checkers: int = self.checkers
        return f"{__name__}.{self.__class__.__name__}('{position_id}', '{match_id}', {checkers})"

    def __str__(self):
        """

        Returns:

        """

        def checkers(top: List[int], bottom: List[int]) -> List[List[str]]:
            """Return an ASCII checker matrix."""
            ascii_checkers: List[List[str]] = [
                ["   " for j in range(len(top))] for i in range(ASCII_BOARD_HEIGHT)
            ]

            for half in (top, bottom):
                for col, num_checkers in enumerate(half):
                    row: int = 0 if half is top else len(ascii_checkers) - 1
                    for i in range(abs(num_checkers)):
                        if (
                            abs(num_checkers) > ASCII_MAX_CHECKERS
                            and i == ASCII_MAX_CHECKERS - 1
                        ):
                            ascii_checkers[row][col] = f" {abs(num_checkers)} "
                            break
                        ascii_checkers[row][col] = " O " if num_checkers > 0 else " X "
                        row += 1 if half is top else -1

            return ascii_checkers

        def split(position: List[int]) -> Tuple[List[int], List[int]]:
            """Return a position split into top (Player.ZERO 12-1) and bottom (Player.ZERO 13-24) halves."""

            def normalize(position: List[int]) -> List[int]:
                """Return position for PlayerType.ZERO"""
                if self.match.player is PlayerType.ONE:
                    position = list(map(lambda n: -n, position[::-1]))
                return position

            position = normalize(position)

            half_len: int = int(len(position) / 2)
            top: List[int] = position[:half_len][::-1]
            bottom: List[int] = position[half_len:]

            return top, bottom

        def set_match_text(match: Match, i: int) -> str:
            """

            Args:
                match:

            Returns:

            """
            spacer = "     "
            match_text = (
                f"{match.length} point match"
                if match.length > 0
                else f"${self.bet * self.match.cube_value} money game"
            )
            cube_text = (
                f" (Cube: {self.match.cube_value})"
                if i == int(ASCII_BOARD_HEIGHT / 2) and match.cube_value == 1
                else ""
            )

            return f"{spacer}{match_text}{cube_text}"

        def set_game_status(match: Match) -> str:
            """

            Args:
                match:

            Returns:

            """
            spacer = "     "

            if match.game_state == GameState.ON_ROLL:
                message = "On roll"
            elif match.game_state == GameState.ROLLED:
                message = f"Rolled {match.dice}"
            elif match.game_state == GameState.DOUBLED:
                message = f"Cube offered at {match.cube_value}"
            elif match.game_state == GameState.RESIGNED:
                message = f"Opponent resigns a {match.resign.phrase}"
            else:
                message = ""

            return f"{spacer}{message}"

        def set_player_text(game: Board) -> tuple:
            """

            Args:
                game:

            Returns:

            """

            def update_cube_text(match: Match, player: PlayerType) -> str:
                if (
                    player == match.cube_holder
                    and match.game_state != GameState.DOUBLED
                ):
                    return f" (Cube: {match.cube_value})"
                return ""

            spacer = "     "

            if game.player == game.player0:
                top = f"{spacer}{game.player1.checker}: {game.player1.nickname}{update_cube_text(game.match, Player.ONE)}"
                bottom = f"{spacer}{game.player0.checker}: {game.player0.nickname}{update_cube_text(game.match, Player.ZERO)}"
            else:
                top = f"{spacer}{game.player0.checker}: {game.player0.nickname}{update_cube_text(game.match, Player.ZERO)}"
                bottom = f"{spacer}{game.player1.checker}: {game.player1.nickname}{update_cube_text(game.match, Player.ONE)}"

            return top, bottom

        def set_player_score(game: Board) -> tuple:
            """

            Args:
                game:

            Returns:

            """
            spacer = "     "

            if game.player == game.player0:
                top = f"{spacer}{game.match.player_1_score} points"
                bottom = f"{spacer}{game.match.player_0_score} points"
            else:
                top = f"{spacer}{game.match.player_0_score} points"
                bottom = f"{spacer}{game.match.player_1_score} points"

            return top, bottom

        def set_player_pip_count() -> tuple:
            """

            Args:
                game:

            Returns:

            """
            spacer = "     "

            # Normalize according to player's perspective
            if self.match.player == PlayerType.ONE:
                position = deepcopy(self.position.swap_players())
            else:
                position = deepcopy(self.position)

            player_pips, opponent_pips = position.pip_count()

            top = f"{spacer}pips: {opponent_pips}"
            bottom = f"{spacer}pips: {player_pips}"

            # if position.player_home() and position.opponent_home():
            #     player_enr, opponent_enr = self.bearoff_stats()
            #
            #     top += f", rolls: {opponent_enr}" if opponent_enr is not None else ""
            #     bottom += f", rolls: {player_enr}" if player_enr is not None else ""

            return top, bottom

        points: List[List[str]] = checkers(*split(list(self.position.board_points)))

        bar: List[List[str]] = checkers(
            *split(
                [
                    self.position.player_bar,
                    -self.position.opponent_bar,
                ]
            )
        )

        # We always want the board to be normalized so that the home is bottom right
        points.reverse() if self.player == self.player0 else None

        message: str = set_game_status(self.match)

        player_text_top, player_text_bottom = set_player_text(self)
        player_score_top, player_score_bottom = set_player_score(self)
        player_pip_count_top, player_pip_count_bottom = set_player_pip_count()

        ascii_board: str = ""
        position_id: str = self.position.encode()
        # Max length for variant name to align nicely with position ID
        max_name_len = 15
        name = getattr(self, "variant_name", self.__class__.__name__)
        name = name[:max_name_len].ljust(max_name_len)
        ascii_board += f" {name} Position ID: {position_id}\n"
        match_id: str = self.match.encode()
        match_ref = self.ref
        match_ref = match_ref[:max_name_len].ljust(max_name_len)
        ascii_board += f" {match_ref} Match ID   : {match_id}\n"

        # Top Player display
        ascii_board += " "
        ascii_board += (
            ASCII_12_01 if int(self.match.turn) != int(self.player) else ASCII_13_24
        )
        ascii_board += player_text_top
        ascii_board += "\n"

        for i in range(len(points)):
            ascii_board += (
                ("^|" if int(self.match.turn) != int(self.player) else "v|")
                if i == int(ASCII_BOARD_HEIGHT / 2)
                else " |"
            )
            ascii_board += "".join(points[i][:POINTS_PER_QUADRANT])
            ascii_board += "|"
            ascii_board += "BAR" if i == int(ASCII_BOARD_HEIGHT / 2) else bar[i][0]
            ascii_board += "|"
            ascii_board += "".join(points[i][POINTS_PER_QUADRANT:])
            ascii_board += "|"

            ascii_board += player_score_top if i == 0 else ""
            ascii_board += (
                message if int(self.match.turn) != int(self.player) and i == 1 else ""
            )
            ascii_board += player_pip_count_top if i == 3 else ""
            ascii_board += (
                set_match_text(self.match, i)
                if i == int(ASCII_BOARD_HEIGHT / 2)
                else ""
            )
            ascii_board += (
                message
                if int(self.match.turn) == int(self.player)
                and i == int(ASCII_BOARD_HEIGHT) - 2
                else ""
            )
            ascii_board += player_pip_count_bottom if i == 7 else ""
            ascii_board += (
                player_score_bottom if i == int(ASCII_BOARD_HEIGHT) - 1 else ""
            )
            ascii_board += "\n"

        # Bottom Player display
        ascii_board += " "
        ascii_board += (
            ASCII_13_24 if int(self.match.turn) != int(self.player) else ASCII_12_01
        )
        ascii_board += player_text_bottom

        return ascii_board
