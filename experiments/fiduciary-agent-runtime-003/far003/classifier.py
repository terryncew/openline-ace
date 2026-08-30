from __future__ import annotations
from .model import Proposal
TIER3_PREFIXES=('tests/','.openline/evaluators/','.openline/policy/','.openline/mandates/','.openline/receipts/','.openline/gate/','.openline/scope/','.github/workflows/','gate/','policy/','experiments/fiduciary-agent-runtime-003/SCOPE_MANIFEST.json')
TIER2_PREFIXES=('agent/search/','agent/retrieval/','generator/','.openline/generator/','search/')
TIER1_PREFIXES=('src/','lib/','app/')
def classify(proposal:Proposal):
    paths=tuple(p[2:] if p.startswith('./') else p for p in proposal.changed_paths)
    if any(any(p.startswith(x) for x in TIER3_PREFIXES) for p in paths): return 'TIER3_CONSTITUTIONAL','principal-owned definition-of-success, scope, or authority surface'
    if proposal.generator_surface or any(any(p.startswith(x) for x in TIER2_PREFIXES) for p in paths): return 'TIER2_GENERATOR','persistent proposal-shaping surface'
    if paths and all(any(p.startswith(x) for x in TIER1_PREFIXES) for p in paths): return 'TIER1_OPERATIONAL','ordinary repository implementation surface'
    return 'TIER2_GENERATOR','unknown surface defaults upward'
