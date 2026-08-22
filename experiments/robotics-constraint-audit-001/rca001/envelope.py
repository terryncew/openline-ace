from dataclasses import dataclass
@dataclass(frozen=True)
class EnvelopeConfig:
    reaction_time_s: float=.05
    min_deceleration_mps2: float=1.5
    safety_margin_m: float=.20
    max_evidence_age_ms: float=100.0

def stopping_distance(speed_mps,cfg):
    if speed_mps<0 or cfg.min_deceleration_mps2<=0: raise ValueError("bad envelope input")
    return speed_mps*cfg.reaction_time_s + speed_mps**2/(2*cfg.min_deceleration_mps2) + cfg.safety_margin_m

def assess(*,speed_mps,distance_to_boundary_m,evidence_age_ms,trusted,cfg):
    if distance_to_boundary_m<0 or evidence_age_ms<0: raise ValueError("bad receiver input")
    req=stopping_distance(speed_mps,cfg)
    if not trusted: return {"standing":"UNDECIDABLE","disposition":"QUARANTINE","reason":"untrusted_evidence","required_stop_m":req}
    if evidence_age_ms>cfg.max_evidence_age_ms: return {"standing":"REJECTED","disposition":"DENY","reason":"stale_envelope_evidence","required_stop_m":req}
    if distance_to_boundary_m<req: return {"standing":"REJECTED","disposition":"DENY","reason":"outside_stopping_envelope","required_stop_m":req}
    return {"standing":"VERIFIED","disposition":"COMMIT","reason":"inside_stopping_envelope","required_stop_m":req}
