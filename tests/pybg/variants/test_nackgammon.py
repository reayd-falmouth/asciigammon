"""Unit tests for nackgammon.py"""

import re
from typing import List, Optional, Tuple, cast

from pybg.core.board import BoardError, GameState, Resign
from pybg.core.player import Player, PlayerType
from pybg.gnubg.position import Position
from pybg.variants.nackgammon import Nackgammon
import pytest

pytestmark = pytest.mark.unit


def test_nackgammon(player0, player1):
    # class Nackgammon
    game = Nackgammon()
    game.ref = ""
    assert game

    game.player0 = Player(PlayerType.ZERO, player0)
    game.player1 = Player(PlayerType.ONE, player1)
    game.player = game.player0

    # def first_roll()
    die_1, die_2 = game.first_roll()
    assert 1 <= die_1 <= 6
    assert 1 <= die_2 <= 6

    # Test for other condition
    # if die_1 > die_2:
    #     die_1, die_2 = game.first_roll()
    # elif die_1 < die_2:
    #     die_1, die_2 = game.first_roll()

    # Simulate a game to test the functionality
    game.match.game_state = GameState.PLAYING

    # def ascii_board()
    ascii_board = str(game)
    assert type(ascii_board) == str

    # def __repr__()
    game_object = repr(game)
    assert game_object

    # def to_json()
    json = game.to_json()
    assert "position" in json
    assert "match" in json
    # assert "gnugameId" in json


