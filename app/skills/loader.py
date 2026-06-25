"""Load Agent Skills with progressive disclosure.

Three levels, straight from the Agent Skills whitepaper:
  L1 metadata (name + description) -> always in the system prompt (cheap).
  L2 SKILL.md body                 -> loaded only when the model calls `load_skill`.
  L3 bundled scripts/references     -> loaded only if the body points to them.

A tiny, dependency-free frontmatter parser keeps `requirements.txt` lean and
demonstrates the format rather than hiding it behind PyYAML.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings


@dataclass
class Skill:
    name: str
    description: str
    allowed_tools: list[str]
    body: str  # the SKILL.md content below the frontmatter (L2)
    path: Path

    def metadata_line(self) -> str:
        # one-line catalog entry (L1) — this is what the model routes on
        desc = " ".join(self.description.split())
        return f"- {self.name}: {desc}"


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (frontmatter_dict, body). Handles scalars, `key: |` block
    scalars, and inline `[a, b]` lists for the fields we care about."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    raw = text[3:end].strip("\n")
    body = text[end + 4 :].lstrip("\n")

    fm: dict = {}
    lines = raw.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if ":" not in line:
            i += 1
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        # nested block (e.g. `metadata:`) — skip its indented children
        if value == "":
            i += 1
            while i < len(lines) and (lines[i].startswith((" ", "\t")) or not lines[i].strip()):
                i += 1
            continue
        if value == "|":  # block scalar
            i += 1
            block = []
            while i < len(lines) and (lines[i].startswith((" ", "\t")) or not lines[i].strip()):
                block.append(lines[i].strip())
                i += 1
            fm[key] = "\n".join(block).strip()
            continue
        if value.startswith("[") and value.endswith("]"):
            fm[key] = [v.strip() for v in value[1:-1].split(",") if v.strip()]
        else:
            fm[key] = value
        i += 1
    return fm, body


def load_skills(skills_dir: str | None = None) -> list[Skill]:
    base = Path(skills_dir or get_settings().skills_dir)
    skills: list[Skill] = []
    for skill_md in sorted(base.glob("*/SKILL.md")):
        fm, body = _parse_frontmatter(skill_md.read_text(encoding="utf-8"))
        name = fm.get("name") or skill_md.parent.name
        allowed = fm.get("allowed-tools") or fm.get("allowed_tools") or []
        if isinstance(allowed, str):
            allowed = [allowed]
        skills.append(
            Skill(
                name=name,
                description=fm.get("description", ""),
                allowed_tools=list(allowed),
                body=body.strip(),
                path=skill_md,
            )
        )
    return skills


class SkillRegistry:
    """Holds loaded skills and serves the catalog (L1) and bodies (L2)."""

    def __init__(self, skills: list[Skill]):
        self._by_name = {s.name: s for s in skills}

    @classmethod
    def load(cls, skills_dir: str | None = None) -> "SkillRegistry":
        return cls(load_skills(skills_dir))

    @property
    def skills(self) -> list[Skill]:
        return list(self._by_name.values())

    def catalog(self) -> str:
        if not self._by_name:
            return "(no skills installed)"
        return "\n".join(s.metadata_line() for s in self._by_name.values())

    def get_body(self, name: str) -> str | None:
        skill = self._by_name.get(name)
        return skill.body if skill else None
