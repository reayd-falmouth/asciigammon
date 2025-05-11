# tests/modules/test_tutor_manager.py

import pytest
import pygame
from unittest.mock import Mock, patch, call
from pybg.modules.tutor_manager import TutorManager
from pybg.gnubg.match import GameState
from pybg.core.board import Play, Move

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_shell():
    game = Mock()
    game.match.player = "human"
    game.player.player_type = "human"
    game.match.game_state = GameState.ROLLED
    game.match.cube_value = 2
    game.match.resign.phrase = "gammon"
    game.position.to_array.return_value = [0] * 250
    game.generate_plays.return_value = []

    shell = Mock()
    shell.game = game
    shell.settings.get.return_value = 5
    shell.active_module = None

    # ✅ This handles both: with or without a `msg` positional argument
    shell.update_output_text.side_effect = lambda *args, **kwargs: (
        args[0] if args else "OK"
    )

    return shell


@pytest.fixture
def tutor(mock_shell):
    return TutorManager(mock_shell)


def test_cmd_hint_no_game(tutor):
    tutor.shell.game.position = Mock()
    tutor.shell.game.match = None
    tutor.shell.update_output_text.side_effect = lambda msg, show_board=True: msg

    tutor.shell.game = None  # Keeps `cmd_hint()` logic happy
    result = tutor.cmd_hint([])
    assert "no game" in result.lower()


def test_cmd_hint_not_your_turn(tutor):
    tutor.shell.game.match.player = "bot"
    result = tutor.cmd_hint([])
    assert "not your turn" in result.lower()


@pytest.mark.parametrize(
    "state,msg",
    [
        (GameState.RESIGNED, "has offered to resign"),
        (GameState.DOUBLED, "Cube offered"),
        (GameState.ON_ROLL, "Roll, double or resign"),
        (GameState.TAKE, "Double accepted"),
    ],
)
def test_cmd_hint_wrong_state_messages(tutor, state, msg):
    tutor.shell.game.match.game_state = state
    result = tutor.cmd_hint([])
    assert msg.lower() in result.lower()


def test_next_previous_hint(tutor):
    play = Mock()
    play.moves = [Mock(source=0, destination=1)]
    tutor.evaluated_plays = [(0.5, play), (0.4, play)]
    tutor.current_hint_index = 0

    tutor.next_hint()
    assert tutor.current_hint_index == 1

    tutor.previous_hint()
    assert tutor.current_hint_index == 0


def test_exit_hint_mode(tutor):
    tutor.original_position = Mock()
    tutor.exit_hint_mode()
    tutor.shell.update_output_text.assert_called_once()
    assert tutor.original_position is None
    assert tutor.shell.active_module is None


def test_handle_event_not_in_tutor_mode(tutor):
    tutor.shell.active_module = "not_tutor"
    result = tutor.handle_event(Mock(type=pygame.KEYDOWN))
    assert result is None


@pytest.mark.parametrize(
    "key,expected_index",
    [
        (pygame.K_DOWN, 1),
        (pygame.K_UP, 0),
    ],
)
def test_handle_arrow_keys_in_hint_mode(key, expected_index, tutor):
    tutor.shell.active_module = "tutor"
    play = Mock()
    play.moves = [Mock(source=0, destination=1)]
    tutor.evaluated_plays = [(0.9, play), (0.8, play)]
    tutor.current_hint_index = 0

    event = Mock(type=pygame.KEYDOWN, key=key)
    tutor.handle_event(event)
    assert tutor.current_hint_index == expected_index


def test_handle_escape_key_in_hint_mode(tutor):
    tutor.shell.active_module = "tutor"
    tutor.original_position = Mock()
    event = Mock(type=pygame.KEYDOWN, key=pygame.K_ESCAPE)
    tutor.handle_event(event)
    tutor.shell.update_output_text.assert_called()


def test_cmd_tutor_mode_valid(tutor):
    response = tutor.cmd_tutor_mode(["tutor"])
    assert "tutor mode set to" in response.lower()
    assert tutor.tutor_mode == "tutor"


def test_cmd_tutor_mode_invalid(tutor):
    response = tutor.cmd_tutor_mode(["invalid"])
    assert "usage: tutor_mode" in response.lower()


def test_register_returns_expected_commands(tutor):
    commands, _, helptext = tutor.register()
    assert "hint" in commands
    assert "tutor_mode" in commands
    assert "hint" in helptext
