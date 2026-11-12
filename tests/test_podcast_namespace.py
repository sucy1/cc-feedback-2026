from __future__ import annotations

import feedparser

PODCAST_NS = "https://podcastindex.org/namespace/1.0"


def _parse_item(item_xml: str, channel_xml: str = "") -> feedparser.FeedParserDict:
    """Wrap item-level XML in a minimal RSS 2.0 feed and parse it."""
    xml = f"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:podcast="{PODCAST_NS}">
  <channel>
    <title>Test feed</title>
    {channel_xml}
    <item>
      <title>Test episode</title>
      {item_xml}
    </item>
  </channel>
</rss>
"""
    return feedparser.parse(xml)


def _parse_channel(channel_xml: str) -> feedparser.FeedParserDict:
    xml = f"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:podcast="{PODCAST_NS}">
  <channel>
    <title>Test feed</title>
    {channel_xml}
  </channel>
</rss>
"""
    return feedparser.parse(xml)


def test_repeated_entry_elements_are_lists_in_document_order():
    result = _parse_item(
        """
        <podcast:transcript url="https://e.com/1.vtt" type="text/vtt"/>
        <podcast:transcript url="https://e.com/1.json" type="application/json"/>
        <podcast:person role="host" href="https://e.com/h">张三</podcast:person>
        <podcast:person role="guest">李四</podcast:person>
        <podcast:soundbite startTime="12.5" duration="30">开场</podcast:soundbite>
        <podcast:soundbite startTime="55.2" duration="20">结尾</podcast:soundbite>
        """
    )
    entry = result.entries[0]

    assert entry["podcast_transcript"] == [
        {"url": "https://e.com/1.vtt", "type": "text/vtt"},
        {"url": "https://e.com/1.json", "type": "application/json"},
    ]
    assert entry["podcast_person"] == [
        {"role": "host", "href": "https://e.com/h", "name": "张三"},
        {"role": "guest", "name": "李四"},
    ]
    assert entry["podcast_soundbite"] == [
        {"start_time": 12.5, "duration": 30.0, "title": "开场"},
        {"start_time": 55.2, "duration": 20.0, "title": "结尾"},
    ]


def test_single_entry_element_is_still_a_list():
    result = _parse_item(
        '<podcast:transcript url="https://e.com/1.vtt" type="text/vtt"/>'
    )
    assert result.entries[0]["podcast_transcript"] == [
        {"url": "https://e.com/1.vtt", "type": "text/vtt"}
    ]


def test_missing_entry_elements_have_no_key():
    result = _parse_item("")
    entry = result.entries[0]
    assert "podcast_transcript" not in entry
    assert "podcast_person" not in entry
    assert "podcast_soundbite" not in entry


def test_person_name_and_optional_attributes():
    result = _parse_item(
        """
        <podcast:person role="host" href="/relative/path">张三</podcast:person>
        <podcast:person>李四</podcast:person>
        """
    )
    people = result.entries[0]["podcast_person"]

    assert people == [
        {"role": "host", "href": "/relative/path", "name": "张三"},
        {"name": "李四"},
    ]
    # href is kept exactly as written; no domain is prepended.
    assert people[0]["href"] == "/relative/path"


def test_soundbite_title_and_numeric_values():
    result = _parse_item(
        '<podcast:soundbite startTime="12.5" duration="30">开场</podcast:soundbite>'
    )
    (soundbite,) = result.entries[0]["podcast_soundbite"]

    assert soundbite["title"] == "开场"
    assert soundbite["start_time"] == 12.5
    assert soundbite["duration"] == 30.0
    assert isinstance(soundbite["start_time"], float)
    assert isinstance(soundbite["duration"], float)
    assert "starttime" not in soundbite


def test_value_includes_recipients():
    result = _parse_item(
        """
        <podcast:value type="lightning" method="keysend" suggested="0.0000000500">
          <podcast:valueRecipient name="张三" type="node" address="03abc" split="95" fee="true"/>
          <podcast:valueRecipient name="李四" type="node" address="03def" split="5" fee="false"/>
        </podcast:value>
        """
    )
    value = result.entries[0]["podcast_value"]

    assert value == {
        "type": "lightning",
        "method": "keysend",
        "suggested": "0.0000000500",
        "recipients": [
            {
                "name": "张三",
                "type": "node",
                "address": "03abc",
                "split": 95,
                "fee": True,
            },
            {
                "name": "李四",
                "type": "node",
                "address": "03def",
                "split": 5,
                "fee": False,
            },
        ],
    }
    assert isinstance(value["recipients"][0]["split"], int)
    assert value["recipients"][1]["fee"] is False


def test_feed_level_podcast_elements_remain_single_values():
    result = _parse_channel(
        """
        <podcast:id value="123"/>
        <podcast:location geo="geo:1,2" osm="W1">Somewhere</podcast:location>
        <podcast:guid>abc-guid</podcast:guid>
        <podcast:medium>podcast</podcast:medium>
        <podcast:locked owner="a@b" value="yes"/>
        """
    )
    feed = result.feed

    assert feed["podcast_id"] == {"value": "123"}
    assert feed["podcast_location"] == {"geo": "geo:1,2", "osm": "W1"}
    assert feed["podcast_guid"] == "abc-guid"
    assert feed["podcast_medium"] == "podcast"
    assert feed["podcast_locked"] == {"owner": "a@b", "value": "yes"}
    for key in (
        "podcast_id",
        "podcast_location",
        "podcast_guid",
        "podcast_medium",
        "podcast_locked",
    ):
        assert not isinstance(feed[key], list)


def test_loose_parser_supports_podcast_namespace(use_loose_parser):
    result = _parse_item(
        """
        <podcast:transcript url="https://e.com/1.vtt" type="text/vtt"/>
        <podcast:person role="host" href="/h">张三</podcast:person>
        <podcast:soundbite startTime="12.5" duration="30">开场</podcast:soundbite>
        <podcast:value type="lightning" method="keysend">
          <podcast:valueRecipient name="李四" type="node" address="03def" split="5" fee="false"/>
        </podcast:value>
        """
    )
    entry = result.entries[0]

    assert entry["podcast_transcript"] == [
        {"url": "https://e.com/1.vtt", "type": "text/vtt"}
    ]
    assert entry["podcast_person"] == [
        {"role": "host", "href": "/h", "name": "张三"}
    ]
    assert entry["podcast_soundbite"] == [
        {"start_time": 12.5, "duration": 30.0, "title": "开场"}
    ]
    assert entry["podcast_value"]["recipients"] == [
        {
            "name": "李四",
            "type": "node",
            "address": "03def",
            "split": 5,
            "fee": False,
        }
    ]
