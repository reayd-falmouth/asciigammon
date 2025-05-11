"""Unit tests for pybg.py"""

import pytest
import re
from typing import List, Optional, Tuple, cast

from pybg.core.board import (
    BACKGAMMON_STARTING_POSITION_ID,
    Board,
    BoardError,
    GameState,
    Resign,
)
from pybg.core.player import Player, PlayerType
from pybg.gnubg.position import Position

pytestmark = pytest.mark.unit


def test_backgammon(player0, player1):
    # class Backgammon
    bg = Board(
        position_id=BACKGAMMON_STARTING_POSITION_ID,
    )
    assert bg

    bg.player0 = Player(PlayerType.ZERO, player0)
    bg.player1 = Player(PlayerType.ONE, player1)
    bg.player = bg.player0

    # def first_roll()
    die_1, die_2 = bg.first_roll()
    assert 1 <= die_1 <= 6
    assert 1 <= die_2 <= 6

    # Test for other condition
    # if die_1 > die_2:
    #     die_1, die_2 = bg.first_roll()
    # elif die_1 < die_2:
    #     die_1, die_2 = bg.first_roll()

    # Simulate a game to test the functionality
    bg.match.game_state = GameState.PLAYING

    # def ascii_board()
    ascii_board = str(bg)
    assert type(ascii_board) == str

    # def __repr__()
    bg_object = repr(bg)
    assert bg_object

    # def to_json()
    json = bg.to_json()
    assert "position" in json
    assert "match" in json
    # assert "gnubgId" in json


def test_generate():
    """Tests the skip function"""
    bg = Board(
        position_id=BACKGAMMON_STARTING_POSITION_ID,
    )
    bg.match.player = PlayerType.ZERO
    bg.position = Position(
        board_points=(
            -1,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            1,
        ),
        player_bar=1,
        player_off=1,
        opponent_bar=1,
        opponent_off=1,
    )
    bg.match.dice = (1, 2)
    assert len(bg.generate_plays()) == 2


def test_encode():
    """Tests the encode function"""
    bg = Board(
        position_id=BACKGAMMON_STARTING_POSITION_ID,
    )
    encoded_string = bg.encode()
    assert encoded_string == "4HPwATDgc/ABMA:MAAAAAAAAAAA"


def test_start():
    """Tests the start function"""
    bg = Board(
        position_id=BACKGAMMON_STARTING_POSITION_ID,
    )
    bg.start()

    assert bg.match.game_state == GameState.ROLLED
    assert bg.match.length == 0
    assert bg.match.dice != (0, 0)


def test_roll():
    """Tests roll"""
    bg = Board(
        position_id=BACKGAMMON_STARTING_POSITION_ID,
    )
    bg.roll()
    assert bg.match.game_state == GameState.ROLLED
    assert bg.match.dice != (0, 0)

    with pytest.raises(
        BoardError, match=re.escape(f"Dice have already been rolled: {bg.match.dice}")
    ):
        bg.roll()


def test_calculate_score():
    """Tests the caluclate score function"""
    bg = Board(
        position_id=BACKGAMMON_STARTING_POSITION_ID,
    )
    score = bg.calculate_score(3, 3)
    assert score == 9


def test_update_score():
    """Tests the update score function"""
    bg = Board(
        position_id=BACKGAMMON_STARTING_POSITION_ID,
    )
    bg.update_score(2, 3, PlayerType.ZERO)
    assert bg.match.player_0_score == 6

    bg.update_score(2, 3, PlayerType.ONE)
    assert bg.match.player_1_score == 6


def test_end_game(capfd):
    """Tests the update score function"""
    bg = Board(
        position_id=BACKGAMMON_STARTING_POSITION_ID,
    )
    bg.match.length = 1
    bg.update_score(2, 3, PlayerType.ZERO)
    bg.end_game()
    out, err = capfd.readouterr()
    # assert out == "Player 0 wins the match!\n"

    bg = Board(
        position_id=BACKGAMMON_STARTING_POSITION_ID,
    )
    bg.match.length = 1
    bg.update_score(2, 3, PlayerType.ONE)
    bg.end_game()
    out, err = capfd.readouterr()
    # assert out == "Player 1 wins the match!\n"

    bg = Board(
        position_id=BACKGAMMON_STARTING_POSITION_ID,
    )
    bg.match.length = 1
    bg.end_game()
    assert bg.position.encode() == "4HPwATDgc/ABMA"
    assert bg.match.dice != (0, 0)
    assert bg.match.game_state == GameState.ROLLED


