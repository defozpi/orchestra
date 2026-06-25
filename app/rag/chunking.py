"""Markdown-aware chunking.

Kept dependency-free and pure so it is trivially unit-testable. The strategy:
split on markdown headings first (so a chunk stays topically coherent), then
pack paragraphs up to a character budget with a small overlap to preserve
context across cut points (see knowledge_base/rag-and-context-rot.md).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_HEADING_RE = re.compile(r"^#{1,6}\s+.*$", re.MULTILINE)


@dataclass
class Chunk:
    text: str
    source: str  # filename the chunk came from
    heading: str  # nearest preceding heading, for citation context
    index: int  # ordinal within the source document


def _split_sections(markdown: str) -> list[tuple[str, str]]:
    """Return (heading, body) sections. Text before the first heading is kept
    under an empty heading."""
    matches = list(_HEADING_RE.finditer(markdown))
    if not matches:
        return [("", markdown)]

    sections: list[tuple[str, str]] = []
    if matches[0].start() > 0:
        sections.append(("", markdown[: matches[0].start()]))

    for i, m in enumerate(matches):
        heading = m.group().lstrip("#").strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        sections.append((heading, markdown[start:end]))
    return sections


def chunk_markdown(
    markdown: str,
    source: str,
    *,
    max_chars: int = 1100,
    overlap: int = 180,
) -> list[Chunk]:
    """Split one markdown document into overlapping, heading-tagged chunks."""
    chunks: list[Chunk] = []
    idx = 0

    for heading, body in _split_sections(markdown):
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
        buffer = ""

        def flush(buf: str) -> str:
            nonlocal idx
            buf = buf.strip()
            if not buf:
                return ""
            chunks.append(
                Chunk(text=buf, source=source, heading=heading, index=idx)
            )
            idx += 1
            # carry the tail of this chunk forward as overlap
            return buf[-overlap:] if overlap else ""

        for para in paragraphs:
            candidate = f"{buffer}\n\n{para}".strip() if buffer else para
            if len(candidate) <= max_chars:
                buffer = candidate
            else:
                carried = flush(buffer)
                buffer = f"{carried}\n\n{para}".strip() if carried else para
                # a single oversized paragraph still gets its own chunk
                while len(buffer) > max_chars:
                    head, buffer = buffer[:max_chars], buffer[max_chars - overlap :]
                    chunks.append(
                        Chunk(text=head.strip(), source=source, heading=heading, index=idx)
                    )
                    idx += 1
        flush(buffer)

    return chunks
