"""Block 4. Change one thing nobody would flag in review, and measure it.

    python 03_sensitivity.py --variant role --replay
    python 03_sensitivity.py --variant english_only

Fifteen minutes, one variant per group, so that the plenary has four results
instead of one. Your instructor will assign you one.

The point of this block is not which variant wins. It is that a change no
reviewer would comment on moves a measured number, which is why a prompt is
a versioned artifact and why "I improved the prompt" is not a claim anybody
should accept without a table.

One TODO marker.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

from documents import DOCS, EXAMPLE_POOL, GOLD
from extractor import SYSTEM_ZERO_SHOT, get_client, run_variant
from scoring import compare

from project.trace import write_json

VARIANTS = ("baseline", "role", "reordered", "no_delimiter", "english_only")


# --------------------------------------------------------------------------
# TODO 8. Build one variant and measure it against your few-shot baseline.
# --------------------------------------------------------------------------

def build_system(variant: str) -> str:
    """Return the system prompt for one variant.

    Start from your few-shot prompt from block 3, and change exactly one
    thing. Not two. The whole value of this block is that only one thing
    moved.

    baseline       your few-shot prompt from block 3, unchanged
    role           prepend "You are a senior service desk analyst." and
                   nothing else. On a task with closed label sets and a
                   schema, a persona usually buys close to nothing and costs
                   tokens on every call. If you find otherwise, that is a
                   genuinely interesting result worth reporting.
    reordered      the same examples in a different order. Nothing about the
                   task changed. Predict the effect before you run it, then
                   write down whether you were right.
    no_delimiter   remove whatever separates the document from the
                   instruction. Watch what happens on the longer messages.
                   This one is a preview of week 12: if the model cannot
                   tell your instruction from the data, neither can your
                   defenses.
    english_only   replace your non-English examples with English ones,
                   keeping the same count. Then read the score per language
                   as well as overall. Be careful here: the story you expect
                   is that non-English documents suffer, and the corpus has
                   five, three, and two documents per language, which is not
                   enough to support that claim even if the numbers point
                   that way. Report what moved, and say what sample would be
                   needed to attribute it. Week 13 asks who a system works
                   for, and this is what it costs to answer with evidence.
    """
    baseline = SYSTEM_ZERO_SHOT + "\n" + _few_shot_block()
    if variant == "baseline":
        return baseline
    if variant == "role":
        return "You are a senior service desk analyst.\n" + baseline
    if variant == "reordered":
        return _with_block(list(reversed(_CHOSEN)), labeled=True)
    if variant == "no_delimiter":
        return _with_block(_CHOSEN, labeled=False)
    if variant == "english_only":
        # EXAMPLE_POOL has three English messages. The fourth slot repeats
        # EX-01 so the block stays the same length as the baseline.
        return _with_block(_ENGLISH, labeled=True)
    raise ValueError(f"unknown variant {variant!r}")


# Same four examples, same verbatim quotes, as few_shot_block.
_CHOSEN = [
    ("EX-02", "L'ascenseur du batiment administratif est bloque entre le rez et le premier avec une personne a l'interieur."),
    ("EX-04", "For information only: the new intranet search will be switched on next week."),
    ("EX-05", "Nous avons recu deux fois la meme facture pour l'entretien des espaces verts, reference 2026-0417."),
    ("EX-01", "The badge reader at the side entrance rejects my card since the system update."),
]

_ENGLISH = [
    ("EX-01", "The badge reader at the side entrance rejects my card since the system update."),
    ("EX-04", "For information only: the new intranet search will be switched on next week."),
    ("EX-06", "The window in office 2.14 will not close and rain is coming in onto the shared printer below it."),
    ("EX-01", "The badge reader at the side entrance rejects my card since the system update."),
]


def _few_shot_block() -> str:
    path = Path(__file__).with_name("02_few_shot.py")
    spec = importlib.util.spec_from_file_location("week02_few_shot", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.few_shot_block()


def _with_block(items: list[tuple[str, str]], labeled: bool) -> str:
    by_id = {doc.id: (doc, gold) for doc, gold in EXAMPLE_POOL}
    lines = ["Examples. Follow these exactly, including the quote style."]
    for ex_id, quote in items:
        doc, gold = by_id[ex_id]
        if quote not in doc.text:
            raise ValueError(f"{ex_id} quote is not verbatim")
        record = json.dumps({
            "category": gold.category,
            "urgency": gold.urgency,
            "due_date": gold.due_date,
            "quote": quote,
        }, ensure_ascii=False)
        if labeled:
            lines.append(f"\nMessage: {doc.text}")
            lines.append("Record: " + record)
        else:
            lines.append(f"\n{doc.text}")
            lines.append(record)
    return SYSTEM_ZERO_SHOT + "\n" + "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=VARIANTS, required=True)
    ap.add_argument("--replay", action="store_true")
    args = ap.parse_args()

    client = get_client(args.replay)

    base = run_variant(client, build_system("baseline"), "baseline",
                       DOCS, GOLD)[0]
    if args.variant == "baseline":
        return 0
    other = run_variant(client, build_system(args.variant), args.variant,
                        DOCS, GOLD)[0]

    print(compare(base, other, "baseline", args.variant))

    # Per language, which is where the english_only variant shows its hand
    # and where an overall average would have hidden it entirely.
    for lang in ("en", "fr", "de"):
        ids = {d.id for d in DOCS if d.lang == lang}
        n = len(ids)
        print(f"  {lang}: {n} documents"
              f"   baseline field errors "
              f"{sum(1 for f in base.failures if f[0] in ids)}"
              f"   {args.variant} field errors "
              f"{sum(1 for f in other.failures if f[0] in ids)}")

    write_json(f"artifacts/week02_sensitivity_{args.variant}.json", {
        "variant": args.variant,
        "baseline_hits": base.hits, "variant_hits": other.hits,
    })

    # Write in DECISIONS.md: what you changed, what moved, and by how much.
    # If nothing moved, say so. A variant that changes nothing measurable is
    # a real result and it is worth reporting, because it tells the room
    # which knobs are worth arguing about and which are superstition.

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