def test_resign():
    """Tests the resign function"""
    bg = Board(
        position_id=BACKGAMMON_STARTING_POSITION_ID,
    )
    bg.match.dice = bg.first_roll()
    with pytest.raises(
        BoardError, match="You must specify resignation: single, gammon or backgammon"
    ):
        bg.resign(None)

    player = bg.match.player
    bg.resign(Resign.GAMMON)
    assert bg.match.game_state == GameState.RESIGNED
    assert bg.match.resign == Resign.GAMMON
    if player == PlayerType.ZERO:
        assert bg.match.player == PlayerType.ONE
    else:
        assert bg.match.player == PlayerType.ZERO


def test_end_turn():
    """Tests end turn"""

    # Test an immediate resignation
    # With a match of length of 1 this should end the match completly
    bg = Board(
        position_id=BACKGAMMON_STARTING_POSITION_ID,
    )
    bg.ref = ""
    bg.match.length = 1
    player = bg.match.player
    bg.end_turn()
    assert bg.match.player_1_score == 0
    assert bg.match.dice == (0, 0)
    assert bg.match.game_state == GameState.ON_ROLL
    if player == PlayerType.ONE:
        assert bg.match.player == PlayerType.ZERO
    else:
        assert bg.match.player == PlayerType.ONE


def test_take():
    """Tests the take method"""
    bg = Board(
        position_id=BACKGAMMON_STARTING_POSITION_ID,
    )
    bg.ref = ""
    bg.match.game_state = GameState.DOUBLED
    bg.match.turn = PlayerType.ONE
    bg.match.player = PlayerType.ONE
    bg.take()
    if bg.match.player == PlayerType.ONE:
        assert bg.match.cube_holder == PlayerType.ONE
    else:
        assert bg.match.cube_holder == PlayerType.ONE
    assert bg.match.dice == (0, 0)

    bg = Board(
        position_id=BACKGAMMON_STARTING_POSITION_ID,
    )
    with pytest.raises(BoardError, match="No double to take"):
        bg.take()


def test_reject():
    """Test reject method"""
    bg = Board(
        position_id=BACKGAMMON_STARTING_POSITION_ID,
    )
    bg.ref = ""
    bg.match.player = PlayerType.ZERO
    bg.match.turn = PlayerType.ZERO
    bg.resign(Resign.SINGLE_GAME)
    bg.reject()

    bg = Board(
        position_id=BACKGAMMON_STARTING_POSITION_ID,
    )
    bg.match.player = PlayerType.ZERO
    bg.match.turn = PlayerType.ZERO
    with pytest.raises(BoardError, match="No resignation to reject"):
        bg.reject()


def test_accept():
    """Test reject method"""
    bg = Board(
        position_id=BACKGAMMON_STARTING_POSITION_ID,
    )
    bg.ref = ""
    bg.match.player = PlayerType.ZERO
    bg.match.turn = PlayerType.ZERO
    bg.resign(Resign.SINGLE_GAME)
    bg.accept()

    bg = Board(
        position_id=BACKGAMMON_STARTING_POSITION_ID,
    )
    bg.match.player = PlayerType.ZERO
    bg.match.turn = PlayerType.ZERO
    with pytest.raises(BoardError, match="No resignation to accept"):
        bg.accept()


def test_double():
    """Test double method"""
    bg = Board(
        position_id=BACKGAMMON_STARTING_POSITION_ID,
    )
    bg.ref = ""
    bg.match.player = PlayerType.ZERO
    bg.match.turn = PlayerType.ZERO

    with pytest.raises(BoardError, match="You cannot double until you hold the cube."):
        bg.double()

    bg.match.cube_holder = PlayerType.ZERO
    with pytest.raises(BoardError, match="You cannot double right now."):
        bg.double()

    bg.match.game_state = GameState.ON_ROLL
    bg.match.cube_holder = PlayerType.CENTERED

    bg.double()
    assert bg.match.player == PlayerType.ZERO
    assert bg.match.cube_holder == PlayerType.CENTERED
    assert bg.match.cube_value == 2
    assert bg.match.double is True
    assert bg.match.game_state == GameState.DOUBLED


