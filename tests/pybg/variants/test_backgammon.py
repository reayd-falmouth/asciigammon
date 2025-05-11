"""Unit tests for backgammon.py"""

import re
from typing import List, Optional, Tuple, cast

from pybg.core.board import BoardError, GameState, Resign
from pybg.core.player import Player, PlayerType
from pybg.gnubg.position import Position
from pybg.variants.backgammon import Backgammon
import pytest

pytestmark = pytest.mark.unit


def test_backgammon(player0, player1):
    # class Backgammon
    bg = Backgammon()
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
    bg = Backgammon()
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
    bg = Backgammon()
    encoded_string = bg.encode()
    assert encoded_string == "4HPwATDgc/ABMA:cAgAAAAAAAAA"


def test_start():
    """Tests the start function"""
    bg = Backgammon()
    bg.start()

    assert bg.match.game_state == GameState.ROLLED
    assert bg.match.length == 0
    assert bg.match.dice != (0, 0)


def test_roll():
    """Tests roll"""
    bg = Backgammon()
    bg.roll()
    assert bg.match.game_state == GameState.ROLLED
    assert bg.match.dice != (0, 0)

    with pytest.raises(
        BoardError, match=re.escape(f"Dice have already been rolled: {bg.match.dice}")
    ):
        bg.roll()


def test_calculate_score():
    """Tests the caluclate score function"""
    bg = Backgammon()
    score = bg.calculate_score(3, 3)
    assert score == 9


def test_update_score():
    """Tests the update score function"""
    bg = Backgammon()
    bg.update_score(2, 3, PlayerType.ZERO)
    assert bg.match.player_0_score == 6
    bg.update_score(2, 3, PlayerType.ONE)
    assert bg.match.player_1_score == 6


def test_end_game(capfd):
    """Tests the update score function"""
    bg = Backgammon()
    bg.match.length = 1
    bg.update_score(2, 3, PlayerType.ZERO)
    bg.end_game()
    out, err = capfd.readouterr()
    # assert out == "Player 0 wins the match!\n"

    bg = Backgammon()
    bg.match.length = 1
    bg.update_score(2, 3, PlayerType.ONE)
    bg.end_game()
    out, err = capfd.readouterr()
    # assert out == "Player 1 wins the match!\n"

    bg = Backgammon()
    bg.match.length = 1
    bg.end_game()
    assert bg.position.encode() == "4HPwATDgc/ABMA"
    assert bg.match.dice != (0, 0)
    assert bg.match.game_state == GameState.ROLLED


def test_resign():
    """Tests the resign function"""
    bg = Backgammon()
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
    bg = Backgammon()
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


# def test_skip():
#     """Tests the skip function"""
#     bg = Backgammon()
#     player = bg.match.player
#     bg.position = Position(
#         board_points=(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1),
#         player_bar=0,
#         player_off=0,
#         opponent_bar=0,
#         opponent_off=0
#     )
#     bg.roll()
#     with pytest.raises(BoardError, match="Cannot skip turn: \d+ possible plays"):
#         bg.skip()
#
#     # TODO: ValueError: max() arg is an empty sequence
#     bg = Backgammon()
#     player = bg.match.player
#     bg.position = Position(
#         board_points=(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -2, -2, -2, -2, -2, -2),
#         player_bar=1,
#         player_off=14,
#         opponent_bar=0,
#         opponent_off=3
#     )
#     bg.roll()
#     bg.skip()
#     assert bg.match.dice == (0, 0)
#     assert bg.match.game_state == GameState.ON_ROLL
#     if player == PlayerType.ONE:
#         assert bg.match.player == PlayerType.ZERO
#     else:
#         assert bg.match.player == PlayerType.ONE


def test_take():
    """Tests the take method"""
    bg = Backgammon()
    bg.match.game_state = GameState.DOUBLED
    bg.match.turn = PlayerType.ONE
    bg.match.player = PlayerType.ONE
    bg.take()
    if bg.match.player == PlayerType.ONE:
        assert bg.match.cube_holder == PlayerType.ONE
    else:
        assert bg.match.cube_holder == PlayerType.ZERO
    assert bg.match.dice == (0, 0)

    bg = Backgammon()
    with pytest.raises(BoardError, match="No double to take"):
        bg.take()


