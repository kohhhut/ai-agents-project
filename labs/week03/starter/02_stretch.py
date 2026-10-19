"""Block 4, completed. TODO 8. One variant per group.

    python 02_stretch.py --variant model --replay
    python 02_stretch.py --variant voting --replay

The written answers are at the bottom.
"""

from __future__ import annotations

import argparse
import collections
import time

from queries import QUERIES
from router import apply_policy, classify
from scoring import report, score_routes

from project.models import LARGE, SMALL
from project.trace import write_json

import importlib.util
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "compare_mod", Path(__file__).with_name("01_compare.py"))
_cmp = importlib.util.module_from_spec(_spec)
sys.modules["compare_mod"] = _cmp
_spec.loader.exec_module(_cmp)


# --------------------------------------------------------------------------
# TODO 8. One variant. Your instructor assigns you one.
# --------------------------------------------------------------------------

def variant_model(client) -> None:
    print("prediction: SMALL beats LARGE on routing and on verbatim evidence\n")
    for spec in (SMALL, LARGE):
        decisions = [classify(client, q.text, spec.name)[0] for q in QUERIES]
        routed = [apply_policy(d, q.text) for d, q in zip(decisions, QUERIES)]
        s = score_routes(routed, QUERIES)
        raw_hits = sum(1 for d, q in zip(decisions, QUERIES)
                       if d and d.route == q.route)
        print(report(s, f"{spec.name} (scored on applied route)"))
        print(f"  classifier alone, before the policy: {raw_hits}/{len(QUERIES)}")
        print(f"  resident memory: {spec.resident_gb} GB\n")
        write_json(f"artifacts/week03_model_{spec.name.replace(':', '_')}.json", {
            "model": spec.name, "hits": s.hits, "total": s.total,
            "unambiguous": [s.unambiguous_hits, s.unambiguous_total],
            "per_route": s.per_route, "raw_classifier_hits": raw_hits,
            "evidence_ok": s.evidence_ok,
            "confidence_min": min(s.confidences),
            "confidence_max": max(s.confidences),
            "confidence_distinct": len(set(s.confidences)),
            "confusion": {f"{g}->{p}": n for (g, p), n in s.confusion.items()},
            "policy_fired": dict(s.policy_fired),
            "resident_gb": spec.resident_gb})


def variant_voting(client, k: int = 3) -> None:
    from queries import AMBIGUOUS_IDS
    temperature = 0.7
    routed, split = [], []
    t0 = time.perf_counter()
    for q in QUERIES:
        votes = []
        for _ in range(k):                    # sequential on purpose
            decision, _meta = classify(client, q.text, SMALL.name,
                                       temperature=temperature)
            votes.append(decision)
        counts = collections.Counter(v.route for v in votes if v)
        if len({v.route for v in votes if v}) > 1 or None in votes:
            split.append(q.id)
        winner = counts.most_common(1)[0][0] if counts else None
        pick = next((v for v in votes if v and v.route == winner), None)
        routed.append(apply_policy(pick, q.text))
    secs = time.perf_counter() - t0
    s = score_routes(routed, QUERIES)
    print(report(s, f"majority of {k} at temperature {temperature}"))
    print(f"\n  queries where the {k} votes disagreed: {split or 'none'}")
    print(f"  ambiguous ids:                          {list(AMBIGUOUS_IDS)}")
    print(f"  {len(QUERIES) * k} classifying calls instead of {len(QUERIES)}, {secs:.1f}s")
    write_json("artifacts/week03_voting.json", {
        "model": SMALL.name, "temperature": temperature, "k": k,
        "hits": s.hits, "total": s.total, "split_votes": split,
        "ambiguous": list(AMBIGUOUS_IDS)})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=("model", "voting"), required=True)
    ap.add_argument("--replay", action="store_true")
    args = ap.parse_args()

    client = _cmp.get_client(args.replay)
    if args.variant == "model":
        variant_model(client)
    else:
        variant_voting(client)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
