"""Stable pseudonyms. The mapping to real identities lives ONLY in private/
(git-ignored). Keep that folder inside an encrypted container."""
import csv
import os
import secrets

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I


def new_code(prefix="R", n=4):
    return f"{prefix}-" + "".join(secrets.choice(ALPHABET) for _ in range(n))


def assign(map_path, real_name, email, orcid="", prefix="R"):
    existing = {}
    if os.path.exists(map_path):
        with open(map_path, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                existing[row["email"].lower()] = row["pseudonym"]
    if email.lower() in existing:
        return existing[email.lower()], False
    taken = set(existing.values())
    code = new_code(prefix)
    while code in taken:
        code = new_code(prefix)
    new_file = not os.path.exists(map_path)
    os.makedirs(os.path.dirname(map_path) or ".", exist_ok=True)
    with open(map_path, "a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        if new_file:
            w.writerow(["pseudonym", "real_name", "email", "orcid"])
        w.writerow([code, real_name, email, orcid])
    return code, True