def test_reject():
    """Test reject method"""
    bg = Backgammon()
    bg.match.player = PlayerType.ZERO
    bg.match.turn = PlayerType.ZERO
    bg.resign(Resign.SINGLE_GAME)
    bg.reject()

    bg = Backgammon()
    bg.match.player = PlayerType.ZERO
    bg.match.turn = PlayerType.ZERO
    with pytest.raises(BoardError, match="No resignation to reject"):
        bg.reject()


def test_accept():
    """Test reject method"""
    bg = Backgammon()
    bg.match.player = PlayerType.ZERO
    bg.match.turn = PlayerType.ZERO
    bg.resign(Resign.SINGLE_GAME)
    bg.accept()

    bg = Backgammon()
    bg.match.player = PlayerType.ZERO
    bg.match.turn = PlayerType.ZERO
    with pytest.raises(BoardError, match="No resignation to accept"):
        bg.accept()


def test_double():
    """Test double method"""
    bg = Backgammon()
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
    bg = Backgammon()
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
    bg = Backgammon()
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

    def do_move(bg: Backgammon, arg: str) -> Backgammon:
        """Make a backgammon move: move <from> <to> ..."""
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

    bg = Backgammon()

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
    bg = Backgammon()

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

    bg = Backgammon()
    bg.ref = ""
    bg.player0 = Player(PlayerType.ZERO, player0)
    bg.player1 = Player(PlayerType.ONE, player1)
    bg.match.player_0_score = 5
    bg.match.player_1_score = 7

    bg.match.player = PlayerType.ZERO
    bg.player = bg.player0
    board = """ Backgammon      Position ID: 4HPwATDgc/ABMA
                 Match ID   : MAgAAFAAOAAA
 +12-11-10--9--8--7-------6--5--4--3--2--1-+     X: 
 | O           X    |   | X              O |     7 points
 | O           X    |   | X              O |     
 | O           X    |   | X                |
 | O                |   | X                |     pips: 167
 | O                |   | X                |
^|                  |BAR|                  |     $0 money game (Cube: 1)
 | X                |   | O                |
 | X                |   | O                |     pips: 167
 | X           O    |   | O                |
 | X           O    |   | O              X |
 | X           O    |   | O              X |     5 points
 +13-14-15-16-17-18------19-20-21-22-23-24-+     O: """
    assert str(board) == bg.__str__()

    bg.match.player = PlayerType.ONE
    bg.player = bg.player1
    bg.match.swap_players()
    bg.position.swap_players()

    board = """ Backgammon      Position ID: 4HPwATDgc/ABMA
                 Match ID   : MAAAAFAAOAAA
 +12-11-10--9--8--7-------6--5--4--3--2--1-+     O: 
 | X           O    |   | O              X |     5 points
 | X           O    |   | O              X |     
 | X           O    |   | O                |
 | X                |   | O                |     pips: 167
 | X                |   | O                |
^|                  |BAR|                  |     $0 money game (Cube: 1)
 | O                |   | X                |
 | O                |   | X                |     pips: 167
 | O           X    |   | X                |
 | O           X    |   | X              O |
 | O           X    |   | X              O |     7 points
 +13-14-15-16-17-18------19-20-21-22-23-24-+     X: """
    assert str(board) == bg.__str__()

    bg.match.game_state = GameState.ON_ROLL
    board = """ Backgammon      Position ID: 4HPwATDgc/ABMA
                 Match ID   : MAUAAFAAOAAA
 +12-11-10--9--8--7-------6--5--4--3--2--1-+     O: 
 | X           O    |   | O              X |     5 points
 | X           O    |   | O              X |     On roll
 | X           O    |   | O                |
 | X                |   | O                |     pips: 167
 | X                |   | O                |
^|                  |BAR|                  |     $0 money game (Cube: 1)
 | O                |   | X                |
 | O                |   | X                |     pips: 167
 | O           X    |   | X                |
 | O           X    |   | X              O |
 | O           X    |   | X              O |     7 points
 +13-14-15-16-17-18------19-20-21-22-23-24-+     X: """
    assert str(board) == bg.__str__()

    bg.match.game_state = GameState.ROLLED
    bg.match.dice = (1, 1)
    board = """ Backgammon      Position ID: 4HPwATDgc/ABMA
                 Match ID   : MIYEAFAAOAAA
 +12-11-10--9--8--7-------6--5--4--3--2--1-+     O: 
 | X           O    |   | O              X |     5 points
 | X           O    |   | O              X |     Rolled (1, 1)
 | X           O    |   | O                |
 | X                |   | O                |     pips: 167
 | X                |   | O                |
^|                  |BAR|                  |     $0 money game (Cube: 1)
 | O                |   | X                |
 | O                |   | X                |     pips: 167
 | O           X    |   | X                |
 | O           X    |   | X              O |
 | O           X    |   | X              O |     7 points
 +13-14-15-16-17-18------19-20-21-22-23-24-+     X: """
    assert str(board) == bg.__str__()

    bg.match.game_state = GameState.DOUBLED
    board = """ Backgammon      Position ID: 4HPwATDgc/ABMA
                 Match ID   : MIcEAFAAOAAA
 +12-11-10--9--8--7-------6--5--4--3--2--1-+     O: 
 | X           O    |   | O              X |     5 points
 | X           O    |   | O              X |     Cube offered at 1
 | X           O    |   | O                |
 | X                |   | O                |     pips: 167
 | X                |   | O                |
^|                  |BAR|                  |     $0 money game (Cube: 1)
 | O                |   | X                |
 | O                |   | X                |     pips: 167
 | O           X    |   | X                |
 | O           X    |   | X              O |
 | O           X    |   | X              O |     7 points
 +13-14-15-16-17-18------19-20-21-22-23-24-+     X: """
    assert str(board) == bg.__str__()

    bg.match.game_state = GameState.RESIGNED
    bg.match.resign = Resign.SINGLE_GAME
    board = """ Backgammon      Position ID: 4HPwATDgc/ABMA
                 Match ID   : MKMEAFAAOAAA
 +12-11-10--9--8--7-------6--5--4--3--2--1-+     O: 
 | X           O    |   | O              X |     5 points
 | X           O    |   | O              X |     Opponent resigns a single
 | X           O    |   | O                |
 | X                |   | O                |     pips: 167
 | X                |   | O                |
^|                  |BAR|                  |     $0 money game (Cube: 1)
 | O                |   | X                |
 | O                |   | X                |     pips: 167
 | O           X    |   | X                |
 | O           X    |   | X              O |
 | O           X    |   | X              O |     7 points
 +13-14-15-16-17-18------19-20-21-22-23-24-+     X: """
    assert str(board) == bg.__str__()

    bg.match.game_state = GameState.ON_ROLL
    bg.match.cube_holder = PlayerType.ONE
    board = """ Backgammon      Position ID: 4HPwATDgc/ABMA
                 Match ID   : EKUEAFAAOAAA
 +12-11-10--9--8--7-------6--5--4--3--2--1-+     O: 
 | X           O    |   | O              X |     5 points
 | X           O    |   | O              X |     On roll
 | X           O    |   | O                |
 | X                |   | O                |     pips: 167
 | X                |   | O                |
^|                  |BAR|                  |     $0 money game (Cube: 1)
 | O                |   | X                |
 | O                |   | X                |     pips: 167
 | O           X    |   | X                |
 | O           X    |   | X              O |
 | O           X    |   | X              O |     7 points
 +13-14-15-16-17-18------19-20-21-22-23-24-+     X:  (Cube: 1)"""
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
#         player_off=0,
#         opponent_bar=0,
#         opponent_off=0,
#     )
#     board = """ Backgammon      Position ID: AAAAfgAAAAAAAA
#                  Match ID   : EKUEAFAAOAAA
#  +12-11-10--9--8--7-------6--5--4--3--2--1-+     O:
#  |                  |   |                O |     5 points
#  |                  |   |                O |     On roll
#  |                  |   |                O |
#  |                  |   |                O |     pips: 6
#  |                  |   |                6 |
# ^|                  |BAR|                  |     $0 money game (Cube: 1)
#  |                  |   |                  |
#  |                  |   |                  |     pips: 0
#  |                  |   |                  |
#  |                  |   |                  |
#  |                  |   |                  |     7 points
#  +13-14-15-16-17-18------19-20-21-22-23-24-+     X:  (Cube: 1)"""
#
#     assert str(board) == bg.__str__()
