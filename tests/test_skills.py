from app.skills.loader import SkillRegistry, _parse_frontmatter, load_skills

SKILL = """---
name: research-synthesis
description: |
  Synthesizes a grounded answer from retrieved passages.
  Use when the user asks to explain or compare.
  Do NOT use for saving notes.
allowed-tools: [search_knowledge_base]
metadata:
  author: defne
---
# Research Synthesis

Body content here.
"""


def test_frontmatter_parses_block_scalar_and_list():
    fm, body = _parse_frontmatter(SKILL)
    assert fm["name"] == "research-synthesis"
    assert "grounded answer" in fm["description"]
    assert fm["allowed-tools"] == ["search_knowledge_base"]
    assert body.startswith("# Research Synthesis")


def test_registry_loads_repo_skills():
    # the real skills/ folder ships with the project
    skills = load_skills("skills")
    names = {s.name for s in skills}
    assert {"research-synthesis", "citing-sources", "note-taking"} <= names


def test_catalog_is_one_line_per_skill():
    reg = SkillRegistry.load("skills")
    catalog = reg.catalog()
    assert catalog.count("\n") + 1 == len(reg.skills)
    assert reg.get_body("note-taking")  # body available on demand (L2)
    assert reg.get_body("does-not-exist") is None
