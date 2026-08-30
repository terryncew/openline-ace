from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve()
EXPERIMENTS = HERE.parents[2]
FAR003 = EXPERIMENTS / "fiduciary-agent-runtime-003"
FAR005 = EXPERIMENTS / "fiduciary-agent-runtime-005"

for path in (FAR003, FAR005):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from far003.canonical import sha256
from far003.classifier import classify
from far003.gate import Gate
from far003.model import Proposal, Receipt
from far003.receipts import Registry
from far005.claim_graph import ClaimGraph, StandingGate

__all__ = [
    "ClaimGraph",
    "Gate",
    "Proposal",
    "Receipt",
    "Registry",
    "StandingGate",
    "classify",
    "sha256",
]
