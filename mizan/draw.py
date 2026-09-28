"""Verifiable reviewer lottery.

Flow:
  1. commit: canonicalise the candidate list, hash it, and bind it to a
     FUTURE drand round. Publish the commit file before that round exists.
  2. draw:   once the round is out, take its randomness and rank every
     candidate by SHA-256(randomness | request_id | pseudonym).
  3. verify: anyone recomputes the ranking from the published files.

Nobody (operator included) can steer the result: the list is frozen before
the randomness exists, and the randomness comes from a public beacon.
"""
import hashlib
import json
import time
import urllib.request

DRAND_BASE = "https://api.drand.sh"


def canonical_list(names):
    """Strip, reject duplicates/blanks, sort. Order of input never matters."""
    cleaned = [n.strip() for n in names if n.strip()]
    if len(cleaned) != len(set(cleaned)):
        raise ValueError("duplicate pseudonym in candidate list")
    return sorted(cleaned)


def list_hash(names):
    blob = "\n".join(canonical_list(names)).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def read_list(path):
    with open(path, encoding="utf-8") as fh:
        return canonical_list(fh.read().splitlines())


def key(randomness, request_id, name):
    return hashlib.sha256(f"{randomness}|{request_id}|{name}".encode("utf-8")).hexdigest()


def rank(names, randomness, request_id):
    """Full ordering. The first k are invited; the rest are the
    replacement queue, used in order when someone declines (stage M1)."""
    names = canonical_list(names)
    return sorted(names, key=lambda n: key(randomness, request_id, n))


def weighted_rank(weights, randomness, request_id):
    """Efraimidis-Spirakis weighted order: key = u ** (1 / w), highest first.
    weights: {name: positive weight}, published before the draw."""
    out = []
    for name, w in weights.items():
        if w <= 0:
            raise ValueError(f"weight for {name} must be positive")
        u = (int(key(randomness, request_id, name), 16) + 1) / (2 ** 256 + 1)
        out.append((u ** (1.0 / w), name))
    return [n for _, n in sorted(out, reverse=True)]


# ---- drand beacon -------------------------------------------------------

def _get_json(url, timeout=15):
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def drand_info():
    return _get_json(f"{DRAND_BASE}/info")


def round_at(unix_time, genesis_time, period):
    return int((unix_time - genesis_time) // period) + 1


def drand_randomness(round_no):
    data = _get_json(f"{DRAND_BASE}/public/{round_no}")
    if int(data["round"]) != int(round_no):
        raise ValueError("beacon returned a different round")
    return data["randomness"]


# ---- commit / draw / verify --------------------------------------------

def make_commit(names, request_id, delay_hours=24.0, now=None, info=None):
    info = info or drand_info()
    now = time.time() if now is None else now
    target = round_at(now + delay_hours * 3600, info["genesis_time"], info["period"])
    return {
        "request_id": request_id,
        "candidates_count": len(canonical_list(names)),
        "candidates_sha256": list_hash(names),
        "drand_base": DRAND_BASE,
        "drand_round": target,
        "committed_at_unix": int(now),
    }


def make_draw(commit, names, randomness, k):
    if list_hash(names) != commit["candidates_sha256"]:
        raise ValueError("candidate list does not match the published commit")
    order = rank(names, randomness, commit["request_id"])
    return {
        "request_id": commit["request_id"],
        "candidates_sha256": commit["candidates_sha256"],
        "drand_round": commit["drand_round"],
        "randomness": randomness,
        "k": k,
        "selected": order[:k],
        "replacement_queue": order[k:],
    }


def verify_draw(result, names):
    """Returns (ok, message). Needs only public files."""
    if list_hash(names) != result["candidates_sha256"]:
        return False, "candidate list hash mismatch"
    order = rank(names, result["randomness"], result["request_id"])
    if order[: result["k"]] != result["selected"] or order[result["k"]:] != result["replacement_queue"]:
        return False, "ranking mismatch"
    return True, "draw verified"
