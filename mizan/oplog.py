"""Tamper-evident, append-only operator log (JSON Lines).

Every entry carries the hash of the previous one, so editing or deleting any
past line breaks the chain and `verify` reports where. Corrections are new
entries, never edits.

kinds: action | deviation | identity_access
Real names never go in this log.
"""
import hashlib
import json
import os
from datetime import datetime, timezone

KINDS = {"action", "deviation", "identity_access"}
GENESIS = "0" * 64


def _digest(entry):
    body = {k: v for k, v in entry.items() if k != "hash"}
    raw = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def read(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def append(path, kind, request_id, actor, action, rule="", input="", output="",
           manual_discretion=False, reason="", now=None):
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {sorted(KINDS)}")
    if kind == "deviation" and not reason:
        raise ValueError("a deviation needs a reason")
    entries = read(path)
    entry = {
        "seq": len(entries) + 1,
        "timestamp": now or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "kind": kind,
        "request_id": request_id,
        "actor": actor,
        "action": action,
        "rule": rule,
        "input": input,
        "output": output,
        "manual_discretion": bool(manual_discretion),
        "reason": reason,
        "prev_hash": entries[-1]["hash"] if entries else GENESIS,
    }
    entry["hash"] = _digest(entry)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def verify(path):
    prev = GENESIS
    for i, e in enumerate(read(path), start=1):
        if e.get("seq") != i:
            return False, f"entry {i}: sequence broken"
        if e.get("prev_hash") != prev:
            return False, f"entry {i}: chain broken (previous entry altered or removed)"
        if _digest(e) != e.get("hash"):
            return False, f"entry {i}: content altered"
        prev = e["hash"]
    return True, "log intact"


def summary(path):
    entries = read(path)
    out = {"entries": len(entries), "deviations": 0, "manual_discretion": 0, "identity_access": 0}
    for e in entries:
        out["deviations"] += e["kind"] == "deviation"
        out["identity_access"] += e["kind"] == "identity_access"
        out["manual_discretion"] += bool(e["manual_discretion"])
    return out
