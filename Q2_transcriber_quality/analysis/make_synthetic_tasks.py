#!/usr/bin/env python3
"""
=============================================================================
  SYNTHETIC TRANSCRIPTION DATA - FOR PIPELINE TESTING ONLY
=============================================================================

Builds a fake task-level CSV matching the Question 2 schema so that
transcriber_quality.py can be exercised before the real dataset arrives.

!! NOTHING THIS PRODUCES IS EVIDENCE ABOUT ANY REAL TRANSCRIBER. !!

It plants several known behaviour profiles as a pipeline fixture. The small
number of users is not sufficient for the detector's default cohort-percentile
calibration, so this fixture does not validate review-queue recall.

Run:  python make_synthetic_tasks.py
Then: python transcriber_quality.py --data synthetic_tasks.csv
"""

import csv
import random
from pathlib import Path

random.seed(11)
OUT = Path(__file__).resolve().parent / "synthetic_tasks.csv"

HINDI = ["नमस्ते आप कैसे हैं", "मुझे कल बाजार जाना है", "यह कितने का है भैया",
         "आज मौसम बहुत अच्छा है", "मैंने खाना खा लिया", "ठीक है", "हाँ जी बिल्कुल",
         "वहाँ पर तीन सौ रुपये लगेंगे", "अगले हफ्ते मिलते हैं", "नहीं मुझे नहीं चाहिए"]

# answer key: behaviour -> expected detector verdict
PROFILES = {
    # honest workers, deliberately varied so the detector must not flag them
    "GOOD_hindi_laptop":   dict(n=90, listen=(1.6,0.45), edit_p=0.62, cosmetic_p=0.10,
                                lang="hindi", dev="laptop", bad=False),
    "GOOD_hindi_mobile":   dict(n=85, listen=(2.3,0.60), edit_p=0.66, cosmetic_p=0.12,
                                lang="hindi", dev="mobile", bad=False),
    "GOOD_bhojpuri_mobile":dict(n=80, listen=(3.1,0.80), edit_p=0.88, cosmetic_p=0.06,
                                lang="bhojpuri", dev="mobile", bad=False),
    "GOOD_bhoj_slow":      dict(n=75, listen=(3.6,0.90), edit_p=0.90, cosmetic_p=0.05,
                                lang="bhojpuri", dev="mobile", bad=False),
    "GOOD_hindi_fast":     dict(n=95, listen=(1.3,0.30), edit_p=0.45, cosmetic_p=0.15,
                                lang="hindi", dev="laptop", bad=False),
    "GOOD_hindi_careful":  dict(n=70, listen=(2.8,0.70), edit_p=0.80, cosmetic_p=0.04,
                                lang="hindi", dev="mobile", bad=False),
    "GOOD_bhoj_laptop":    dict(n=88, listen=(2.4,0.55), edit_p=0.84, cosmetic_p=0.08,
                                lang="bhojpuri", dev="laptop", bad=False),
    "GOOD_hindi_mid":      dict(n=92, listen=(2.0,0.50), edit_p=0.70, cosmetic_p=0.11,
                                lang="hindi", dev="mobile", bad=False),

    # planted bad actors
    "BAD_rubberstamp":     dict(n=90, listen=(1.7,0.40), edit_p=0.04, cosmetic_p=0.0,
                                lang="hindi", dev="mobile", bad=True,
                                why="accepts almost everything; peers edit the same clips"),
    "BAD_speedrun":        dict(n=85, listen=(0.55,0.15), edit_p=0.35, cosmetic_p=0.85,
                                lang="hindi", dev="mobile", bad=True,
                                why="sub-realtime + cosmetic edits only"),
    "BAD_cosmetic":        dict(n=80, listen=(1.1,0.25), edit_p=0.95, cosmetic_p=0.92,
                                lang="hindi", dev="laptop", bad=True,
                                why="edits everything, but only punctuation"),
    "BAD_metronome":       dict(n=100, listen=None, fixed_time=9.0, edit_p=0.30,
                                cosmetic_p=0.70, lang="bhojpuri", dev="mobile", bad=True,
                                why="constant time regardless of clip length"),
    "BAD_deleter":         dict(n=70, listen=(0.7,0.2), edit_p=0.98, cosmetic_p=0.0,
                                truncate=True, lang="hindi", dev="mobile", bad=True,
                                why="truncates text to pass quickly"),
}

# shared clip pool so peer consensus (Signal 2) is computable
CLIPS = []
for i in range(260):
    txt = random.choice(HINDI)
    CLIPS.append({
        "url": f"https://cdn.example/audio/clip_{i:04d}.wav",
        "dur": round(random.uniform(3.0, 22.0), 2),
        "truth": txt,
        # whether an honest listener would need to edit this clip
        "needs_edit": random.random() < 0.72,
    })


def degrade(s):
    """Simulate a Whisper error an honest transcriber would fix."""
    subs = {"तीन": "आठ", "नहीं": "", "कल": "आज", "अच्छा": "अच्छी", "रुपये": "रुपए"}
    for k, v in subs.items():
        if k in s:
            return s.replace(k, v, 1)
    return s[:-2] if len(s) > 6 else s


def cosmetic(s):
    return s + random.choice([".", " ।", "  ", ","])


def main():
    rows = []
    for uid, p in PROFILES.items():
        clips = random.sample(CLIPS, min(p["n"], len(CLIPS)))
        for c in clips:
            whisper = degrade(c["truth"]) if c["needs_edit"] else c["truth"]

            if p.get("fixed_time"):
                tt = max(1.0, random.gauss(p["fixed_time"], 1.2))
            else:
                mu, sd = p["listen"]
                tt = max(1.0, c["dur"] * max(0.2, random.gauss(mu, sd)))

            if random.random() < p["edit_p"]:
                if p.get("truncate"):
                    user = whisper[: max(2, int(len(whisper) * random.uniform(0.3, 0.55)))]
                elif random.random() < p["cosmetic_p"]:
                    user = cosmetic(whisper)
                else:
                    user = c["truth"]
            else:
                user = whisper

            nonspace = len(user.replace(" ", ""))
            rows.append({
                "user_id": uid,
                "recording_url": c["url"],
                "whisper_text": whisper,
                "user_text": user,
                "is_edited": "Yes" if user != whisper else "No",
                "duration": round(c["dur"], 2),
                "time_taken_by_user": round(tt, 2),
                "segment_character_per_second": round(nonspace / tt, 3),
                "language": p["lang"],
                "device_class": p["dev"],
                "task_type": "free_speech",
            })

    random.shuffle(rows)
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {len(rows)} SYNTHETIC rows to {OUT.name}\n")
    print("PLANTED PROFILES — these are test labels, not detector guarantees:")
    for uid, p in PROFILES.items():
        if p.get("bad"):
            print(f"  {uid:<22} {p['why']}")
    print("\nThe fixture has too few users per language/device cohort for reliable")
    print("percentile calibration. No flags under the default cohort settings is a")
    print("safe abstention, not proof of detector sensitivity.\n")
    print("NOTE: no honeypot column here, so the detector will correctly refuse to")
    print("recommend blocking anyone — which is the designed behaviour, not a bug.")


if __name__ == "__main__":
    main()
