"""Block until Qdrant is reachable (used by the container entrypoint)."""

from __future__ import annotations

import sys
import time
import urllib.request

from app.config import get_settings


def main(timeout: float = 60.0) -> int:
    url = get_settings().qdrant_url.rstrip("/") + "/readyz"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                if resp.status == 200:
                    print(f"[wait_for_qdrant] ready: {url}")
                    return 0
        except Exception:
            pass
        time.sleep(1.5)
    print(f"[wait_for_qdrant] timed out waiting for {url}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
