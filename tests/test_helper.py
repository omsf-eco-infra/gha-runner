import pytest
from unittest.mock import mock_open, patch
from gha_runner.helper.workflow_cmds import output, warning, error


def test_output(monkeypatch):
    # Setup mock environment variable
    monkeypatch.setenv("GITHUB_OUTPUT", "mock_output_file")

    mock_file = mock_open()
    with patch("builtins.open", mock_file):
        output("test_name", "test_value")

    mock_file().write.assert_called_once_with("test_name=test_value\n")


def test_warning(capsys):
    warning("Test Title", "Test Message")
    captured = capsys.readouterr()
    assert captured.out == "::warning title=Test Title::Test Message\n"


def test_warning_with_special_chars(capsys):
    warning("Test:Title", "Test,Message")
    captured = capsys.readouterr()
    assert captured.out == "::warning title=Test:Title::Test,Message\n"


def test_error(capsys):
    error("Test Title", "Test Message")
    captured = capsys.readouterr()
    assert captured.out == "::error title=Test Title::Test Message\n"


def test_error_with_special_chars(capsys):
    error("Test:Title", "Test,Message")
    captured = capsys.readouterr()
    assert captured.out == "::error title=Test:Title::Test,Message\n"


def test_output_missing_env_var(monkeypatch):
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    with pytest.raises(KeyError):
        output("test_name", "test_value")
