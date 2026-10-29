"""Split a SQL migration into statements while keeping line numbers."""

from __future__ import annotations

import re
from dataclasses import dataclass

BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
LINE_COMMENT_RE = re.compile(r"--[^\n]*")


@dataclass
class Statement:
    """One statement, normalized, with the line it starts on."""

    text: str
    line: int

    @property
    def upper(self) -> str:
        return self.text.upper()


def strip_comments(sql: str) -> str:
    """Remove block and line comments, preserving line breaks for numbering."""
    without_block = BLOCK_COMMENT_RE.sub(
        lambda m: "\n" * m.group(0).count("\n"), sql
    )
    return LINE_COMMENT_RE.sub("", without_block)


def split_statements(sql: str) -> list[Statement]:
    """Split on semicolons at the top level, tracking line numbers.

    Semicolons inside single quotes, double quotes, or dollar-quoted blocks are ignored.
    """
    cleaned = strip_comments(sql)
    statements: list[Statement] = []
    buffer: list[str] = []
    line = 1
    start_line = 1
    quote: str | None = None
    dollar_tag: str | None = None
    index = 0

    while index < len(cleaned):
        char = cleaned[index]

        if dollar_tag is None and quote is None:
            match = re.match(r"\$[A-Za-z_]*\$", cleaned[index:])
            if match:
                dollar_tag = match.group(0)
                buffer.append(dollar_tag)
                index += len(dollar_tag)
                continue

        if dollar_tag is not None:
            if cleaned.startswith(dollar_tag, index):
                buffer.append(dollar_tag)
                index += len(dollar_tag)
                dollar_tag = None
                continue

        if char in ("'", '"') and dollar_tag is None:
            if quote is None:
                quote = char
            elif quote == char:
                quote = None
        elif quote is None and dollar_tag is None and char == ";":
            text = "".join(buffer).strip()
            if text:
                statements.append(Statement(text=" ".join(text.split()), line=start_line))
            buffer = []
            index += 1
            start_line = line + cleaned[index:index + 1].count("\n")
            # recompute precisely below
            start_line = line
            continue

        if quote is None and dollar_tag is None:
            buffer.append(char)
        else:
            buffer.append(char)

        if char == "\n":
            line += 1
            if not "".join(buffer).strip():
                start_line = line
        index += 1

    tail = "".join(buffer).strip()
    if tail:
        statements.append(Statement(text=" ".join(tail.split()), line=start_line))
    return statements