def test_redouble():
    """Test redouble method"""
    bg = Board(
        position_id=BACKGAMMON_STARTING_POSITION_ID,
    )
    bg.ref = ""
    bg.match.player = PlayerType.ZERO
    bg.match.turn = PlayerType.ZERO

    with pytest.raises(BoardError, match="Cannot redouble: it's not your turn"):
        bg.redouble()

    bg.match.game_state = GameState.ON_ROLL
    bg.match.cube_holder = PlayerType.CENTERED

    bg.double()
    bg.redouble()
    assert bg.match.player == PlayerType.ZERO
    assert bg.match.cube_holder == PlayerType.ONE
    assert bg.match.cube_value == 4
    assert bg.match.double is True
    assert bg.match.game_state == GameState.ON_ROLL
    assert bg.match.dice == (0, 0)


def test_drop():
    """Test redouble method"""
    bg = Board(
        position_id=BACKGAMMON_STARTING_POSITION_ID,
    )
    bg.ref = ""
    bg.match.length = 9
    bg.match.player = PlayerType.ZERO
    bg.match.turn = PlayerType.ZERO

    with pytest.raises(BoardError, match="No double to drop"):
        bg.drop()

    bg.match.game_state = GameState.ON_ROLL
    bg.match.cube_holder = PlayerType.CENTERED

    bg.double()
    bg.drop()

    assert bg.match.player_0_score == 1
    assert bg.match.cube_holder == PlayerType.CENTERED
    assert bg.match.cube_value == 1
    assert bg.match.double is False
    assert bg.position.encode() == "4HPwATDgc/ABMA"
    assert bg.match.dice != (0, 0)
    assert bg.match.game_state == GameState.ROLLED


def test_plays():
    """Tests the play method"""

    def do_move(bg: Board, arg: str) -> Board:
        """Make a pybg move: move <from> <to> ..."""
        Moves = Tuple[Tuple[Optional[int], Optional[int]], ...]

        def parse_arg(arg: str) -> Moves:
            arg_ints: List[Optional[int]] = list(
                map(lambda n: (int(n) - 1) if n.isdigit() else -1, arg.split())
            )

            if len(arg_ints) % 2 == 1:
                raise ValueError("Incomplete move.")
            if len(arg_ints) > 8:
                raise ValueError("Too many moves.")

            return cast(
                Moves,
                tuple(tuple(arg_ints[i : i + 2]) for i in range(0, len(arg_ints), 2)),
            )

        moves: Moves = parse_arg(arg)

        bg.play(moves)

        return bg

    bg = Board(
        position_id=BACKGAMMON_STARTING_POSITION_ID,
    )
    bg.ref = ""
    bg.match.length = 1
    bg.match.dice = (1, 2)

    with pytest.raises(
        BoardError,
        match=re.escape("Invalid move sequence: ((22, 21), (22, 20))"),
    ):
        do_move(bg, "23 22 23 21")

    bg.position = Position(
        board_points=(
            1,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
        ),
        player_bar=0,
        player_off=14,
        opponent_bar=15,
        opponent_off=0,
    )
    bg = do_move(bg, "1 off")
    assert bg.match.game_state == GameState.GAME_OVER


def test_multiplier():
    """Tests the multiplier methoc"""
    bg = Board(
        position_id=BACKGAMMON_STARTING_POSITION_ID,
    )
    bg.ref = ""

    with pytest.raises(
        BoardError,
        match="Checkers are still on the board, what do you resign, single, gammon or backgammon?",
    ):
        bg.multiplier()

    bg.position = Position(
        board_points=(
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
        ),
        player_bar=0,
        player_off=15,
        opponent_bar=1,
        opponent_off=0,
    )
    multiplier = bg.multiplier()
    assert multiplier == Resign.BACKGAMMON

    bg.position = Position(
        board_points=(
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
        ),
        player_bar=0,
        player_off=15,
        opponent_bar=1,
        opponent_off=14,
    )
    multiplier = bg.multiplier()
    assert multiplier == Resign.SINGLE_GAME

    bg.position = Position(
        board_points=(
            0,
            0,
            0,
            0,
            0,
            -1,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
        ),
        player_bar=0,
        player_off=15,
        opponent_bar=0,
        opponent_off=0,
    )
    multiplier = bg.multiplier()
    assert multiplier == Resign.BACKGAMMON

    bg.position = Position(
        board_points=(
            0,
            0,
            0,
            0,
            0,
            0,
            -1,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
        ),
        player_bar=0,
        player_off=15,
        opponent_bar=0,
        opponent_off=0,
    )
    multiplier = bg.multiplier()
    assert multiplier == Resign.GAMMON


