from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
@dataclass(frozen=True)
class Proposal:
    proposal_id:str; actor_id:str; action:str; changed_paths:tuple[str,...]; payload_sha256:str
    mutation_tier:str='TIER1_OPERATIONAL'; generator_surface:bool=False; description:str=''
@dataclass(frozen=True)
class Receipt:
    receipt_id:str; issuer_id:str; issuer_role:str; kind:str; subject_id:str; subject_sha256:str; claims:dict[str,Any]; signature:str
@dataclass(frozen=True)
class Decision:
    disposition:str; reasons:tuple[str,...]; proposal_id:str; relied_on:tuple[str,...]=field(default_factory=tuple)
