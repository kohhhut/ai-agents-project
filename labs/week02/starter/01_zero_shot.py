"""Block 2. The zero-shot baseline, scored per field.

    python 01_zero_shot.py --replay     # the shipped recording, instant
    python 01_zero_shot.py              # your own model, about 45 seconds

Develop your scorer against `--replay`. The recording holds every model
answer for both variants, so your scorer runs in well under a second and you
can iterate on it properly instead of waiting forty-five seconds to find out
you compared the wrong field.

The recording contains real failures, because the model really does make
them. If your scorer reports forty out of forty, your scorer does nothing.

One TODO marker here. TODO 1 to 4 live in extractor.py and scoring.py, and
this file will not run until they are done.
"""

from __future__ import annotations

import argparse

from documents import DOCS, GOLD
from extractor import (PROMPT_VERSION, SYSTEM_ZERO_SHOT, get_client,
                       run_variant)

from project.trace import write_json
from dataclasses import asdict
from project.contracts import GoldCase, GoldSet

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--replay", action="store_true")
    args = ap.parse_args()

    client = get_client(args.replay)
    board, records, metas = run_variant(client, SYSTEM_ZERO_SHOT,
                                        "zero-shot", DOCS, GOLD)

    if board.failures:
        print("failures worth reading:")
        for doc_id, fieldname, note in board.failures[:10]:
            print(f"  {doc_id}  {fieldname:<9} {note}")

    write_json("artifacts/week02_zero_shot.json", {
        "variant": "zero-shot",
        "prompt_version": PROMPT_VERSION,
        "hits": board.hits, "total": board.total, "invalid": board.invalid,
    })

    # TODO 7. Write the gold set into the project spine.
    #
    BEHAVIOR = {
        "REQ-01": "Extracts category access and urgency urgent, with no due date "
                  "because the message only says 'tomorrow' and 'today', which "
                  "are relative expressions, and quotes a span copied verbatim "
                  "from the message that supports the urgency.",
        "REQ-02": "Extracts category hardware and urgency standard, with due date "
                  "2026-09-15, because 15/09/2026 is a European DD/MM/YYYY date.",
        "REQ-03": "Extracts category billing and urgency standard, with no due "
                  "date, because the message says it is not urgent and gives no "
                  "date.",
        "REQ-04": "Extracts category facilities and urgency urgent, with no due "
                  "date, because the open entrance door needs someone "
                  "'immediately', which is not a calendar date.",
        "REQ-05": "Extracts category access and urgency standard, with no due "
                  "date, because the message says 'not urgent' and only "
                  "'before the end of the month', which is a relative "
                  "expression.",
        "REQ-06": "Extracts category billing and urgency info, with no due date, "
                  "because the message only informs the help desk and says no "
                  "action is needed.",
        "REQ-07": "Extracts category facilities and urgency standard, with due "
                  "date 2026-10-01, because '1. Oktober 2026' is a written "
                  "German calendar date.",
        "REQ-08": "Extracts category hardware and urgency urgent, with no due "
                  "date, because the file server is down and blocking the "
                  "whole team today, with no calendar date given.",
        "REQ-09": "Extracts category other and urgency info, with no due date, "
                  "because the message is only a suggestion and says it is not "
                  "a problem.",
        "REQ-10": "Extracts category access and urgency standard, with no due "
                  "date, because 'before the end of the month' is a relative "
                  "expression.",
    }

    cases = [
        GoldCase(
            case_id=doc.id,
            week_added=2,
            question=doc.text,
            expected=asdict(GOLD[doc.id]),
            expected_behavior=BEHAVIOR[doc.id],
            slice_tags=[doc.lang],
        )
        for doc in DOCS
    ]
    gold = GoldSet(cases=cases)
    write_json("artifacts/goldset.json", gold.model_dump(mode="json"))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
