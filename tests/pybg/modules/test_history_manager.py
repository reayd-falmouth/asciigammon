# tests/modules/test_history_manager.py

import pytest
from unittest.mock import Mock, patch

from pybg.modules.history_manager import HistoryManager
from pybg.variants.backgammon import STARTING_POSITION_ID, STARTING_MATCH_ID

pytestmark = pytest.mark.unit

GAME_ID = f"{STARTING_POSITION_ID}:{STARTING_MATCH_ID}"


@pytest.fixture
def mock_shell():
    shell = Mock()
    shell.settings = {
        "variant": "backgammon",
        "match_length": 1,
        "game_mode": "match",
        "autodoubles": False,
        "jacoby": False,
        "player_agent": "human",
        "opponent_agent": "human",
    }
    shell.game.ref = "match1"
    shell.game.position.decode.return_value = "decoded_position"
    shell.game.match.decode.return_value = "decoded_match"
    shell.update_output_text.side_effect = lambda text, show_board=True: text
    shell.active_module = None
    return shell


@pytest.fixture
def history_manager(mock_shell):
    # Patch save/load to prevent file I/O
    with patch.object(HistoryManager, "load_from_file"), patch.object(
        HistoryManager, "save_to_file"
    ):
        return HistoryManager(mock_shell)


def test_record_move_creates_new_match(history_manager):
    history_manager.record_move("match1", GAME_ID, "test move")
    assert "match1" in history_manager.matches
    assert len(history_manager.matches["match1"]["moves"]) == 1


def test_get_current_match_ref_returns_empty(history_manager):
    assert history_manager.get_current_match_ref() == ""


def test_update_view_to_current_move(history_manager):
    history_manager.record_move("match1", GAME_ID, "msg")
    result = history_manager.update_view_to_current_move()
    assert "LOG for Match match1 (Moves: 1):" in result
    assert ">  1. msg" in result
    history_manager.shell.update_output_text.assert_called_once()


def test_next_move_advances_index(history_manager):
    history_manager.record_move("match1", GAME_ID, "move1")
    history_manager.record_move("match1", GAME_ID, "move2")
    history_manager.next_move()
    assert history_manager.current_move_index == 1


def test_previous_move(history_manager):
    history_manager.record_move("match1", GAME_ID, "m1")
    history_manager.record_move("match1", GAME_ID, "m2")
    history_manager.current_move_index = 1
    history_manager.previous_move()
    assert history_manager.current_move_index == 0


def test_next_match(history_manager):
    history_manager.record_move("m1", GAME_ID, "")
    history_manager.record_move("m2", GAME_ID, "")
    history_manager.current_match_index = 0
    history_manager.next_match()
    assert history_manager.current_match_index == 1


def test_previous_match_does_not_underflow(history_manager):
    history_manager.record_move("m1", GAME_ID, "")
    history_manager.current_match_index = 0
    history_manager.previous_match()
    assert history_manager.current_match_index == 0


def test_delete_current_match(history_manager):
    history_manager.record_move("m1", GAME_ID, "")
    history_manager.delete_current_match()
    assert "m1" not in history_manager.matches


def test_cmd_history_with_ref(history_manager):
    history_manager.record_move("match1", GAME_ID, "msg")
    history_manager.shell.game.ref = "match1"
    response = history_manager.cmd_history([])
    assert "LOG for Match match1 (Moves: 1):" in response
    assert ">  1. msg" in response


def test_cmd_history_empty(history_manager):
    history_manager.match_refs.clear()
    response = history_manager.cmd_history([])
    assert "No match history available" in response


def test_handle_event_game_event():
    shell = Mock()
    shell.settings = {
        "variant": "backgammon",
        "match_length": 1,
        "game_mode": "match",
        "autodoubles": False,
        "jacoby": False,
        "player_agent": "human",
        "opponent_agent": "human",
    }
    shell.active_module = None
    shell.update_output_text = lambda text, show_board=True: text
    h = HistoryManager(shell)
    event = Mock()
    event.type = 1000  # EVENT_GAME
    event.dict = {"match_ref": "match1", "game_id": GAME_ID, "message": "msg"}

    h.handle_event(event)
    assert "match1" in h.matches
    assert h.matches["match1"]["moves"][0]["message"] == "msg"


def test_register_returns_expected_structure(history_manager):
    commands, _, helptext = history_manager.register()
    assert "history" in commands
    assert "play" in commands
    assert "delete" in commands
    assert "clear" in commands
    assert "export" in commands
    assert "history" in helptext
    assert "delete" in helptext
    assert "play" in helptext
