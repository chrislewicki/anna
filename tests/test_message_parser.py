"""Tests for message parsing, including the passive-mention word boundary."""

from message_parser import parse_message

BOT_ID = 5555
ROLE_IDS = [7777]


def parse(content, **kwargs):
    return parse_message(content, BOT_ID, ROLE_IDS, **kwargs)


def test_passive_mention_mid_sentence():
    assert parse("i heard anna is a bot").is_passive_mention


def test_passive_mention_at_start():
    assert parse("anna? are you there").is_passive_mention


def test_passive_mention_at_end():
    assert parse("thanks anna").is_passive_mention


def test_passive_mention_bare_word():
    assert parse("anna").is_passive_mention


def test_passive_mention_case_insensitive():
    assert parse("Anna!").is_passive_mention


def test_no_passive_mention_inside_word():
    assert not parse("annapolis is nice").is_passive_mention
    assert not parse("i ate a banana").is_passive_mention


def test_direct_mention_parses_command():
    parsed = parse(f"<@{BOT_ID}> ping")
    assert parsed.is_bot_mentioned
    assert parsed.is_command
    assert parsed.clean_prompt == "ping"


def test_role_mention_triggers():
    parsed = parse(f"<@&{ROLE_IDS[0]}> play something")
    assert parsed.is_bot_mentioned
    assert parsed.clean_prompt == "play something"


def test_reply_to_bot_counts_as_mention():
    parsed = parse("skip", referenced_message_author_id=BOT_ID)
    assert parsed.is_bot_mentioned


def test_unrelated_message_ignored():
    parsed = parse("just chatting about stuff")
    assert not parsed.is_bot_mentioned
    assert not parsed.is_command
