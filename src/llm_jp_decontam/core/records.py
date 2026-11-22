"""Records of the input files.

An input file is gzip-compressed JSON Lines.  One line is one record:

    {"id": str, "messages": [{"role": str, "content": str}, ...]}

A message with the role "assistant" may also hold "reasoning": str.  Only the keys id,
messages, role, content and reasoning are read.
"""

from __future__ import annotations

import json
import re
from typing import NamedTuple

_TSV_UNSAFE = re.compile(r"[\t\r\n]")


class Record(NamedTuple):
    """One parsed record."""

    id: str
    """The id, with tabs and line breaks replaced by spaces so that it fits in a TSV cell."""
    texts: list[str]
    """The text elements: `content` and `reasoning` of every message, in order."""


def parse_record(line: str | bytes) -> Record | None:
    """Parse one line of an input file.

    Returns None for a parse failure: a line that is not JSON, a record whose `messages` is
    not a list, or a record with a message whose `content` is not a string.
    """
    try:
        obj = json.loads(line)
    except (ValueError, RecursionError):
        return None
    messages = obj.get("messages") if isinstance(obj, dict) else None
    if not isinstance(messages, list):
        return None

    texts = []
    for message in messages:
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str):
            return None
        texts.append(content)
        if message.get("role") == "assistant":
            reasoning = message.get("reasoning")
            if isinstance(reasoning, str):
                texts.append(reasoning)

    record_id = obj.get("id")
    if not isinstance(record_id, str):
        record_id = "" if record_id is None else json.dumps(record_id, ensure_ascii=False)
    return Record(_TSV_UNSAFE.sub(" ", record_id), texts)
