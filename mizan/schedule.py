"""Right-to-Evaluation schedule for one request (protocol section 3).

Day 0 request, day 3 draw (M0). Escalation days count from the draw, so the
35-day guarantee ends on day 38 of the request.
"""
from datetime import date, timedelta

STAGES = [
    (0, "request received; completeness check"),
    (2, "audit done; candidate list committed (hash + drand round)"),
    (3, "M0: draw, 3 invitations, 5 days to accept"),
    (8, "M1: replace each decline/silence from the queue"),
    (13, "M2: widen to top 30 incl. adjacent fields, double reward"),
    (18, "M3: assign an on-call guaranteed reviewer (accept within 48h)"),
    (38, "LIMIT: fewer than 2 reviews -> 'Right-to-Evaluation failure'"),
]


def plan(submitted: date):
    return [(submitted + timedelta(days=d), d, label) for d, label in STAGES]


def response_deadlines(reviews_published: date, extension=False):
    author = reviews_published + timedelta(days=30 + (15 if extension else 0))
    verdict = author + timedelta(days=14)
    return author, verdict