def test_set_player_score(capfd, player0, player1):
    """test the set player sore method"""

    bg = Board(
        position_id=BACKGAMMON_STARTING_POSITION_ID,
    )
    bg.ref = ""
    bg.player0 = Player(PlayerType.ZERO, player0)
    bg.player1 = Player(PlayerType.ONE, player1)
    bg.match.player_0_score = 5
    bg.match.player_1_score = 7

    bg.match.player = PlayerType.ZERO
    bg.player = bg.player0
    board = """ Board           Position ID: 4HPwATDgc/ABMA
                 Match ID   : MAAAAFAAOAAA
 +13-14-15-16-17-18------19-20-21-22-23-24-+     X: 
 | O           X    |   | X              O |     7 points
 | O           X    |   | X              O |
 | O           X    |   | X                |
 | O                |   | X                |     pips: 167
 | O                |   | X                |
v|                  |BAR|                  |     $0 money game (Cube: 1)
 | X                |   | O                |
 | X                |   | O                |     pips: 167
 | X           O    |   | O                |
 | X           O    |   | O              X |     
 | X           O    |   | O              X |     5 points
 +12-11-10--9--8--7-------6--5--4--3--2--1-+     O: """
    assert str(board) == bg.__str__()

    bg.match.player = PlayerType.ONE
    bg.player = bg.player1
    bg.match.swap_players()
    bg.position.swap_players()

    #     board = """ Board           Position ID: 4HPwATDgc/ABMA
    #                  Match ID   : MAgAAFAAOAAA
    #  +13-14-15-16-17-18------19-20-21-22-23-24-+     O:
    #  | X           O    |   | O              X |     5 points
    #  | X           O    |   | O              X |
    #  | X           O    |   | O                |
    #  | X                |   | O                |     pips: 167
    #  | X                |   | O                |
    # v|                  |BAR|                  |     $0 money game (Cube: 1)
    #  | O                |   | X                |
    #  | O                |   | X                |     pips: 167
    #  | O           X    |   | X                |
    #  | O           X    |   | X              O |
    #  | O           X    |   | X              O |     7 points
    #  +12-11-10--9--8--7-------6--5--4--3--2--1-+     X: """
    #     assert str(board) == bg.__str__()

    bg.match.game_state = GameState.ON_ROLL
    board = """ Board           Position ID: 4HPwATDgc/ABMA
                 Match ID   : MA0AAFAAOAAA
 +13-14-15-16-17-18------19-20-21-22-23-24-+     O: 
 | X           O    |   | O              X |     5 points
 | X           O    |   | O              X |
 | X           O    |   | O                |
 | X                |   | O                |     pips: 167
 | X                |   | O                |
v|                  |BAR|                  |     $0 money game (Cube: 1)
 | O                |   | X                |
 | O                |   | X                |     pips: 167
 | O           X    |   | X                |
 | O           X    |   | X              O |     On roll
 | O           X    |   | X              O |     7 points
 +12-11-10--9--8--7-------6--5--4--3--2--1-+     X: """
    assert str(board) == bg.__str__()

    bg.match.game_state = GameState.ROLLED
    bg.match.dice = (1, 1)
    board = """ Board           Position ID: 4HPwATDgc/ABMA
                 Match ID   : MI4EAFAAOAAA
 +13-14-15-16-17-18------19-20-21-22-23-24-+     O: 
 | X           O    |   | O              X |     5 points
 | X           O    |   | O              X |
 | X           O    |   | O                |
 | X                |   | O                |     pips: 167
 | X                |   | O                |
v|                  |BAR|                  |     $0 money game (Cube: 1)
 | O                |   | X                |
 | O                |   | X                |     pips: 167
 | O           X    |   | X                |
 | O           X    |   | X              O |     Rolled (1, 1)
 | O           X    |   | X              O |     7 points
 +12-11-10--9--8--7-------6--5--4--3--2--1-+     X: """
    assert str(board) == bg.__str__()

    bg.match.game_state = GameState.DOUBLED
    board = """ Board           Position ID: 4HPwATDgc/ABMA
                 Match ID   : MI8EAFAAOAAA
 +13-14-15-16-17-18------19-20-21-22-23-24-+     O: 
 | X           O    |   | O              X |     5 points
 | X           O    |   | O              X |
 | X           O    |   | O                |
 | X                |   | O                |     pips: 167
 | X                |   | O                |
v|                  |BAR|                  |     $0 money game (Cube: 1)
 | O                |   | X                |
 | O                |   | X                |     pips: 167
 | O           X    |   | X                |
 | O           X    |   | X              O |     Cube offered at 1
 | O           X    |   | X              O |     7 points
 +12-11-10--9--8--7-------6--5--4--3--2--1-+     X: """
    assert str(board) == bg.__str__()

    bg.match.game_state = GameState.RESIGNED
    bg.match.resign = Resign.SINGLE_GAME
    board = """ Board           Position ID: 4HPwATDgc/ABMA
                 Match ID   : MKsEAFAAOAAA
 +13-14-15-16-17-18------19-20-21-22-23-24-+     O: 
 | X           O    |   | O              X |     5 points
 | X           O    |   | O              X |
 | X           O    |   | O                |
 | X                |   | O                |     pips: 167
 | X                |   | O                |
v|                  |BAR|                  |     $0 money game (Cube: 1)
 | O                |   | X                |
 | O                |   | X                |     pips: 167
 | O           X    |   | X                |
 | O           X    |   | X              O |     Opponent resigns a single
 | O           X    |   | X              O |     7 points
 +12-11-10--9--8--7-------6--5--4--3--2--1-+     X: """
    assert str(board) == bg.__str__()

    bg.match.game_state = GameState.ON_ROLL
    bg.match.cube_holder = PlayerType.ONE
    board = """ Board           Position ID: 4HPwATDgc/ABMA
                 Match ID   : EK0EAFAAOAAA
 +13-14-15-16-17-18------19-20-21-22-23-24-+     O: 
 | X           O    |   | O              X |     5 points
 | X           O    |   | O              X |
 | X           O    |   | O                |
 | X                |   | O                |     pips: 167
 | X                |   | O                |
v|                  |BAR|                  |     $0 money game (Cube: 1)
 | O                |   | X                |
 | O                |   | X                |     pips: 167
 | O           X    |   | X                |
 | O           X    |   | X              O |     On roll
 | O           X    |   | X              O |     7 points
 +12-11-10--9--8--7-------6--5--4--3--2--1-+     X:  (Cube: 1)"""
    assert str(board) == bg.__str__()


