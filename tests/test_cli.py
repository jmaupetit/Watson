"""Tests for the Watson CLI."""

import re
from datetime import datetime, timedelta
from itertools import combinations
from zoneinfo import ZoneInfo

import arrow
import pytest

from watson import cli
from watson.cli import local_tz_info

# Not all ISO-8601 compliant strings are recognized by arrow.get(str)
VALID_DATES_DATA = [
    ("2018", "2018-01-01 00:00:00"),  # years
    ("2018-04", "2018-04-01 00:00:00"),  # calendar dates
    ("2018-04-10", "2018-04-10 00:00:00"),
    ("2018/04/10", "2018-04-10 00:00:00"),
    ("2018.04.10", "2018-04-10 00:00:00"),
    ("2018-4-10", "2018-04-10 00:00:00"),
    ("2018/4/10", "2018-04-10 00:00:00"),
    ("2018.4.10", "2018-04-10 00:00:00"),
    ("20180410", "2018-04-10 00:00:00"),
    ("2018-123", "2018-05-03 00:00:00"),  # ordinal dates
    ("2018-04-10 12:30:43", "2018-04-10 12:30:43"),
    ("2018-04-10T12:30:43", "2018-04-10 12:30:43"),
    ("2018-04-10 12:30:43Z", "2018-04-10 12:30:43"),
    ("2018-04-10 12:30:43.1233", "2018-04-10 12:30:43"),
    ("2018-04-10 12:30:43+03:00", "2018-04-10 12:30:43"),
    ("2018-04-10 12:30:43-07:00", "2018-04-10 12:30:43"),
    ("2018-04-10T12:30:43-07:00", "2018-04-10 12:30:43"),
    ("2018-04-10 12:30", "2018-04-10 12:30:00"),
    ("2018-04-10T12:30", "2018-04-10 12:30:00"),
    ("2018-04-10 12", "2018-04-10 12:00:00"),
    ("2018-04-10T12", "2018-04-10 12:00:00"),
    (
        "14:05:12",
        arrow.now().replace(hour=14, minute=5, second=12).format("YYYY-MM-DD HH:mm:ss"),
    ),
    (
        "14:05",
        arrow.now().replace(hour=14, minute=5, second=0).format("YYYY-MM-DD HH:mm:ss"),
    ),
    ("2018-W08", "2018-02-19 00:00:00"),  # week dates
    ("2018W08", "2018-02-19 00:00:00"),
    ("2018-W08-2", "2018-02-20 00:00:00"),
    ("2018W082", "2018-02-20 00:00:00"),
]

INVALID_DATES_DATA = [
    (" 2018"),
    ("2018 "),
    ("201804"),
    ("18-04-10"),
    ("180410"),  # truncated representation not allowed
    ("hello 2018"),
    ("yesterday"),
    ("tomorrow"),
    ("14:05:12.000"),  # Times alone are not allowed
    ("140512.000"),
    ("140512"),
    ("14.05"),
    ("2018-04-10T"),
    ("2018-04-10T12:30:43."),
]

VALID_TIMES_DATA = [
    ("14:12"),
    ("14:12:43"),
    ("2019-04-10T14:12"),
    ("2019-04-10T14:12:43"),
]


class OutputParser:
    """Helpers to parse Watson CLI output."""

    FRAME_ID_PATTERN = re.compile(r"id: (?P<frame_id>[0-9a-f]+)")

    @staticmethod
    def get_frame_id(output):
        """Extract the frame id from the command output."""
        return OutputParser.FRAME_ID_PATTERN.search(output).group("frame_id")

    @staticmethod
    def get_start_date(watson, output):
        """Get the start date of the frame displayed in the command output."""
        frame_id = OutputParser.get_frame_id(output)
        return watson.frames[frame_id].start.format("YYYY-MM-DD HH:mm:ss")


# watson add


@pytest.mark.parametrize("test_dt,expected", VALID_DATES_DATA)
def test_add_valid_date(runner, watson, test_dt, expected):
    """The add command should accept valid dates."""
    result = runner.invoke(
        cli.add, ["-f", test_dt, "-t", test_dt, "project-name"], obj=watson
    )
    assert result.exit_code == 0
    assert OutputParser.get_start_date(watson, result.output) == expected


