# tests/modules/test_help_module.py

import pytest
from unittest.mock import Mock
from pybg.modules.help_module import HelpModule

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_shell():
    shell = Mock()
    shell.help.get_help.side_effect = lambda arg=None: f"help: {arg or 'all'}"
    return shell


@pytest.fixture
def help_module(mock_shell):
    return HelpModule(mock_shell)


def test_cmd_help_no_args(help_module):
    result = help_module.cmd_help([])
    assert result == "help: all"
    help_module.shell.help.get_help.assert_called_once_with()


def test_cmd_help_with_args(help_module):
    result = help_module.cmd_help(["move"])
    assert result == "help: move"
    help_module.shell.help.get_help.assert_called_with("move")


def test_cmd_quit_triggers_shell_quit(help_module):
    help_module.cmd_quit([])
    help_module.shell.quit.assert_called_once()


def test_register_returns_expected_commands(help_module):
    commands, _, descriptions = help_module.register()
    assert set(commands.keys()) == {"help", "exit", "quit"}
    assert "Show the help menu" in descriptions["help"]
    assert "Exit the application" in descriptions["exit"]
