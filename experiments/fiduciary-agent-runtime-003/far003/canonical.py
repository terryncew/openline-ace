from __future__ import annotations
import hashlib, hmac, json

def canonical(obj): return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def sha256(obj):
    if isinstance(obj,bytes): b=obj
    elif isinstance(obj,str): b=obj.encode()
    else: b=canonical(obj)
    return hashlib.sha256(b).hexdigest()
def sign(secret,payload): return hmac.new(secret.encode(),canonical(payload),hashlib.sha256).hexdigest()
def verify(secret,payload,signature): return hmac.compare_digest(sign(secret,payload),signature)
