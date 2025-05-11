# test_game_module.py

import pytest
from unittest.mock import MagicMock
from pybg.modules.game_module import GameModule
from pybg.core.board import BoardError

pytestmark = pytest.mark.unit


class DummyGame:
    def __init__(self):
        self.play = MagicMock()
        self.generate_plays = MagicMock(return_value=[])
        self.match = MagicMock()
        self.position = MagicMock()
        self.valid_actions = MagicMock(return_value=["move", "double"])
        self.action_mask = MagicMock(return_value=[0, 1, 1])
        self.roll = MagicMock()
        self.double = MagicMock()
        self.take = MagicMock()
        self.drop = MagicMock()
        self.accept = MagicMock()
        self.reject = MagicMock()
        self.resign = MagicMock()
        self.match.turn.name = "Player 1"
        self.match.dice = [3, 5]
        self.match.length = 1
        self.match.game_state = MagicMock()


class DummyShell:
    def __init__(self):
        self.game = DummyGame()
        self.settings = {
            "variant": "backgammon",
            "match_length": 5,
            "game_mode": "match",
            "autodoubles": False,
            "jacoby": False,
            "player_agent": "random",
            "opponent_agent": "random",
            "hint_top_n": 3,
        }
        self.sound_manager = MagicMock()
        self.sound_manager.play_sound = MagicMock()
        self.history_module = MagicMock()
        self.history_module.get_current_match_ref = MagicMock(return_value="ref")
        self.log_current_state = MagicMock()
        self.update_output_text = MagicMock(return_value="Updated")
        self.guard_game = MagicMock()


@pytest.fixture
def module():
    shell = DummyShell()
    return GameModule(shell)


def test_category():
    assert GameModule.category == "Game"


def test_guard_game_raises_if_no_game():
    mod = GameModule(MagicMock(game=None))
    with pytest.raises(ValueError):
        mod.guard_game()


def test_cmd_show_returns_text(module):
    result = module.cmd_show([])
    assert result == "Updated"


def test_cmd_roll_triggers_roll(module):
    result = module.cmd_roll([])
    module.shell.game.roll.assert_called_once()
    assert result == "Updated"


def test_cmd_move_invalid_format(module):
    with pytest.raises(BoardError):
        module.parse_moves(["invalid"])


def test_cmd_move_invalid_numbers(module):
    module.shell.game.generate_plays = MagicMock(return_value=[])
    with pytest.raises(BoardError):
        module.parse_moves(["x/y"])


def test_cmd_double_executes_command(module):
    result = module.cmd_double([])
    assert result == "Updated"
    module.shell.game.double.assert_called_once()


def test_register_returns_expected_keys(module):
    commands, _, help_texts = module.register()
    expected_keys = {
        "new",
        "debug",
        "roll",
        "move",
        "double",
        "take",
        "drop",
        "accept",
        "reject",
        "resign",
        "show",
    }
    assert expected_keys.issubset(commands.keys())
    assert expected_keys.issubset(help_texts.keys())