def test_nackgammon_generate():
    """Tests the skip function"""
    game = Nackgammon()
    game.ref = ""
    game.match.player = PlayerType.ZERO
    game.position = Position(
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
    game.match.dice = (1, 2)
    assert len(game.generate_plays()) == 2


def test_nackgammon_encode():
    """Tests the encode function"""
    game = Nackgammon()
    encoded_string = game.encode()
    assert encoded_string == "4Dl4ADbgOXgANg:cAgAAAAAAAAA"


def test_nackgammon_start():
    """Tests the start function"""
    game = Nackgammon()
    game.start()

    assert game.match.game_state == GameState.ROLLED
    assert game.match.length == 0
    assert game.match.dice != (0, 0)


def test_nackgammon_roll():
    """Tests roll"""
    game = Nackgammon()
    game.roll()
    assert game.match.game_state == GameState.ROLLED
    assert game.match.dice != (0, 0)

    with pytest.raises(
        BoardError, match=re.escape(f"Dice have already been rolled: {game.match.dice}")
    ):
        game.roll()


def test_nackgammon_calculate_score():
    """Tests the caluclate score function"""
    game = Nackgammon()
    score = game.calculate_score(3, 3)
    assert score == 9


def test_nackgammon_update_score():
    """Tests the update score function"""
    game = Nackgammon()
    game.update_score(2, 3, PlayerType.ZERO)
    assert game.match.player_0_score == 6
    game.update_score(2, 3, PlayerType.ONE)
    assert game.match.player_1_score == 6


def test_nackgammon_end_game(capfd):
    """Tests the update score function"""
    game = Nackgammon()
    game.match.length = 1
    game.update_score(2, 3, PlayerType.ZERO)
    game.end_game()
    out, err = capfd.readouterr()
    # assert out == "Player 0 wins the match!\n"

    game = Nackgammon()
    game.match.length = 1
    game.update_score(2, 3, PlayerType.ONE)
    game.end_game()
    out, err = capfd.readouterr()
    # assert out == "Player 1 wins the match!\n"

    game = Nackgammon()
    game.match.length = 1
    game.end_game()
    assert game.position.encode() == "4Dl4ADbgOXgANg"
    assert game.match.dice != (0, 0)
    assert game.match.game_state == GameState.ROLLED


def test_nackgammon_resign():
    """Tests the resign function"""
    game = Nackgammon()
    game.match.dice = game.first_roll()
    with pytest.raises(
        BoardError, match="You must specify resignation: single, gammon or backgammon"
    ):
        game.resign(None)

    player = game.match.player
    game.resign(Resign.GAMMON)
    assert game.match.game_state == GameState.RESIGNED
    assert game.match.resign == Resign.GAMMON
    if player == PlayerType.ZERO:
        assert game.match.player == PlayerType.ONE
    else:
        assert game.match.player == PlayerType.ZERO


def test_nackgammon_end_turn():
    """Tests end turn"""

    # Test an immediate resignation
    # With a match of length of 1 this should end the match completly
    game = Nackgammon()
    game.match.length = 1
    player = game.match.player
    game.end_turn()
    assert game.match.player_1_score == 0
    assert game.match.dice == (0, 0)
    assert game.match.game_state == GameState.ON_ROLL
    if player == PlayerType.ONE:
        assert game.match.player == PlayerType.ZERO
    else:
        assert game.match.player == PlayerType.ONE


# def test_nackgammon_skip():
#     """Tests the skip function"""
#     game = Nackgammon()
#     player = game.match.player
#     game.position = Position(
#         board_points=(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1),
#         player_bar=0,
#         player_off=0,
#         opponent_bar=0,
#         opponent_off=0
#     )
#     game.roll()
#     with pytest.raises(BoardError, match="Cannot skip turn: \d+ possible plays"):
#         game.skip()
#
#     # TODO: ValueError: max() arg is an empty sequence
#     game = Nackgammon()
#     player = game.match.player
#     game.position = Position(
#         board_points=(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -2, -2, -2, -2, -2, -2),
#         player_bar=1,
#         player_off=14,
#         opponent_bar=0,
#         opponent_off=3
#     )
#     game.roll()
#     game.skip()
#     assert game.match.dice == (0, 0)
#     assert game.match.game_state == GameState.ON_ROLL
#     if player == PlayerType.ONE:
#         assert game.match.player == PlayerType.ZERO
#     else:
#         assert game.match.player == PlayerType.ONE


def test_nackgammon_take():
    """Tests the take method"""
    game = Nackgammon()
    game.match.game_state = GameState.DOUBLED
    game.match.turn = PlayerType.ONE
    game.match.player = PlayerType.ONE
    game.take()
    if game.match.player == PlayerType.ONE:
        assert game.match.cube_holder == PlayerType.ONE
    else:
        assert game.match.cube_holder == PlayerType.ZERO
    assert game.match.dice == (0, 0)

    game = Nackgammon()
    with pytest.raises(BoardError, match="No double to take"):
        game.take()


def test_nackgammon_reject():
    """Test reject method"""
    game = Nackgammon()
    game.match.player = PlayerType.ZERO
    game.match.turn = PlayerType.ZERO
    game.resign(Resign.SINGLE_GAME)
    game.reject()

    game = Nackgammon()
    game.match.player = PlayerType.ZERO
    game.match.turn = PlayerType.ZERO
    with pytest.raises(BoardError, match="No resignation to reject"):
        game.reject()


def test_nackgammon_accept():
    """Test reject method"""
    game = Nackgammon()
    game.match.player = PlayerType.ZERO
    game.match.turn = PlayerType.ZERO
    game.resign(Resign.SINGLE_GAME)
    game.accept()

    game = Nackgammon()
    game.match.player = PlayerType.ZERO
    game.match.turn = PlayerType.ZERO
    with pytest.raises(BoardError, match="No resignation to accept"):
        game.accept()


def test_nackgammon_double():
    """Test double method"""
    game = Nackgammon()
    game.match.player = PlayerType.ZERO
    game.match.turn = PlayerType.ZERO

    with pytest.raises(BoardError, match="You cannot double until you hold the cube."):
        game.double()

    game.match.cube_holder = PlayerType.ZERO
    with pytest.raises(BoardError, match="You cannot double right now."):
        game.double()

    game.match.game_state = GameState.ON_ROLL
    game.match.cube_holder = PlayerType.CENTERED

    game.double()
    assert game.match.player == PlayerType.ZERO
    assert game.match.cube_holder == PlayerType.CENTERED
    assert game.match.cube_value == 2
    assert game.match.double is True
    assert game.match.game_state == GameState.DOUBLED


def test_nackgammon_redouble():
    """Test redouble method"""
    game = Nackgammon()
    game.match.player = PlayerType.ZERO
    game.match.turn = PlayerType.ZERO

    with pytest.raises(BoardError, match="Cannot redouble: it's not your turn"):
        game.redouble()

    game.match.game_state = GameState.ON_ROLL
    game.match.cube_holder = PlayerType.CENTERED

    game.double()
    game.redouble()
    assert game.match.player == PlayerType.ZERO
    assert game.match.cube_holder == PlayerType.ONE
    assert game.match.cube_value == 4
    assert game.match.double is True
    assert game.match.game_state == GameState.ON_ROLL
    assert game.match.dice == (0, 0)


def test_nackgammon_drop():
    """Test redouble method"""
    game = Nackgammon()
    game.match.length = 9
    game.match.player = PlayerType.ZERO
    game.match.turn = PlayerType.ZERO

    with pytest.raises(BoardError, match="No double to drop"):
        game.drop()

    game.match.game_state = GameState.ON_ROLL
    game.match.cube_holder = PlayerType.CENTERED

    game.double()
    game.drop()

    assert game.match.player_0_score == 1
    assert game.match.cube_holder == PlayerType.CENTERED
    assert game.match.cube_value == 1
    assert game.match.double is False
    assert game.position.encode() == "4Dl4ADbgOXgANg"
    assert game.match.dice != (0, 0)
    assert game.match.game_state == GameState.ROLLED


def test_nackgammon_plays():
    """Tests the play method"""

    def do_move(game: Nackgammon, arg: str) -> Nackgammon:
        """Make a nackgammon move: move <from> <to> ..."""
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

        game.play(moves)

        return game

    game = Nackgammon()

    game.match.length = 1
    game.match.dice = (1, 2)

    with pytest.raises(
        BoardError,
        match=re.escape("Invalid move sequence: ((20, 19), (20, 18))"),
    ):
        do_move(game, "21 20 21 19")

    game.position = Position(
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
    game = do_move(game, "1 off")
    assert game.match.game_state == GameState.GAME_OVER


def test_nackgammon_multiplier():
    """Tests the multiplier methoc"""
    game = Nackgammon()

    with pytest.raises(
        BoardError,
        match="Checkers are still on the board, what do you resign, single, gammon or backgammon?",
    ):
        game.multiplier()

    game.position = Position(
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
    multiplier = game.multiplier()
    assert multiplier == Resign.BACKGAMMON

    game.position = Position(
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
    multiplier = game.multiplier()
    assert multiplier == Resign.SINGLE_GAME

    game.position = Position(
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
    multiplier = game.multiplier()
    assert multiplier == Resign.BACKGAMMON

    game.position = Position(
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
    multiplier = game.multiplier()
    assert multiplier == Resign.GAMMON


def test_nackgammon_set_player_score(capfd, player0, player1):
    """test the set player sore method"""

    game = Nackgammon()
    game.ref = ""
    game.player0 = Player(PlayerType.ZERO, player0)
    game.player1 = Player(PlayerType.ONE, player1)
    game.match.player_0_score = 5
    game.match.player_1_score = 7

    game.match.player = PlayerType.ZERO
    game.player = game.player1
    board = """ Nackgammon      Position ID: 4Dl4ADbgOXgANg
                 Match ID   : MAgAAFAAOAAA
 +13-14-15-16-17-18------19-20-21-22-23-24-+     O: 
 | X           O    |   | O           X  X |     5 points
 | X           O    |   | O           X  X |
 | X           O    |   | O                |
 | X                |   | O                |     pips: 194
 |                  |   |                  |
v|                  |BAR|                  |     $0 money game (Cube: 1)
 |                  |   |                  |
 | O                |   | X                |     pips: 194
 | O           X    |   | X                |
 | O           X    |   | X           O  O |     
 | O           X    |   | X           O  O |     7 points
 +12-11-10--9--8--7-------6--5--4--3--2--1-+     X: """
    assert str(board) == game.__str__()

    game.match.player = PlayerType.ONE
    game.player = game.player0
    game.match.swap_players()
    game.position.swap_players()

    board = """ Nackgammon      Position ID: 4Dl4ADbgOXgANg
                 Match ID   : MAAAAFAAOAAA
 +13-14-15-16-17-18------19-20-21-22-23-24-+     X: 
 | O           X    |   | X           O  O |     7 points
 | O           X    |   | X           O  O |
 | O           X    |   | X                |
 | O                |   | X                |     pips: 194
 |                  |   |                  |
v|                  |BAR|                  |     $0 money game (Cube: 1)
 |                  |   |                  |
 | X                |   | O                |     pips: 194
 | X           O    |   | O                |
 | X           O    |   | O           X  X |     
 | X           O    |   | O           X  X |     5 points
 +12-11-10--9--8--7-------6--5--4--3--2--1-+     O: """
    assert str(board) == game.__str__()

    game.match.game_state = GameState.ON_ROLL
    board = """ Nackgammon      Position ID: 4Dl4ADbgOXgANg
                 Match ID   : MAUAAFAAOAAA
 +13-14-15-16-17-18------19-20-21-22-23-24-+     X: 
 | O           X    |   | X           O  O |     7 points
 | O           X    |   | X           O  O |
 | O           X    |   | X                |
 | O                |   | X                |     pips: 194
 |                  |   |                  |
v|                  |BAR|                  |     $0 money game (Cube: 1)
 |                  |   |                  |
 | X                |   | O                |     pips: 194
 | X           O    |   | O                |
 | X           O    |   | O           X  X |     On roll
 | X           O    |   | O           X  X |     5 points
 +12-11-10--9--8--7-------6--5--4--3--2--1-+     O: """
    assert str(board) == game.__str__()

    game.match.game_state = GameState.ROLLED
    game.match.dice = (1, 1)
    board = """ Nackgammon      Position ID: 4Dl4ADbgOXgANg
                 Match ID   : MIYEAFAAOAAA
 +13-14-15-16-17-18------19-20-21-22-23-24-+     X: 
 | O           X    |   | X           O  O |     7 points
 | O           X    |   | X           O  O |
 | O           X    |   | X                |
 | O                |   | X                |     pips: 194
 |                  |   |                  |
v|                  |BAR|                  |     $0 money game (Cube: 1)
 |                  |   |                  |
 | X                |   | O                |     pips: 194
 | X           O    |   | O                |
 | X           O    |   | O           X  X |     Rolled (1, 1)
 | X           O    |   | O           X  X |     5 points
 +12-11-10--9--8--7-------6--5--4--3--2--1-+     O: """
    assert str(board) == game.__str__()

    game.match.game_state = GameState.DOUBLED
    board = """ Nackgammon      Position ID: 4Dl4ADbgOXgANg
                 Match ID   : MIcEAFAAOAAA
 +13-14-15-16-17-18------19-20-21-22-23-24-+     X: 
 | O           X    |   | X           O  O |     7 points
 | O           X    |   | X           O  O |
 | O           X    |   | X                |
 | O                |   | X                |     pips: 194
 |                  |   |                  |
v|                  |BAR|                  |     $0 money game (Cube: 1)
 |                  |   |                  |
 | X                |   | O                |     pips: 194
 | X           O    |   | O                |
 | X           O    |   | O           X  X |     Cube offered at 1
 | X           O    |   | O           X  X |     5 points
 +12-11-10--9--8--7-------6--5--4--3--2--1-+     O: """
    assert str(board) == game.__str__()

    game.match.game_state = GameState.RESIGNED
    game.match.resign = Resign.SINGLE_GAME
    board = """ Nackgammon      Position ID: 4Dl4ADbgOXgANg
                 Match ID   : MKMEAFAAOAAA
 +13-14-15-16-17-18------19-20-21-22-23-24-+     X: 
 | O           X    |   | X           O  O |     7 points
 | O           X    |   | X           O  O |
 | O           X    |   | X                |
 | O                |   | X                |     pips: 194
 |                  |   |                  |
v|                  |BAR|                  |     $0 money game (Cube: 1)
 |                  |   |                  |
 | X                |   | O                |     pips: 194
 | X           O    |   | O                |
 | X           O    |   | O           X  X |     Opponent resigns a single
 | X           O    |   | O           X  X |     5 points
 +12-11-10--9--8--7-------6--5--4--3--2--1-+     O: """
    assert str(board) == game.__str__()

    game.match.game_state = GameState.ON_ROLL
    game.match.cube_holder = PlayerType.ONE
    board = """ Nackgammon      Position ID: 4Dl4ADbgOXgANg
                 Match ID   : EKUEAFAAOAAA
 +13-14-15-16-17-18------19-20-21-22-23-24-+     X:  (Cube: 1)
 | O           X    |   | X           O  O |     7 points
 | O           X    |   | X           O  O |
 | O           X    |   | X                |
 | O                |   | X                |     pips: 194
 |                  |   |                  |
v|                  |BAR|                  |     $0 money game (Cube: 1)
 |                  |   |                  |
 | X                |   | O                |     pips: 194
 | X           O    |   | O                |
 | X           O    |   | O           X  X |     On roll
 | X           O    |   | O           X  X |     5 points
 +12-11-10--9--8--7-------6--5--4--3--2--1-+     O: """
    assert str(board) == game.__str__()

    game.position = Position(
        board_points=(
            6,
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
        player_off=0,
        opponent_bar=0,
        opponent_off=0,
    )
    board = """ Nackgammon      Position ID: AAAAfgAAAAAAAA
                 Match ID   : EKUEAFAAOAAA
 +13-14-15-16-17-18------19-20-21-22-23-24-+     X:  (Cube: 1)
 |                  |   |                  |     7 points
 |                  |   |                  |
 |                  |   |                  |
 |                  |   |                  |     pips: 0
 |                  |   |                  |
v|                  |BAR|                  |     $0 money game (Cube: 1)
 |                  |   |                6 |
 |                  |   |                O |     pips: 6
 |                  |   |                O |
 |                  |   |                O |     On roll
 |                  |   |                O |     5 points
 +12-11-10--9--8--7-------6--5--4--3--2--1-+     O: """

    assert str(board) == game.__str__()
