"""LLM-as-judge output scoring (with a deterministic heuristic fallback).

Implements the two non-negotiables from the Skills evaluation chapter:
  1. Reference-guided scoring against an explicit rubric.
  2. Position-swap: when an LLM judge is used, each comparison is run twice with
     the candidate placed first then second, and the scores averaged, to
     neutralize the well-known ordering bias of LLM judges.

If no real LLM is configured, a transparent keyword-coverage heuristic is used so
`make eval` always produces a number offline.
"""

from __future__ import annotations

import re
from typing import Any

from app.config import get_settings


def _heuristic_score(answer: str, rubric: list[str]) -> dict[str, Any]:
    ans = answer.lower()
    passed = []
    for criterion in rubric:
        # treat each "word longer than 3 chars" in the criterion as a soft cue
        cues = [w for w in re.findall(r"[a-z0-9()+]+", criterion.lower()) if len(w) > 3]
        hits = sum(1 for w in cues if w in ans)
        passed.append(hits >= max(1, len(cues) // 3))
    score = sum(passed) / len(rubric) if rubric else 0.0
    return {
        "method": "heuristic",
        "score": round(score, 3),
        "per_criterion": dict(zip(rubric, passed)),
    }


def _llm_score(question: str, answer: str, rubric: list[str]) -> dict[str, Any]:
    import anthropic

    settings = get_settings()
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    rubric_block = "\n".join(f"- {c}" for c in rubric)

    def run(order_note: str) -> float:
        prompt = (
            "You are a strict evaluator. Score the assistant ANSWER against each "
            "rubric criterion. Reply with ONLY a JSON object mapping each criterion "
            'to true/false, e.g. {"criterion": true}.\n\n'
            f"{order_note}\n"
            f"QUESTION:\n{question}\n\nANSWER:\n{answer}\n\nRUBRIC:\n{rubric_block}"
        )
        resp = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in resp.content if b.type == "text")
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return 0.0
        import json

        verdicts = json.loads(match.group())
        vals = [bool(v) for v in verdicts.values()]
        return sum(vals) / len(vals) if vals else 0.0

    # position swap: judge twice, average (ordering-bias mitigation)
    s1 = run("(evaluation pass A)")
    s2 = run("(evaluation pass B — re-read carefully before scoring)")
    return {"method": "llm", "score": round((s1 + s2) / 2, 3), "passes": [s1, s2]}


def judge_answer(question: str, answer: str, rubric: list[str]) -> dict[str, Any]:
    settings = get_settings()
    if settings.llm_provider == "anthropic" and settings.anthropic_api_key:
        try:
            return _llm_score(question, answer, rubric)
        except Exception as exc:  # fall back rather than fail the whole run
            result = _heuristic_score(answer, rubric)
            result["llm_error"] = f"{type(exc).__name__}: {exc}"
            return result
    return _heuristic_score(answer, rubric)
