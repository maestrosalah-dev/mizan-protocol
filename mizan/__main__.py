"""Command line: python -m mizan <command> --help"""
import argparse
import json
import sys
from datetime import date

from . import coi, draw, oplog, pseudonym, schedule


def _write_json(obj, path):
    text = json.dumps(obj, ensure_ascii=False, indent=2)
    if path:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    print(text)


def cmd_commit(a):
    names = draw.read_list(a.list)
    info = None
    if a.genesis is not None and a.period is not None:
        info = {"genesis_time": a.genesis, "period": a.period}
    _write_json(draw.make_commit(names, a.request, a.delay_hours, info=info), a.out)
    print("\nPublish this commit file BEFORE the drand round above is released.", file=sys.stderr)


def cmd_draw(a):
    with open(a.commit, encoding="utf-8") as fh:
        commit = json.load(fh)
    names = draw.read_list(a.list)
    randomness = a.randomness or draw.drand_randomness(commit["drand_round"])
    _write_json(draw.make_draw(commit, names, randomness, a.k), a.out)


def cmd_verify(a):
    with open(a.draw, encoding="utf-8") as fh:
        result = json.load(fh)
    ok, msg = draw.verify_draw(result, draw.read_list(a.list))
    if ok and a.check_beacon:
        live = draw.drand_randomness(result["drand_round"])
        if live != result["randomness"]:
            ok, msg = False, "randomness does not match the public drand round"
    print(("OK: " if ok else "FAIL: ") + msg)
    sys.exit(0 if ok else 1)


def cmd_coi(a):
    eligible, excluded = coi.screen(a.reviewers, a.author)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write("\n".join(sorted(eligible)) + "\n")
    print(f"eligible: {len(eligible)}  excluded: {len(excluded)}")
    for p, reasons in excluded:
        print(f"  excluded {p}: {', '.join(reasons)}")


def cmd_pseudonym(a):
    code, created = pseudonym.assign(a.map, a.name, a.email, a.orcid, a.prefix)
    print(code if created else f"{code} (already assigned)")
    if a.log:
        oplog.append(a.log, "identity_access", "-", a.actor, "assign_pseudonym",
                     output=code, reason="registration")


def cmd_log(a):
    if a.log_cmd == "add":
        e = oplog.append(a.file, a.kind, a.request, a.actor, a.action, a.rule,
                         a.input, a.output, a.manual, a.reason)
        print(f"#{e['seq']} {e['hash'][:12]}")
    elif a.log_cmd == "verify":
        ok, msg = oplog.verify(a.file)
        print(("OK: " if ok else "FAIL: ") + msg)
        sys.exit(0 if ok else 1)
    else:
        print(json.dumps(oplog.summary(a.file), indent=2))


def cmd_schedule(a):
    d = date.fromisoformat(a.submitted)
    for when, day, label in schedule.plan(d):
        print(f"{when.isoformat()}  day {day:>2}  {label}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="mizan", description="Mizan protocol tooling")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("commit", help="freeze a candidate list and bind it to a future drand round")
    s.add_argument("--list", required=True)
    s.add_argument("--request", required=True)
    s.add_argument("--delay-hours", type=float, default=24.0)
    s.add_argument("--genesis", type=int, help="offline: drand genesis_time")
    s.add_argument("--period", type=int, help="offline: drand period (seconds)")
    s.add_argument("--out")
    s.set_defaults(func=cmd_commit)

    s = sub.add_parser("draw", help="rank candidates with the committed round's randomness")
    s.add_argument("--commit", required=True)
    s.add_argument("--list", required=True)
    s.add_argument("--k", type=int, default=3)
    s.add_argument("--randomness", help="paste the round's randomness if offline")
    s.add_argument("--out")
    s.set_defaults(func=cmd_draw)

    s = sub.add_parser("verify", help="anyone: recompute a published draw")
    s.add_argument("--draw", required=True)
    s.add_argument("--list", required=True)
    s.add_argument("--check-beacon", action="store_true", help="also re-fetch the drand round")
    s.set_defaults(func=cmd_verify)

    s = sub.add_parser("coi", help="screen reviewers against an author (private data)")
    s.add_argument("--reviewers", required=True)
    s.add_argument("--author", required=True)
    s.add_argument("--out", help="write eligible pseudonyms, one per line")
    s.set_defaults(func=cmd_coi)

    s = sub.add_parser("pseudonym", help="assign a stable pseudonym (private map)")
    s.add_argument("--map", default="private/identity_map.csv")
    s.add_argument("--name", required=True)
    s.add_argument("--email", required=True)
    s.add_argument("--orcid", default="")
    s.add_argument("--prefix", default="R")
    s.add_argument("--log", help="operator log to record the identity access in")
    s.add_argument("--actor", default="coordinator")
    s.set_defaults(func=cmd_pseudonym)

    s = sub.add_parser("log", help="tamper-evident operator log")
    ls = s.add_subparsers(dest="log_cmd", required=True)
    add = ls.add_parser("add")
    add.add_argument("--file", default="logs/operator_log.jsonl")
    add.add_argument("--kind", choices=sorted(oplog.KINDS), default="action")
    add.add_argument("--request", required=True)
    add.add_argument("--actor", default="coordinator")
    add.add_argument("--action", required=True)
    add.add_argument("--rule", default="")
    add.add_argument("--input", default="")
    add.add_argument("--output", default="")
    add.add_argument("--manual", action="store_true", help="manual discretion was used")
    add.add_argument("--reason", default="")
    for name in ("verify", "summary"):
        x = ls.add_parser(name)
        x.add_argument("--file", default="logs/operator_log.jsonl")
    s.set_defaults(func=cmd_log)

    s = sub.add_parser("schedule", help="Right-to-Evaluation dates for a request")
    s.add_argument("--submitted", required=True, help="YYYY-MM-DD")
    s.set_defaults(func=cmd_schedule)

    a = p.parse_args(argv)
    try:
        a.func(a)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