#     bg.position = Position(
#         board_points=(
#             6,
#             0,
#             0,
#             0,
#             0,
#             0,
#             0,
#             0,
#             0,
#             0,
#             0,
#             0,
#             0,
#             0,
#             0,
#             0,
#             0,
#             0,
#             0,
#             0,
#             0,
#             0,
#             0,
#             0,
#         ),
#         player_bar=0,
#         player_off=9,
#         opponent_bar=0,
#         opponent_off=15,
#     )
#     board = """ Board           Position ID: AAAAfgAAAAAAAA
#                  Match ID   : EKUEAFAAOAAA
#  +13-14-15-16-17-18------19-20-21-22-23-24-+     X: player1 (Cube: 1)
#  |                  |   |                  |     7 points
#  |                  |   |                  |
#  |                  |   |                  |
#  |                  |   |                  |     pips: 0, rolls: 0.0
#  |                  |   |                  |
# v|                  |BAR|                  |     $0 money game (Cube: 1)
#  |                  |   |                6 |
#  |                  |   |                O |     pips: 6, rolls: 2.69
#  |                  |   |                O |
#  |                  |   |                O |     On roll
#  |                  |   |                O |     5 points
#  +12-11-10--9--8--7-------6--5--4--3--2--1-+     O: player0"""
#
#     assert str(board) == bg.__str__()


