# tests/modules/test_history_manager.py

import pytest
import tempfile
import os
import json
from unittest.mock import Mock, patch
from pybg.modules.history_manager import HistoryManager

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_shell():
    shell = Mock()
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
    history_manager.record_move("match1", "gameid:matchid", "test move")
    assert "match1" in history_manager.matches
    assert len(history_manager.matches["match1"]["moves"]) == 1


def test_get_current_match_ref_returns_empty(history_manager):
    assert history_manager.get_current_match_ref() == ""


# def test_get_current_state_empty(history_manager):
#     assert history_manager.get_current_state() == ([""], "")
#
#
# def test_get_current_state_with_move(history_manager):
#     history_manager.record_move("match1", "gameid:matchid", "msg")
#     history_manager.current_match_index = 0
#     assert history_manager.get_current_state() == (["gameid"], "msg")


def test_update_view_to_current_move(history_manager):
    history_manager.record_move("match1", "position:match", "msg")
    result = history_manager.update_view_to_current_move()
    assert result == "LOG for Match match1 (Moves: 1):\n\n>  1. msg"
    history_manager.shell.update_output_text.assert_called_once()


def test_next_move_advances_index(history_manager):
    history_manager.record_move("match1", "a:b", "move1")
    history_manager.record_move("match1", "c:d", "move2")
    history_manager.next_move()
    assert history_manager.current_move_index == 1


def test_previous_move(history_manager):
    history_manager.record_move("match1", "a:b", "m1")
    history_manager.record_move("match1", "c:d", "m2")
    history_manager.current_move_index = 1
    history_manager.previous_move()
    assert history_manager.current_move_index == 0


def test_next_match(history_manager):
    history_manager.record_move("m1", "g1", "")
    history_manager.record_move("m2", "g2", "")
    history_manager.current_match_index = 0
    history_manager.next_match()
    assert history_manager.current_match_index == 1


def test_previous_match_does_not_underflow(history_manager):
    history_manager.record_move("m1", "g1", "")
    history_manager.current_match_index = 0
    history_manager.previous_match()
    assert history_manager.current_match_index == 0


def test_delete_current_match(history_manager):
    history_manager.record_move("m1", "g1", "")
    history_manager.delete_current_match()
    assert "m1" not in history_manager.matches


def test_cmd_history_with_ref(history_manager):
    history_manager.record_move("match1", "pos:match", "msg")
    history_manager.shell.game.ref = "match1"
    response = history_manager.cmd_history([])
    assert response == "LOG for Match match1 (Moves: 1):\n\n>  1. msg"


def test_cmd_history_empty(history_manager):
    history_manager.match_refs.clear()
    response = history_manager.cmd_history([])
    assert "No match history available" in response


def test_cmd_goto_valid(history_manager):
    history_manager.record_move("match1", "pos:match", "msg")
    response = history_manager.cmd_goto(["1"])
    assert response is None  # load_from_file called


def test_cmd_goto_invalid_number(history_manager):
    response = history_manager.cmd_goto(["not_a_number"])
    assert "Usage: goto <move_number>" in response


def test_cmd_goto_out_of_range(history_manager):
    history_manager.record_move("match1", "pos:match", "msg")
    response = history_manager.cmd_goto(["10"])
    assert "Invalid move number" in response


def test_cmd_delete_history(history_manager):
    history_manager.record_move("m1", "g1", "")
    result = history_manager.cmd_delete_history([])
    history_manager.shell.update_output_text.assert_called_with(
        "Deleted current match."
    )


#
# def test_cmd_save_history_writes_file(mock_shell):
#     with tempfile.TemporaryDirectory() as tmpdir:
#         fake_path = os.path.join(tmpdir, "history.json")
#
#         with patch("pybg.modules.history_manager.ASSETS_DIR", tmpdir):
#             h = HistoryManager(mock_shell)
#             h.match_history_path = fake_path  # ✅ must come before record_move()
#             h.record_move("m1", "pos:match", "msg")
#             result = h.cmd_save_history([])
#
#             assert os.path.exists(fake_path)
#             with open(fake_path) as f:
#                 data = json.load(f)
#             assert "m1" in data["matches"]


def test_handle_event_game_event():
    shell = Mock()
    shell.active_module = None
    h = HistoryManager(shell)
    event = Mock()
    event.type = 1000  # EVENT_GAME
    event.dict = {"match_ref": "m1", "game_id": "pos:match", "message": "msg"}

    h.handle_event(event)
    assert "m1" in h.matches
    assert h.matches["m1"]["moves"][0]["message"] == ""


def test_register_returns_expected_structure(history_manager):
    commands, _, helptext = history_manager.register()
    assert "history" in commands
    assert "goto" in commands
    assert "delete_history" in commands
    assert "save_history" in commands
    assert "goto" in helptext
