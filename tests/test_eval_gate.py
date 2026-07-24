"""Eval gate wrapper (spec §6).

Skips locally when captures are absent (the buildable suite stays green), but
the standalone `python -m scripts.eval_gate` exits non-zero in CI so the Opsera
stage is red until real captures are recorded.
"""

from __future__ import annotations

import pytest
from app.eval.gate import run_gate
from app.eval.replay import captures_available


@pytest.mark.skipif(not captures_available(), reason="no recorded captures — record with live keys")
def test_eval_gate_passes_with_captures() -> None:
    result = run_gate()
    assert result.ok, "\n".join(result.failures)


def test_gate_reports_missing_captures_when_absent() -> None:
    # When captures are absent the gate must refuse to run (not pass silently).
    if captures_available():
        pytest.skip("captures present")
    result = run_gate()
    assert result.ran is False
    assert result.ok is False
