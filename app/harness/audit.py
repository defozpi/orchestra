"""Structured audit log of every tool call and harness decision.

"Do auditing needs: Log tool usage for audit purposes" — MCP best practices.
Every event is captured both for the live event stream (the UI shows it) and for
governance/debugging.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("orchestra.audit")


@dataclass
class AuditEvent:
    kind: str  # step | tool_call | tool_result | approval_required | answer | error
    data: dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)

    def as_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "ts": self.ts, **self.data}


class AuditLog:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def record(self, kind: str, **data: Any) -> AuditEvent:
        event = AuditEvent(kind=kind, data=data)
        self.events.append(event)
        logger.info("audit %s %s", kind, {k: v for k, v in data.items() if k != "content"})
        return event
