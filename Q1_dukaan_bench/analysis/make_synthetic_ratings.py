#!/usr/bin/env python3
"""
=============================================================================
  SYNTHETIC DATA GENERATOR - FOR PIPELINE TESTING ONLY
=============================================================================

This script invents fake ratings so that analyze.py and the dashboard can be
tested BEFORE any real participants are run.

!! NOTHING THIS SCRIPT PRODUCES IS A RESULT. !!

Every file it writes is prefixed `SYNTHETIC_`. Delete the whole
`responses_synthetic/` directory before you put real data in, so there is zero
chance of a fabricated row reaching the submission.

The generating assumptions below are a PRIOR - a guess about what we expect to
find, written down in advance so we can see later whether reality matched. They
are not evidence of anything.

Run:  python make_synthetic_ratings.py
"""

import csv
import random
from pathlib import Path

random.seed(7)

OUT = Path(__file__).resolve().parent.parent / "rating" / "responses_synthetic"

MODELS = ["gpt_image_1", "gemini_2_5_flash_image", "gemini_3_1_flash_image_preview"]
PROMPTS = [
    ("P01", "Devanagari", "Hindi"),          ("P02", "Devanagari", "Hindi"),
    ("P03", "Devanagari", "Hindi + English"),("P04", "Devanagari", "Hindi"),
    ("P05", "Tamil", "Tamil"),               ("P06", "Bengali", "Bengali"),
    ("P07", "Gurmukhi", "Punjabi"),          ("P08", "Telugu", "Telugu"),
    ("P09", "Urdu", "Urdu"),                 ("P10", "Latin", "English"),
]

# PRIOR, not data: Latin text is largely solved; Devanagari is partially there;
# lower-resource scripts and RTL Nastaliq are expected to collapse.
TF_PRIOR = {
    "Latin":      {"gpt_image_1": 2.7, "gemini_2_5_flash_image": 2.5, "gemini_3_1_flash_image_preview": 2.8},
    "Devanagari": {"gpt_image_1": 1.1, "gemini_2_5_flash_image": 0.9, "gemini_3_1_flash_image_preview": 1.6},
    "Tamil":      {"gpt_image_1": 0.5, "gemini_2_5_flash_image": 0.4, "gemini_3_1_flash_image_preview": 0.9},
    "Bengali":    {"gpt_image_1": 0.4, "gemini_2_5_flash_image": 0.3, "gemini_3_1_flash_image_preview": 0.8},
    "Gurmukhi":   {"gpt_image_1": 0.3, "gemini_2_5_flash_image": 0.2, "gemini_3_1_flash_image_preview": 0.5},
    "Telugu":     {"gpt_image_1": 0.3, "gemini_2_5_flash_image": 0.3, "gemini_3_1_flash_image_preview": 0.6},
    "Urdu":       {"gpt_image_1": 0.2, "gemini_2_5_flash_image": 0.2, "gemini_3_1_flash_image_preview": 0.3},
}
CA_PRIOR = {"gpt_image_1": 2.0, "gemini_2_5_flash_image": 1.9, "gemini_3_1_flash_image_preview": 2.2}
CU_PRIOR = {"gpt_image_1": 2.4, "gemini_2_5_flash_image": 2.1, "gemini_3_1_flash_image_preview": 2.5}

RATERS = [
    ("R01", ["Devanagari", "Latin"]),            ("R02", ["Devanagari", "Latin"]),
    ("R03", ["Devanagari", "Urdu", "Latin"]),    ("R04", ["Tamil", "Latin"]),
    ("R05", ["Tamil", "Devanagari", "Latin"]),   ("R06", ["Bengali", "Latin"]),
    ("R07", ["Bengali", "Devanagari", "Latin"]), ("R08", ["Gurmukhi", "Devanagari", "Latin"]),
    ("R09", ["Telugu", "Latin"]),                ("R10", ["Devanagari", "Latin"]),
]

FIELDS = ["rater_id", "screen_index", "is_duplicate_check", "prompt_id", "script",
          "language", "position", "image_id", "model_key", "tf",
          "tf_skipped_cannot_read", "ca", "cu", "upr", "ca_tags",
          "h2h_winner", "h2h_choice", "screen_seconds", "comment"]


def clamp(v):
    return max(0, min(3, int(round(v))))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in OUT.glob("*.csv"):
        f.unlink()

    for rid, scripts in RATERS:
        bias = random.uniform(-0.35, 0.35)   # per-rater leniency
        order = PROMPTS[:]
        random.shuffle(order)
        order.append(PROMPTS[0])             # duplicate check

        rows = []
        for si, (pid, script, lang) in enumerate(order, start=1):
            panes = MODELS[:]
            random.shuffle(panes)

            cell = {}
            for pos, mk in zip("ABC", panes):
                can_read = script in scripts
                tf = clamp(random.gauss(TF_PRIOR[script][mk] + bias, 0.6))
                ca = clamp(random.gauss(CA_PRIOR[mk] + bias, 0.7))
                cu = clamp(random.gauss(CU_PRIOR[mk] + bias, 0.6))
                # A poster is only postable if the text is right AND it looks decent.
                upr = 1 if (tf >= 3 and cu >= 2 and ca >= 2 and random.random() < 0.8) else 0
                tags = []
                if ca <= 1 and script in ("Tamil", "Telugu", "Bengali") and random.random() < 0.45:
                    tags.append("rajasthan-default")
                if ca <= 1 and random.random() < 0.3:
                    tags.append("wrong-region")
                cell[pos] = dict(mk=mk, tf=tf if can_read else None,
                                 skipped=0 if can_read else 1,
                                 ca=ca, cu=cu, upr=upr, tags=tags)

            best = max("ABC", key=lambda p: (cell[p]["tf"] or 0) * 2 + cell[p]["cu"])
            choice = best if any(cell[p]["upr"] for p in "ABC") or random.random() < 0.35 else "none"

            for pos in "ABC":
                c = cell[pos]
                rows.append({
                    "rater_id": rid, "screen_index": si,
                    "is_duplicate_check": 1 if si == len(order) else 0,
                    "prompt_id": pid, "script": script, "language": lang,
                    "position": pos, "image_id": f"{pid}__{c['mk']}__run1",
                    "model_key": c["mk"],
                    "tf": "" if c["tf"] is None else c["tf"],
                    "tf_skipped_cannot_read": c["skipped"],
                    "ca": c["ca"], "cu": c["cu"], "upr": c["upr"],
                    "ca_tags": "|".join(c["tags"]),
                    "h2h_winner": 1 if choice == pos else 0,
                    "h2h_choice": choice,
                    "screen_seconds": random.randint(55, 190),
                    "comment": "",
                })

        with open(OUT / f"ratings_{rid}.csv", "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rows)

    print(f"Wrote {len(RATERS)} SYNTHETIC rating files to {OUT}")
    print("These are NOT results. Delete this directory before adding real data.")


if __name__ == "__main__":
    main()