@pytest.mark.parametrize("test_dt", INVALID_DATES_DATA)
def test_add_invalid_date(runner, watson, test_dt):
    """The add command should reject invalid dates."""
    result = runner.invoke(
        cli.add, ["-f", test_dt, "-t", test_dt, "project-name"], obj=watson
    )
    assert result.exit_code != 0


# watson aggregate


@pytest.mark.parametrize("test_dt,expected", VALID_DATES_DATA)
def test_aggregate_valid_date(runner, watson, test_dt, expected):
    """The aggregate command should accept valid dates."""
    # This is super fast, because no internal 'report' invocations are made
    result = runner.invoke(cli.aggregate, ["-f", test_dt, "-t", test_dt], obj=watson)
    assert result.exit_code == 0


@pytest.mark.parametrize("test_dt", INVALID_DATES_DATA)
def test_aggregate_invalid_date(runner, watson, test_dt):
    """The aggregate command should reject invalid dates."""
    # This is super fast, because no internal 'report' invocations are made
    result = runner.invoke(cli.aggregate, ["-f", test_dt, "-t", test_dt], obj=watson)
    assert result.exit_code != 0


@pytest.mark.parametrize(
    ("from_dt", "to_dt"),
    [
        # Spring-forward DST (2022-03-27 in Europe/Berlin)
        ("2022-03-21", "2022-03-28"),
        ("2022-03-21 16:16:00", "2022-03-28 16:16:00"),
        # Fall-back DST (2022-10-30 in Europe/Berlin)
        ("2022-10-24", "2022-10-31"),
        ("2022-10-24 16:16:00", "2022-10-31 16:16:00"),
        # Normal week, including later start time than end time
        ("2022-04-04", "2022-04-11"),
        ("2022-04-04 18:00:00", "2022-04-11 08:00:00"),
    ],
)
def test_aggregate_includes_final_day_across_dst(
    runner, watson, mocker, from_dt, to_dt
):
    """The aggregate command should include all calendar days across DST transitions."""
    # Return distinct tzinfo objects per call, matching tz.gettz(None) behavior.
    mocker.patch(
        "watson.cli.local_tz_info",
        side_effect=lambda: ZoneInfo.no_cache("Europe/Berlin"),
    )
    berlin = ZoneInfo("Europe/Berlin")
    start = arrow.get(from_dt).replace(tzinfo=berlin)
    end = arrow.get(to_dt).replace(tzinfo=berlin)
    frame_start = end.replace(hour=16, minute=16, second=0)
    watson.frames.add("github", frame_start, frame_start.shift(minutes=5), ["bug"])

    result = runner.invoke(
        cli.aggregate, ["-G", "-f", from_dt, "-t", to_dt], obj=watson
    )

    assert result.exit_code == 0, result.output
    for i in range((end.date() - start.date()).days + 1):
        day_label = start.shift(days=i).format("ddd DD MMMM YYYY")
        assert day_label in result.output
    assert f"{end.format('ddd DD MMMM YYYY')} - 05m 00s" in result.output
    assert "github - 05m 00s" in result.output


# watson log


@pytest.mark.parametrize("cmd", [cli.aggregate, cli.log, cli.report])
def test_incompatible_options(runner, watson, cmd):
    """Mutually exclusive options should not be used together."""
    name_interval_options = ["--" + s for s in cli._SHORTCUT_OPTIONS]
    for opt1, opt2 in combinations(name_interval_options, 2):
        result = runner.invoke(cmd, [opt1, opt2], obj=watson)
        assert result.exit_code != 0


@pytest.mark.parametrize("test_dt,expected", VALID_DATES_DATA)
def test_log_valid_date(runner, watson, test_dt, expected):
    """The log command should accept valid dates."""
    result = runner.invoke(cli.log, ["-f", test_dt, "-t", test_dt], obj=watson)
    assert result.exit_code == 0


@pytest.mark.parametrize("test_dt", INVALID_DATES_DATA)
def test_log_invalid_date(runner, watson, test_dt):
    """The log command should reject invalid dates."""
    result = runner.invoke(cli.log, ["-f", test_dt, "-t", test_dt], obj=watson)
    assert result.exit_code != 0


