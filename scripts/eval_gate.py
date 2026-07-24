"""Run the eval gate and exit non-zero on failure (spec §6, Opsera stage 4).

    python -m scripts.eval_gate

Deterministic — replays recorded captures, never the network.
"""

from __future__ import annotations

import sys

from app.eval.gate import run_gate


def main() -> int:
    result = run_gate()
    if result.ok:
        print("eval gate: PASS")
        return 0
    print("eval gate: FAIL")
    for f in result.failures:
        print(f"  - {f}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
