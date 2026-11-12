# Support for the Podcast Namespace
# Copyright 2010-2025 Kurt McKee <contactme@kurtmckee.org>
# Copyright 2002-2008 Mark Pilgrim
# All rights reserved.
#
# This file is a part of feedparser.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS 'AS IS'
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from ..util import FeedParserDict


class Namespace:
    supported_namespaces = {
        "https://podcastindex.org/namespace/1.0": "podcast",
        "http://podcastindex.org/namespace/1.0": "podcast",
        "https://podcastindex.org/namespace/1.0/": "podcast",
        "http://podcastindex.org/namespace/1.0/": "podcast",
    }

    def __init__(self):
        # Elements nested inside <podcast:person>, <podcast:soundbite>, and
        # <podcast:value> are tracked on these stacks so the dictionary can be
        # updated when the element's text content is available.
        self._podcast_person_stack = []
        self._podcast_soundbite_stack = []
        self._podcast_value_stack = []
        super().__init__()

    def _start_podcast_transcript(self, attrs_d):
        context = self._get_context()
        context.setdefault("podcast_transcript", []).append(FeedParserDict(attrs_d))
        self.push("podcast_transcript", 0)

    def _start_podcast_person(self, attrs_d):
        person = FeedParserDict()
        for key in ("role", "href"):
            if key in attrs_d:
                person[key] = attrs_d[key]
        self._get_context().setdefault("podcast_person", []).append(person)
        self._podcast_person_stack.append(person)
        self.push("podcast_person", 0)

    def _end_podcast_person(self):
        name = self.pop("podcast_person")
        if self._podcast_person_stack:
            person = self._podcast_person_stack.pop()
            if name:
                person["name"] = name

    def _start_podcast_soundbite(self, attrs_d):
        soundbite = FeedParserDict()
        for attr, key in (("starttime", "start_time"), ("duration", "duration")):
            if attr in attrs_d:
                try:
                    soundbite[key] = float(attrs_d[attr])
                except (TypeError, ValueError):
                    pass
        self._get_context().setdefault("podcast_soundbite", []).append(soundbite)
        self._podcast_soundbite_stack.append(soundbite)
        self.push("podcast_soundbite", 0)

    def _end_podcast_soundbite(self):
        title = self.pop("podcast_soundbite")
        if self._podcast_soundbite_stack:
            soundbite = self._podcast_soundbite_stack.pop()
            if title:
                soundbite["title"] = title

    def _start_podcast_value(self, attrs_d):
        value = FeedParserDict(attrs_d)
        value["recipients"] = []
        self._get_context()["podcast_value"] = value
        self._podcast_value_stack.append(value)
        self.push("podcast_value", 0)

    def _end_podcast_value(self):
        self.pop("podcast_value")
        if self._podcast_value_stack:
            self._podcast_value_stack.pop()

    def _start_podcast_valuerecipient(self, attrs_d):
        recipient = FeedParserDict()
        for key in ("name", "type", "address"):
            if key in attrs_d:
                recipient[key] = attrs_d[key]
        if "split" in attrs_d:
            try:
                recipient["split"] = int(float(attrs_d["split"]))
            except (TypeError, ValueError):
                pass
        # The fee attribute defaults to false; include it even when it is
        # explicitly set to "false" so callers can distinguish it from a
        # missing attribute.
        recipient["fee"] = str(attrs_d.get("fee", "false")).strip().lower() in (
            "true",
            "1",
            "yes",
        )
        if self._podcast_value_stack:
            self._podcast_value_stack[-1]["recipients"].append(recipient)
        self.push("podcast_valuerecipient", 0)