# watson report


@pytest.mark.parametrize("test_dt,expected", VALID_DATES_DATA)
def test_report_valid_date(runner, watson, test_dt, expected):
    """The report command should accept valid dates."""
    result = runner.invoke(cli.report, ["-f", test_dt, "-t", test_dt], obj=watson)
    assert result.exit_code == 0


@pytest.mark.parametrize("test_dt", INVALID_DATES_DATA)
def test_report_invalid_date(runner, watson, test_dt):
    """The report command should reject invalid dates."""
    result = runner.invoke(cli.report, ["-f", test_dt, "-t", test_dt], obj=watson)
    assert result.exit_code != 0


# watson stop


@pytest.mark.parametrize("at_dt", VALID_TIMES_DATA)
def test_stop_valid_time(runner, watson, mocker, at_dt):
    """The stop command should accept a valid --at time."""
    mocker.patch("arrow.arrow.dt_datetime", wraps=datetime)
    start_dt = datetime(2019, 4, 10, 14, 0, 0, tzinfo=local_tz_info())
    arrow.arrow.dt_datetime.now.return_value = start_dt
    result = runner.invoke(cli.start, ["a-project"], obj=watson)
    assert result.exit_code == 0
    # Simulate one hour has elapsed, so that 'at_dt' is older than now()
    # but newer than the start date.
    arrow.arrow.dt_datetime.now.return_value = start_dt + timedelta(hours=1)
    result = runner.invoke(cli.stop, ["--at", at_dt], obj=watson)
    assert result.exit_code == 0


# watson start


@pytest.mark.parametrize("at_dt", VALID_TIMES_DATA)
def test_start_valid_time(runner, watson, mocker, at_dt):
    """The start command should accept a valid --at time."""
    # Simulate a start date so that 'at_dt' is older than now().
    mocker.patch("arrow.arrow.dt_datetime", wraps=datetime)
    start_dt = datetime(2019, 4, 10, 14, 0, 0, tzinfo=local_tz_info())
    arrow.arrow.dt_datetime.now.return_value = start_dt + timedelta(hours=1)
    result = runner.invoke(cli.start, ["a-project", "--at", at_dt], obj=watson)
    assert result.exit_code == 0


# watson start new task in past, with existing task


def test_start_existing_frame_stopped(runner, watson, mocker):
    """Starting a project should stop the current one (stop_on_start)."""
    # Simulate a start date so that 'at_dt' is older than now().
    watson.config.set("options", "stop_on_start", "true")
    mocker.patch("arrow.arrow.dt_datetime", wraps=datetime)
    start_dt = datetime(2019, 4, 10, 15, 0, 0, tzinfo=local_tz_info())
    arrow.arrow.dt_datetime.now.return_value = start_dt
    runner.invoke(
        cli.start,
        ["a-project", "--at", "14:10"],
        obj=watson,
    )

    result = runner.invoke(
        cli.start,
        ["b-project", "--at", "14:15"],
        obj=watson,
    )
    assert result.exit_code == 0, result.stdout

    frame_id = OutputParser.get_frame_id(result.output)
    assert watson.frames[frame_id].project == "a-project"
    assert watson.current["project"] == "b-project"


# watson restart


@pytest.mark.parametrize("at_dt", VALID_TIMES_DATA)
def test_restart_valid_time(runner, watson, mocker, at_dt):
    """The restart command should accept a valid --at time."""
    # Create a previous entry the same as in `test_stop_valid_time`
    mocker.patch("arrow.arrow.dt_datetime", wraps=datetime)
    start_dt = datetime(2019, 4, 10, 14, 0, 0, tzinfo=local_tz_info())
    arrow.arrow.dt_datetime.now.return_value = start_dt
    result = runner.invoke(cli.start, ["a-project"], obj=watson)
    # Simulate one hour has elapsed, so that 'at_dt' is older than now()
    # but newer than the start date.
    arrow.arrow.dt_datetime.now.return_value = start_dt + timedelta(hours=1)
    result = runner.invoke(cli.stop, ["--at", at_dt], obj=watson)
    # Test that the last frame can be restarted
    result = runner.invoke(cli.restart, ["--at", at_dt], obj=watson)
    assert result.exit_code == 0
