from app.rag.chunking import chunk_markdown

DOC = """# Title

Intro paragraph about the topic that sets the scene.

## Section A

First detailed paragraph of section A with enough text to be meaningful.

Second paragraph of section A continuing the explanation in more depth.

## Section B

Section B paragraph one.
"""


def test_chunks_are_produced_and_tagged():
    chunks = chunk_markdown(DOC, source="doc.md", max_chars=120, overlap=20)
    assert chunks, "expected at least one chunk"
    assert all(c.source == "doc.md" for c in chunks)
    # headings are captured for citation context
    headings = {c.heading for c in chunks}
    assert "Section A" in headings
    assert "Section B" in headings


def test_chunks_respect_size_budget():
    chunks = chunk_markdown(DOC, source="doc.md", max_chars=120, overlap=20)
    # allow a little slack for overlap/句 joining, but nothing wildly oversized
    assert all(len(c.text) <= 200 for c in chunks)


def test_indices_are_sequential():
    chunks = chunk_markdown(DOC, source="doc.md", max_chars=120, overlap=20)
    assert [c.index for c in chunks] == list(range(len(chunks)))
