"""Unit tests for CLI output using capsys fixture."""

import pytest
import json

# Assuming CLI module exists at src/cli.py
from src.cli import main


class TestCLIProgressOutput:
    """Test CLI progress indicators and status messages."""

    def test_verbose_mode_shows_progress(self, capsys, mocker):
        """
        Verify: Verbose mode displays progress indicators

        User Story: As a user running long tasks, I want to see progress
        """
        args = ["--verbose", "--task", "long-running-task"]

        with mocker.patch('sys.argv', ['cli'] + args):
            main()

        captured = capsys.readouterr()

        # Check stdout contains progress indicators
        assert "Processing" in captured.out
        assert "1/10" in captured.out or "10%" in captured.out
        assert "✓" in captured.out or "Complete" in captured.out

        # Verify nothing in stderr (no errors)
        assert len(captured.err) == 0

    def test_quiet_mode_suppresses_progress(self, capsys, mocker):
        """
        Verify: Quiet mode only shows final result

        User Story: As a user in scripts, I want minimal output
        """
        args = ["--quiet", "--task", "quick-task"]

        with mocker.patch('sys.argv', ['cli'] + args):
            main()

        captured = capsys.readouterr()

        # Should only have final result, no progress
        assert "Processing" not in captured.out
        assert "%" not in captured.out

        # Should have result
        assert len(captured.out) > 0  # Some output
        assert len(captured.out.split('\n')) <= 3  # Minimal lines


class TestCLIErrorMessages:
    """Test CLI error handling and stderr output."""

    def test_error_messages_to_stderr(self, capsys, mocker):
        """
        Verify: Errors go to stderr with proper formatting

        Shell convention: Errors to stderr, normal output to stdout
        """
        args = ["--config", "nonexistent.json"]

        with mocker.patch('sys.argv', ['cli'] + args):
            with pytest.raises(SystemExit) as exc_info:
                main()

        captured = capsys.readouterr()

        # Error should be in stderr
        assert "ERROR:" in captured.err or "Error:" in captured.err
        assert "nonexistent.json" in captured.err

        # stdout should be empty
        assert len(captured.out) == 0

        # Exit code should be non-zero
        assert exc_info.value.code != 0

    def test_error_formatting_is_readable(self, capsys, mocker):
        """
        Verify: Error messages are user-friendly, not stack traces

        User Experience: Errors should guide users, not overwhelm
        """
        args = ["--temperature", "999"]  # Invalid value

        with mocker.patch('sys.argv', ['cli'] + args):
            with pytest.raises(SystemExit):
                main()

        captured = capsys.readouterr()

        # Should have user-friendly message
        assert "temperature" in captured.err.lower()
        assert "valid range" in captured.err.lower() or "0.0 to 2.0" in captured.err

        # Should NOT have full stack trace (unless --debug)
        assert "Traceback" not in captured.err
        assert "line " not in captured.err


class TestCLIOutputFormatting:
    """Test CLI output formatting options."""

    def test_json_output_is_valid(self, capsys, mocker):
        """
        Verify: --json flag produces parseable JSON

        Integration: Scripts need to parse output
        """
        args = ["--json", "--task", "test"]

        with mocker.patch('sys.argv', ['cli'] + args):
            main()

        captured = capsys.readouterr()

        # Should be valid JSON
        data = json.loads(captured.out)  # Raises if invalid

        # Verify structure
        assert "status" in data
        assert "result" in data or "error" in data

        # Verify no extra output
        assert captured.err == ""

    def test_help_text_output(self, capsys, mocker):
        """
        Verify: --help displays usage information to stdout
        """
        args = ["--help"]

        with mocker.patch('sys.argv', ['cli'] + args):
            with pytest.raises(SystemExit):  # help typically exits
                main()

        captured = capsys.readouterr()

        # Help should be in stdout
        assert "usage:" in captured.out.lower() or "Usage:" in captured.out
        assert "--help" in captured.out or "-h" in captured.out

        # No errors
        assert len(captured.err) == 0

    def test_version_output(self, capsys, mocker):
        """
        Verify: --version displays version information
        """
        args = ["--version"]

        with mocker.patch('sys.argv', ['cli'] + args):
            with pytest.raises(SystemExit):  # version typically exits
                main()

        captured = capsys.readouterr()

        # Version should be in stdout
        assert len(captured.out.strip()) > 0  # Some version info
        assert "version" in captured.out.lower() or any(char.isdigit() for char in captured.out)

        # No errors
        assert len(captured.err) == 0