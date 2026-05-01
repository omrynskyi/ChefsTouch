from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import List, Union

_ID_RE = re.compile(r'"id"\s*:\s*"([^"\\]+)"')
_TYPE_RE = re.compile(r'"type"\s*:\s*"([^"\\]+)"')


@dataclass
class SkeletonEvent:
    id: str
    component_type: str


@dataclass
class ContentEvent:
    op: dict


class JSONStreamHealer:
    """
    State machine that parses a JSONL stream incrementally.

    Feed token chunks via feed(). Each time a complete JSON object is
    detected (brace depth returns to 0), a ContentEvent is emitted.
    A SkeletonEvent is emitted earlier — as soon as "id" and "type"
    are visible in the partial buffer — to let the client render a
    shimmer placeholder before the full op arrives.
    """

    def __init__(self) -> None:
        self.depth: int = 0
        self.in_string: bool = False
        self.escape_next: bool = False
        self.line_buffer: str = ""
        self.skeleton_emitted: set = set()

    def feed(self, chunk: str) -> List[Union[SkeletonEvent, ContentEvent]]:
        events: List[Union[SkeletonEvent, ContentEvent]] = []
        for char in chunk:
            events.extend(self._process_char(char))
        return events

    def finalize(self) -> List[Union[SkeletonEvent, ContentEvent]]:
        """Attempt to parse any remaining buffer content after the stream ends."""
        raw = self.line_buffer.strip()
        if raw:
            try:
                obj = json.loads(raw)
                return [ContentEvent(op=obj)]
            except json.JSONDecodeError:
                pass
        return []

    def _process_char(self, char: str) -> List[Union[SkeletonEvent, ContentEvent]]:
        events: List[Union[SkeletonEvent, ContentEvent]] = []

        if self.escape_next:
            self.escape_next = False
            self.line_buffer += char
            return events

        if char == "\\" and self.in_string:
            self.escape_next = True
            self.line_buffer += char
            return events

        if char == '"':
            self.in_string = not self.in_string
            self.line_buffer += char
            return events

        if not self.in_string:
            if char == "{":
                self.depth += 1
                self.line_buffer += char
                return events
            if char == "}":
                self.depth -= 1
                self.line_buffer += char
                if self.depth == 0 and self.line_buffer.strip():
                    events.extend(self._try_emit_content())
                return events
            if char == "\n" and self.depth == 0:
                self.line_buffer = ""
                return events

        self.line_buffer += char

        if self.depth >= 1:
            events.extend(self._maybe_emit_skeleton())

        return events

    def _maybe_emit_skeleton(self) -> List[Union[SkeletonEvent, ContentEvent]]:
        id_match = _ID_RE.search(self.line_buffer)
        type_match = _TYPE_RE.search(self.line_buffer)
        if id_match and type_match:
            obj_id = id_match.group(1)
            obj_type = type_match.group(1)
            if obj_id not in self.skeleton_emitted:
                self.skeleton_emitted.add(obj_id)
                return [SkeletonEvent(id=obj_id, component_type=obj_type)]
        return []

    def _try_emit_content(self) -> List[Union[SkeletonEvent, ContentEvent]]:
        raw = self.line_buffer.strip()
        self.line_buffer = ""
        try:
            obj = json.loads(raw)
            return [ContentEvent(op=obj)]
        except json.JSONDecodeError:
            return []
