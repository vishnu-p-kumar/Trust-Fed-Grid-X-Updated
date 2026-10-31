"""Pairwise-mask secure aggregation reference protocol for controlled simulations.

This is an educational protocol sketch. Production deployments require authenticated
key exchange, dropout recovery, replay protection, side-channel review and formal audit.
"""
from __future__ import annotations
import hashlib
import numpy as np

def _seed(secret: bytes, round_id: str, a: str, b: str) -> int:
    msg="|".join([round_id,*sorted([a,b])]).encode()
    return int.from_bytes(hashlib.sha256(secret+msg).digest()[:8],"big")

def masked_sum(updates: dict[str,np.ndarray], *, secret: bytes, round_id: str) -> np.ndarray:
    if len(updates)<2 or not secret: raise ValueError("at least two clients and a shared secret are required")
    ids=sorted(updates); arrays={k:np.asarray(v,dtype=float) for k,v in updates.items()}
    shape=arrays[ids[0]].shape
    if any(a.shape!=shape or not np.isfinite(a).all() for a in arrays.values()): raise ValueError("updates must be finite and have identical shapes")
    masked={k:a.copy() for k,a in arrays.items()}
    for i,a in enumerate(ids):
        for b in ids[i+1:]:
            rng=np.random.default_rng(_seed(secret,round_id,a,b)); mask=rng.normal(size=shape)
            masked[a]+=mask; masked[b]-=mask
    return np.sum(np.stack(list(masked.values())),axis=0)
