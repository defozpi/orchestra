"""Human-in-the-loop approval gate for action (write) tools.

"Do include HITL: Show tool inputs to the user before calling the server, to
avoid malicious or accidental data exfiltration" — MCP best practices.

A tool whose name starts with a configured prefix (save_, delete_, send_, ...) is
an *action* tool. Unless the request explicitly grants auto-approval, the harness
will NOT execute it: instead it surfaces the exact proposed call for the user to
approve. This is the read / draft / act ladder enforced at runtime.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import get_settings


@dataclass
class ApprovalPolicy:
    auto_approve: bool = False
    prefixes: tuple[str, ...] = ()

    @classmethod
    def from_settings(cls, auto_approve: bool = False) -> "ApprovalPolicy":
        return cls(
            auto_approve=auto_approve,
            prefixes=get_settings().require_approval_prefixes,
        )

    def is_action(self, tool_name: str) -> bool:
        return tool_name.startswith(self.prefixes)

    def needs_approval(self, tool_name: str) -> bool:
        return self.is_action(tool_name) and not self.auto_approve
