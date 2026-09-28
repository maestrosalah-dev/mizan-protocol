import json
import os
import tempfile
import unittest
from datetime import date

from mizan import coi, draw, oplog, schedule

NAMES = [f"R-{c}" for c in "ABCDEFGHJK"]
RAND = "a" * 64


def _w(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


class DrawTests(unittest.TestCase):
    def test_order_independent_of_input_order(self):
        self.assertEqual(draw.rank(NAMES, RAND, "P1"), draw.rank(list(reversed(NAMES)), RAND, "P1"))

    def test_hash_ignores_order_and_whitespace(self):
        self.assertEqual(draw.list_hash(NAMES), draw.list_hash([" " + n + " " for n in reversed(NAMES)]))

    def test_request_id_changes_ranking(self):
        self.assertNotEqual(draw.rank(NAMES, RAND, "P1"), draw.rank(NAMES, RAND, "P2"))

    def test_duplicates_rejected(self):
        with self.assertRaises(ValueError):
            draw.list_hash(["R-A", "R-A"])

    def test_commit_draw_verify_roundtrip(self):
        info = {"genesis_time": 1_000_000, "period": 30}
        c = draw.make_commit(NAMES, "P1", 24, now=2_000_000, info=info)
        self.assertEqual(c["drand_round"], (2_000_000 + 86_400 - 1_000_000) // 30 + 1)
        r = draw.make_draw(c, NAMES, RAND, 3)
        self.assertEqual(len(r["selected"]), 3)
        self.assertEqual(len(r["replacement_queue"]), 7)
        self.assertEqual(draw.verify_draw(r, NAMES), (True, "draw verified"))

    def test_tampered_list_or_result_fails(self):
        info = {"genesis_time": 0, "period": 30}
        c = draw.make_commit(NAMES, "P1", 24, now=100, info=info)
        with self.assertRaises(ValueError):
            draw.make_draw(c, NAMES + ["R-Z"], RAND, 3)
        r = draw.make_draw(c, NAMES, RAND, 3)
        r["selected"] = list(reversed(r["selected"]))
        self.assertFalse(draw.verify_draw(r, NAMES)[0])

    def test_weighted_rank_deterministic_and_complete(self):
        w = {n: (2.0 if i < 3 else 1.0) for i, n in enumerate(NAMES)}
        a = draw.weighted_rank(w, RAND, "F1")
        self.assertEqual(a, draw.weighted_rank(w, RAND, "F1"))
        self.assertEqual(sorted(a), sorted(NAMES))


class LogTests(unittest.TestCase):
    def test_chain_detects_edit_and_deletion(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "log.jsonl")
            for i in range(3):
                oplog.append(p, "action", "P1", "coordinator", f"step{i}", now="2026-01-01T00:00:00Z")
            self.assertTrue(oplog.verify(p)[0])
            with open(p, encoding="utf-8") as fh:
                lines = fh.read().splitlines()
            e = json.loads(lines[1]); e["action"] = "edited"
            _w(p, "\n".join([lines[0], json.dumps(e), lines[2]]) + "\n")
            self.assertFalse(oplog.verify(p)[0])
            _w(p, "\n".join([lines[0], lines[2]]) + "\n")
            self.assertFalse(oplog.verify(p)[0])

    def test_deviation_requires_reason(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                oplog.append(os.path.join(d, "l"), "deviation", "P1", "c", "extend")


class CoiTests(unittest.TestCase):
    def test_screen(self):
        with tempfile.TemporaryDirectory() as d:
            rv = os.path.join(d, "r.csv"); au = os.path.join(d, "a.json")
            _w(rv, 
                "pseudonym,orcid,institution,coauthor_orcids,supervision_orcids,funding_ids\n"
                "R-A,0000-1,Univ X,,,\n"
                "R-B,0000-2,Univ Y,0000-9,,\n"
                "R-C,0000-3,Univ Z,,,\n")
            _w(au, json.dumps({"orcids": ["0000-9"], "institutions": ["univ x"]}))
            eligible, excluded = coi.screen(rv, au)
            self.assertEqual(eligible, ["R-C"])
            self.assertEqual({p for p, _ in excluded}, {"R-A", "R-B"})


class ScheduleTests(unittest.TestCase):
    def test_limit_is_day_38(self):
        last = schedule.plan(date(2026, 11, 1))[-1]
        self.assertEqual((last[0], last[1]), (date(2026, 12, 9), 38))


if __name__ == "__main__":
    unittest.main()
