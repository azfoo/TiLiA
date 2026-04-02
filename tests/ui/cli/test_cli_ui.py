from unittest.mock import patch

import pytest


class TestCLI:
    def test_wrong_argument(self, cli, tilia_errors):
        cli.parse_and_run("nonsense")

        tilia_errors.assert_error()
        tilia_errors.assert_in_error_message("nonsense")

    PARSE_COMMAND_CASES = [
        ("spaced args", ["spaced", "args"]),
        ('"spaced args"', ["spaced args"]),
        ('"spaced args" and more', ["spaced args", "and", "more"]),
        ('"three spaced args"', ["three spaced args"]),
        ('"three spaced args" and more', ["three spaced args", "and", "more"]),
        (
            'surrounded "quoted args" surrounded',
            ["surrounded", "quoted args", "surrounded"],
        ),
        ('"unfinished', None),
        ('"unfinished and more', None),
        ('not started"', None),
        ('notstarted"', None),
        ('notstarted" and more', None),
        ('this has notstarted"', None),
        ('"onestring"', ["onestring"]),
        ("trailing space ", ["trailing", "space"]),
        ("trailing spaces     ", ["trailing", "spaces"]),
    ]

    @pytest.mark.parametrize("command,result", PARSE_COMMAND_CASES)
    def test_parse_command(self, cli, command, result):

        assert cli.parse_command(command) == result

    def test_toggle_verbose(self, cli):
        with patch("tilia.log.logger.on_settings_updated") as logger:
            cli.parse_and_run("metadata set-media-length 60")
            cli.parse_and_run("-v metadata set-media-length 60")
            cli.parse_and_run("--no-v metadata set-media-length 60")

        assert logger._mock_call_count == 2