def test_is_player_home(capfd, player0, player1):
    bg = Board(
        position_id=BACKGAMMON_STARTING_POSITION_ID,
    )
    bg.player0 = Player(PlayerType.ZERO, player0)
    bg.player1 = Player(PlayerType.ONE, player1)
    bg.match.player_0_score = 5
    bg.match.player_1_score = 7

    bg.match.player = PlayerType.ZERO
    bg.player = bg.player0
    bg.position = Position(
        board_points=(
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
        ),
        player_bar=0,
        player_off=15,
        opponent_bar=0,
        opponent_off=15,
    )
    assert bg.is_player_home()

    bg.position = Position(
        board_points=(
            2,
            2,
            2,
            2,
            2,
            2,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            -2,
            -2,
            -2,
            -2,
            -2,
            -2,
        ),
        player_bar=0,
        player_off=3,
        opponent_bar=0,
        opponent_off=3,
    )
    assert bg.is_player_home()

    bg.position = Position(
        board_points=(
            2,
            2,
            2,
            2,
            2,
            2,
            -3,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            3,
            -2,
            -2,
            -2,
            -2,
            -2,
            -2,
        ),
        player_bar=0,
        player_off=0,
        opponent_bar=0,
        opponent_off=0,
    )
    assert not bg.is_player_home()

    bg.position = Position(
        board_points=(
            -2,
            2,
            2,
            2,
            2,
            2,
            -2,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            2,
            -2,
            -2,
            -2,
            -2,
            -2,
            2,
        ),
        player_bar=0,
        player_off=1,
        opponent_bar=0,
        opponent_off=1,
    )
    assert not bg.is_player_home()


def test_is_opponent_home(capfd, player0, player1):
    bg = Board(
        position_id=BACKGAMMON_STARTING_POSITION_ID,
    )
    bg.player0 = Player(PlayerType.ZERO, player0)
    bg.player1 = Player(PlayerType.ONE, player1)
    bg.match.player_0_score = 5
    bg.match.player_1_score = 7

    bg.match.player = PlayerType.ZERO
    bg.player = bg.player0
    bg.position = Position(
        board_points=(
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
        ),
        player_bar=0,
        player_off=15,
        opponent_bar=0,
        opponent_off=15,
    )
    assert bg.is_opponent_home()

    bg.position = Position(
        board_points=(
            2,
            2,
            2,
            2,
            2,
            2,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            -2,
            -2,
            -2,
            -2,
            -2,
            -2,
        ),
        player_bar=0,
        player_off=3,
        opponent_bar=0,
        opponent_off=3,
    )
    assert bg.is_opponent_home()

    bg.position = Position(
        board_points=(
            2,
            2,
            2,
            2,
            2,
            2,
            -3,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            3,
            -2,
            -2,
            -2,
            -2,
            -2,
            -2,
        ),
        player_bar=0,
        player_off=0,
        opponent_bar=0,
        opponent_off=0,
    )
    assert not bg.is_opponent_home()

    bg.position = Position(
        board_points=(
            -2,
            2,
            2,
            2,
            2,
            2,
            -2,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            2,
            -2,
            -2,
            -2,
            -2,
            -2,
            2,
        ),
        player_bar=0,
        player_off=1,
        opponent_bar=0,
        opponent_off=1,
    )
    assert not bg.is_opponent_home()


def test_checkers_on_bar(capfd, player0, player1):
    position_id = "/wEAAO4/AADAAQ"
    bg = Board(position_id=position_id, match_id="MAAAAAAAAAAA")
    bg.ref = ""
    board = """ Board           Position ID: /wEAAO4/AADAAQ
                 Match ID   : MAAAAAAAAAAA
 +13-14-15-16-17-18------19-20-21-22-23-24-+     X: player1
 |                  | O |                X |     0 points
 |                  | O |                X |
 |                  | O |                X |
 |                  |   |                X |     pips: 84
 |                  |   |                9 |
v|                  |BAR|                  |     $0 money game (Cube: 1)
 |                  |   |                9 |
 |                  |   |                O |     pips: 84
 |                  | X |                O |
 |                  | X |                O |     
 |                  | X |                O |     0 points
 +12-11-10--9--8--7-------6--5--4--3--2--1-+     O: player0"""
    assert str(board) == bg.__str__()
