"""Run the evaluation suite and print a report.

Covers three of the four Skills failure modes directly:
  - Trigger:    did the expected tool fire (positive) / stay quiet (negative)?
  - Execution:  trajectory (expected tools present) + LLM-as-judge output score.
  - (Token-budget / regression are exercised by running the full library together.)

Usage:  python -m app.eval.run_eval
"""

from __future__ import annotations

import json
from pathlib import Path

from app.eval.judge import judge_answer
from app.harness.runtime import Runtime

CASES_PATH = Path("app/eval/cases.json")


def _tools_used(trace: list) -> list[str]:
    return [e["name"] for e in trace if e.get("kind") == "tool_call"]


def run() -> dict:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    runtime = Runtime()
    results = []
    try:
        # auto_approve so action tools actually execute during evaluation
        agent = runtime.agent(auto_approve=True)
        for case in cases:
            answer, audit = agent.run(case["input"])
            trace = [e.as_dict() for e in audit.events]
            used = _tools_used(trace)

            expected = case.get("expected_tools", [])
            if case["should_trigger"]:
                trigger_ok = all(t in used for t in expected) if expected else bool(used)
                trajectory_ok = all(t in used for t in expected)  # ANY_ORDER (read-only)
            else:
                # negative case: no retrieval/action tool should fire
                trigger_ok = not any(t in used for t in ["search_knowledge_base"] + expected)
                trajectory_ok = trigger_ok

            verdict = judge_answer(case["input"], answer, case.get("rubric", []))
            results.append(
                {
                    "case_id": case["case_id"],
                    "should_trigger": case["should_trigger"],
                    "tools_used": used,
                    "trigger_ok": trigger_ok,
                    "trajectory_ok": trajectory_ok,
                    "judge_score": verdict["score"],
                    "judge_method": verdict["method"],
                    "answer": answer,
                }
            )
    finally:
        runtime.close()

    trig = [r["trigger_ok"] for r in results]
    summary = {
        "cases": len(results),
        "trigger_accuracy": round(sum(trig) / len(trig), 3) if trig else 0.0,
        "trajectory_pass": round(
            sum(r["trajectory_ok"] for r in results) / len(results), 3
        )
        if results
        else 0.0,
        "avg_judge_score": round(
            sum(r["judge_score"] for r in results) / len(results), 3
        )
        if results
        else 0.0,
    }
    return {"summary": summary, "results": results}


def main() -> None:
    report = run()
    s = report["summary"]
    print("\n=== orchestra eval report ===")
    print(
        f"cases={s['cases']}  trigger_accuracy={s['trigger_accuracy']:.0%}  "
        f"trajectory_pass={s['trajectory_pass']:.0%}  "
        f"avg_judge_score={s['avg_judge_score']:.2f}"
    )
    print("-" * 60)
    for r in report["results"]:
        flag = "PASS" if r["trigger_ok"] and r["trajectory_ok"] else "FAIL"
        print(
            f"[{flag}] {r['case_id']:<32} tools={r['tools_used']} "
            f"judge={r['judge_score']:.2f} ({r['judge_method']})"
        )
    print()


if __name__ == "__main__":
    main()
