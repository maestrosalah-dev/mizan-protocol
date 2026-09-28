"""Conflict-of-interest screening on PRIVATE data; outputs PUBLIC pseudonyms.

reviewers CSV columns:
  pseudonym, orcid, institution, coauthor_orcids, supervision_orcids, funding_ids
  (multi-valued fields separated by ';', co-authors limited to the last 5 years)
author JSON:
  {"orcids": [...], "institutions": [...], "funding_ids": [...],
   "declared_competitors": [...pseudonyms or orcids...]}
"""
import csv
import json


def _split(v):
    return {x.strip() for x in (v or "").split(";") if x.strip()}


def screen(reviewers_csv, author_json):
    with open(author_json, encoding="utf-8") as fh:
        a = json.load(fh)
    a_orcids = set(a.get("orcids", []))
    a_inst = {i.strip().lower() for i in a.get("institutions", []) if i.strip()}
    a_fund = set(a.get("funding_ids", []))
    competitors = set(a.get("declared_competitors", []))

    eligible, excluded = [], []
    with open(reviewers_csv, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            reasons = []
            inst = (r.get("institution") or "").strip().lower()
            if r["orcid"] in a_orcids:
                reasons.append("is an author")
            if inst and inst in a_inst:
                reasons.append("same institution")
            if _split(r.get("coauthor_orcids")) & a_orcids:
                reasons.append("co-author within 5 years")
            if _split(r.get("supervision_orcids")) & a_orcids:
                reasons.append("supervision relationship")
            if _split(r.get("funding_ids")) & a_fund:
                reasons.append("shared funding")
            if r["pseudonym"] in competitors or r["orcid"] in competitors:
                reasons.append("declared direct competitor")
            if reasons:
                excluded.append((r["pseudonym"], reasons))
            else:
                eligible.append(r["pseudonym"])
    return eligible, excluded
