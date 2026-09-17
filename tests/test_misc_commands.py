"""Tests for choose, 8ball, help, uptime, and the formatting utilities."""

import asyncio
import re

from commands.choose import choose
from commands.eightball import eightball, RESPONSES
from commands.help import help_cmd
from commands.uptime import uptime
from utils import format_duration_long, format_track_time, youtube_search_query
from conftest import make_ctx


# --- utils ---

def test_youtube_search_query_strips_asterisks():
    # Censored titles from streaming services break YouTube search verbatim
    assert youtube_search_query("Ninajirachi F**k My Computer") == "ytsearch1:Ninajirachi F k My Computer"


def test_youtube_search_query_plain():
    assert youtube_search_query("aespa whiplash") == "ytsearch1:aespa whiplash"
    assert youtube_search_query("aespa whiplash", results=5) == "ytsearch5:aespa whiplash"

def test_format_duration_long():
    assert format_duration_long(93784) == "1d 2h 3m 4s"
    assert format_duration_long(3600) == "1h"
    assert format_duration_long(5400) == "1h 30m"
    assert format_duration_long(59) == "59s"
    assert format_duration_long(0) == "0s"
    assert format_duration_long(-5) == "0s"


def test_format_track_time():
    assert format_track_time(151) == "2:31"
    assert format_track_time(3723) == "1:02:03"
    assert format_track_time(0) == "0:00"


# --- choose ---

def test_choose_pipes():
    response = asyncio.run(choose(make_ctx(), "pizza | tacos | sushi"))
    assert any(option in response for option in ("pizza", "tacos", "sushi"))


def test_choose_commas():
    response = asyncio.run(choose(make_ctx(), "red, green, blue"))
    assert any(option in response for option in ("red", "green", "blue"))


def test_choose_spaces():
    response = asyncio.run(choose(make_ctx(), "heads tails"))
    assert "heads" in response or "tails" in response


def test_choose_needs_two_options():
    assert "at least two" in asyncio.run(choose(make_ctx(), "onlyone"))
    assert "at least two" in asyncio.run(choose(make_ctx(), ""))


def test_choose_pipes_take_precedence_over_spaces():
    # "new york | los angeles" is 2 options, not 4
    response = asyncio.run(choose(make_ctx(), "new york | los angeles"))
    assert response in ("i choose: **new york**", "i choose: **los angeles**")


# --- 8ball ---

def test_eightball_answers():
    response = asyncio.run(eightball(make_ctx(), "will it work?"))
    assert any(answer in response for answer in RESPONSES)


def test_eightball_needs_question():
    assert "ask me a question" in asyncio.run(eightball(make_ctx(), ""))


# --- help ---

def test_help_lists_commands():
    response = asyncio.run(help_cmd(make_ctx(), ""))
    for cmd in ("play", "shuffle", "reminders", "8ball", "loop"):
        assert cmd in response


def test_help_detail():
    response = asyncio.run(help_cmd(make_ctx(), "play"))
    assert "Usage" in response
    assert "@Anna play" in response
    # Developer-facing sections are stripped
    assert "Args:" not in response
    # No stale > prefix style anywhere in the help text
    assert ">play" not in response


def test_help_detail_strips_angle_bracket():
    response = asyncio.run(help_cmd(make_ctx(), ">remind"))
    assert "Usage" in response


def test_help_unknown():
    assert "unknown command" in asyncio.run(help_cmd(make_ctx(), "frobnicate"))


# --- uptime ---

def test_uptime_format():
    response = asyncio.run(uptime(make_ctx(), ""))
    assert re.fullmatch(r"Uptime: (\d+d )?(\d+h )?(\d+m )?\d+s", response)


# --- registry sanity ---

def test_registry_has_all_new_commands():
    from commands import registry
    for name in ("playnext", "remove", "move", "loop", "volume", "autoplay",
                 "saveq", "loadq", "playlists", "delq", "reminders", "cancel",
                 "choose", "8ball", "shuffle"):
        assert name in registry, f"missing command: {name}"
