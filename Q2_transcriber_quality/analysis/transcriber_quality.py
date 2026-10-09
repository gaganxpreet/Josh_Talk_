#!/usr/bin/env python3
"""
Transcriber quality analysis - Josh Talks AI, Question 2.

Computes every signal in 01_PART_I_warning_signs.md from the task-level CSV, and
- critically - CALIBRATES THRESHOLDS FROM THE OBSERVED DISTRIBUTION rather than
hardcoding the provisional numbers in the document.

    python transcriber_quality.py --data tasks.csv
    python transcriber_quality.py --data tasks.csv --cohort-cols language,device_class
    python transcriber_quality.py --data tasks.csv --json out.json

Expected columns (missing ones degrade gracefully, and are reported):
    user_id, recording_url, whisper_text, user_text, is_edited,
    duration, time_taken_by_user, segment_character_per_second
Optional, strongly recommended (see Part II s7):
    language, device_class, task_type, playback_speed_used, is_honeypot

Standard library only.

-----------------------------------------------------------------------------
READ THIS BEFORE USING THE OUTPUT
-----------------------------------------------------------------------------
This script produces FLAGS FOR REVIEW. It does not produce block decisions.
Per Part II, no account should be blocked on these numbers alone - they measure
effort, not accuracy, and the only clean blocking signal is a failed honeypot
with a known answer.

The script enforces that stance: it prints a review queue, and it refuses to
emit anything labelled as a block recommendation.
-----------------------------------------------------------------------------
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics as st
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# tunables - structural, not calibrated. Percentile-based gates do the real work.
# ---------------------------------------------------------------------------
MIN_TASKS            = 30     # below this, report insufficient_data (Part II s3)
MIN_DURATION_S       = 4.0    # exclude clips where UI overhead swamps the ratio
MIN_PEERS_FOR_CONSENSUS = 3
CONSENSUS_EDIT_GATE  = 0.70
MIN_EDIT_FOR_RATE    = 20     # chars, before trusting effective_edit_rate
SUB_REALTIME_GATE    = 0.9    # listen_ratio below this = could not have listened
FLAG_PERCENTILE      = 5.0    # "bottom 5% of cohort"


# ---------------------------------------------------------------------------
# text helpers
# ---------------------------------------------------------------------------

_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)


def norm_unicode(s: str) -> str:
    """NFC-normalise. Without this, legitimate nukta/ZWJ fixes look like no-ops."""
    return unicodedata.normalize("NFC", s or "")


def strip_cosmetic(s: str) -> str:
    """Remove punctuation, collapse whitespace, casefold."""
    s = norm_unicode(s)
    s = _PUNCT.sub("", s)
    return re.sub(r"\s+", " ", s).strip().casefold()


def levenshtein(a: str, b: str, cap: int = 4000) -> int:
    """Iterative two-row Levenshtein. Truncates pathological inputs."""
    a, b = norm_unicode(a)[:cap], norm_unicode(b)[:cap]
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def indel_split(a: str, b: str, cap: int = 4000) -> tuple[int, int]:
    """
    Rough insertion/deletion decomposition via LCS length.

    Part I, Signal 5: deleting a long Whisper hallucination is one keystroke but a
    huge edit distance. Without separating insertions from deletions, the
    throughput metric flags the single most valuable edit a transcriber makes.
    """
    a, b = norm_unicode(a)[:cap], norm_unicode(b)[:cap]
    if not a or not b:
        return (len(b), len(a))
    prev = [0] * (len(b) + 1)
    for ca in a:
        cur = [0]
        for j, cb in enumerate(b, 1):
            cur.append(prev[j - 1] + 1 if ca == cb else max(prev[j], cur[j - 1]))
        prev = cur
    lcs = prev[-1]
    return (len(b) - lcs, len(a) - lcs)   # inserted, deleted


# ---------------------------------------------------------------------------
# stats helpers
# ---------------------------------------------------------------------------

def pctile(xs, p):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    if len(xs) == 1:
        return xs[0]
    k = (len(xs) - 1) * (p / 100.0)
    lo, hi = math.floor(k), math.ceil(k)
    return xs[lo] if lo == hi else xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def spearman(xs, ys):
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 10:
        return None

    def rank(vs):
        order = sorted(range(len(vs)), key=lambda i: vs[i])
        r = [0.0] * len(vs)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and vs[order[j + 1]] == vs[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    rx, ry = rank([p[0] for p in pairs]), rank([p[1] for p in pairs])
    n = len(pairs)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return round(num / den, 3) if den else None


def safe_med(xs):
    xs = [x for x in xs if x is not None]
    return round(st.median(xs), 3) if xs else None


# ---------------------------------------------------------------------------
# load + per-task derivation
# ---------------------------------------------------------------------------

def num(v):
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def load(path: Path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise SystemExit("Empty file.")

    present = set(rows[0].keys())
    required = {"user_id", "recording_url", "whisper_text", "user_text",
                "is_edited", "duration", "time_taken_by_user"}
    missing = required - present
    if missing:
        print(f"WARNING missing required columns: {sorted(missing)}", file=sys.stderr)

    optional = {"language", "device_class", "task_type",
                "playback_speed_used", "is_honeypot"}
    absent_opt = sorted(optional - present)

    for r in rows:
        w, u = norm_unicode(r.get("whisper_text", "")), norm_unicode(r.get("user_text", ""))
        dur, tt = num(r.get("duration")), num(r.get("time_taken_by_user"))

        r["_w"], r["_u"] = w, u
        r["_dur"], r["_tt"] = dur, tt
        r["_listen_ratio"] = (tt / dur) if (dur and dur > 0 and tt is not None) else None
        r["_usable_ratio"] = r["_listen_ratio"] if (dur or 0) >= MIN_DURATION_S else None

        flag = str(r.get("is_edited", "")).strip().lower()
        declared = flag in ("yes", "y", "true", "1")
        actually = (w != u)
        r["_declared_edited"] = declared
        r["_actually_edited"] = actually
        r["_flag_mismatch"] = declared != actually

        if actually:
            d = levenshtein(w, u)
            ins, dele = indel_split(w, u)
        else:
            d, ins, dele = 0, 0, 0
        r["_edit_distance"], r["_ins"], r["_del"] = d, ins, dele
        r["_norm_edit"] = d / max(1, len(w))
        r["_is_cosmetic"] = actually and (strip_cosmetic(w) == strip_cosmetic(u))
        r["_len_ratio"] = len(u) / max(1, len(w))
        r["_empty"] = len(u.strip()) == 0

        window = max(1.0, (tt - dur)) if (tt is not None and dur is not None) else None
        r["_eff_edit_rate"] = (ins / window) if (window and ins >= MIN_EDIT_FOR_RATE) else None

        # recompute the supplied CPS column to check its definition matches the brief
        nonspace = len(re.sub(r"\s", "", u))
        r["_cps_recomputed"] = (nonspace / tt) if (tt and tt > 0) else None
        r["_cps_given"] = num(r.get("segment_character_per_second"))

    return rows, absent_opt


# ---------------------------------------------------------------------------
# peer consensus (Signal 2)
# ---------------------------------------------------------------------------

def build_consensus(rows):
    by_clip = defaultdict(list)
    for r in rows:
        by_clip[r.get("recording_url", "")].append(r)

    overlapping = {k: v for k, v in by_clip.items()
                   if len({x["user_id"] for x in v}) > MIN_PEERS_FOR_CONSENSUS}
    consensus = {}
    for url, rs in by_clip.items():
        per_user = {}
        for r in rs:
            per_user.setdefault(r["user_id"], r["_actually_edited"])
        consensus[url] = per_user

    return consensus, {
        "clips_total": len(by_clip),
        "clips_with_overlap": len(overlapping),
        "overlap_share": round(len(overlapping) / max(1, len(by_clip)), 4),
        "available": len(overlapping) >= 20,
    }


# ---------------------------------------------------------------------------
# per-user metrics
# ---------------------------------------------------------------------------

def per_user(rows, consensus):
    by_user = defaultdict(list)
    for r in rows:
        by_user[r["user_id"]].append(r)

    out = {}
    for uid, rs in by_user.items():
        n = len(rs)
        ratios = [r["_usable_ratio"] for r in rs if r["_usable_ratio"] is not None]
        sub = [r for r in rs if r["_usable_ratio"] is not None
               and r["_usable_ratio"] < SUB_REALTIME_GATE]
        edited = [r for r in rs if r["_actually_edited"]]

        # Signal 2 - anomalous deference
        adr, adr_n = None, 0
        accepted_hard = 0
        for r in rs:
            if r["_actually_edited"]:
                continue
            peers = consensus.get(r.get("recording_url", ""), {})
            others = [v for k, v in peers.items() if k != uid]
            if len(others) >= MIN_PEERS_FOR_CONSENSUS:
                adr_n += 1
                if sum(others) / len(others) >= CONSENSUS_EDIT_GATE:
                    accepted_hard += 1
        if adr_n >= 10:
            adr = round(accepted_hard / adr_n, 4)

        # Signal 6 - self-duplication across DIFFERENT clips
        seen, dup = defaultdict(set), 0
        for r in rs:
            key = strip_cosmetic(r["_u"])
            if key and r.get("recording_url") not in seen[key]:
                if seen[key]:
                    dup += 1
                seen[key].add(r.get("recording_url"))

        cps_dev = [abs(r["_cps_given"] - r["_cps_recomputed"])
                   for r in rs if r["_cps_given"] is not None
                   and r["_cps_recomputed"] is not None]

        out[uid] = {
            "user_id": uid,
            "n_tasks": n,
            "sufficient_data": n >= MIN_TASKS,
            "language": rs[0].get("language", "unknown"),
            "device_class": rs[0].get("device_class", "unknown"),
            "task_type": rs[0].get("task_type", "unknown"),

            "median_listen_ratio": safe_med(ratios),
            "sub_realtime_rate": round(len(sub) / max(1, len(ratios)), 4) if ratios else None,
            "accept_rate": round(sum(1 for r in rs if not r["_actually_edited"]) / n, 4),
            "adr": adr,
            "adr_n": adr_n,
            "cosmetic_share": (round(sum(1 for r in edited if r["_is_cosmetic"]) / len(edited), 4)
                               if edited else None),
            "median_norm_edit": safe_med([r["_norm_edit"] for r in edited]) if edited else None,
            "audio_sensitivity": spearman([r["_dur"] for r in rs], [r["_tt"] for r in rs]),
            "duration_iqr": (round((pctile([r["_dur"] for r in rs], 75) or 0)
                                   - (pctile([r["_dur"] for r in rs], 25) or 0), 2)),
            "median_eff_edit_rate": safe_med([r["_eff_edit_rate"] for r in rs]),
            "self_dup_rate": round(dup / n, 4),
            "median_len_ratio": safe_med([r["_len_ratio"] for r in rs]),
            "empty_rate": round(sum(1 for r in rs if r["_empty"]) / n, 4),
            "flag_mismatch_rate": round(sum(1 for r in rs if r["_flag_mismatch"]) / n, 4),
            "cps_column_max_deviation": round(max(cps_dev), 3) if cps_dev else None,
        }
    return out


# ---------------------------------------------------------------------------
# cohort-relative flagging (Part I s3 - the confounder that outranks all signals)
# ---------------------------------------------------------------------------

SIGNALS = [
    # (metric, direction, label, tier)  direction=-1 -> LOW values are bad
    ("sub_realtime_rate",   +1, "Sub-realtime completion",   "A"),
    ("adr",                 +1, "Anomalous deference",       "A"),
    ("cosmetic_share",      +1, "Cosmetic-only editing",     "B"),
    ("audio_sensitivity",   -1, "Audio insensitivity",       "B"),
    ("median_eff_edit_rate",+1, "Implausible throughput",    "C"),
    ("self_dup_rate",       +1, "Degenerate output",         "C"),
]


def flag(users, cohort_cols):
    cohorts = defaultdict(list)
    for u in users.values():
        key = tuple(u.get(c, "unknown") for c in cohort_cols) if cohort_cols else ("all",)
        u["_cohort"] = " / ".join(map(str, key))
        cohorts[u["_cohort"]].append(u)

    calibration = {}
    for cname, members in cohorts.items():
        eligible = [m for m in members if m["sufficient_data"]]
        calibration[cname] = {"n_users": len(members), "n_eligible": len(eligible),
                              "thresholds": {}}
        if len(eligible) < 10:
            # Too few peers for a percentile to mean anything. Say so; don't guess.
            for m in members:
                m["flags"] = []
                m["note"] = (f"cohort '{cname}' has only {len(eligible)} eligible user(s) - "
                             "too few for percentile calibration; no flags raised")
            continue

        for metric, direction, label, tier in SIGNALS:
            vals = [m[metric] for m in eligible if m.get(metric) is not None]
            if len(vals) < 10:
                continue
            cut = pctile(vals, 100 - FLAG_PERCENTILE if direction > 0 else FLAG_PERCENTILE)
            calibration[cname]["thresholds"][metric] = {
                "cut": round(cut, 4) if cut is not None else None,
                "direction": "high is bad" if direction > 0 else "low is bad",
                "cohort_median": safe_med(vals),
                "tier": tier,
            }
            for m in members:
                v = m.get(metric)
                if v is None or not m["sufficient_data"]:
                    continue
                if (direction > 0 and v > cut) or (direction < 0 and v < cut):
                    # Signal 4 is meaningless without duration spread (Part I)
                    if metric == "audio_sensitivity" and (m["duration_iqr"] or 0) < 3:
                        continue
                    m.setdefault("flags", []).append(
                        {"signal": label, "tier": tier, "metric": metric,
                         "value": v, "cohort_cut": round(cut, 4)})

    for m in users.values():
        m.setdefault("flags", [])
        m["n_flags"] = len(m["flags"])
        m["tier_a_flags"] = sum(1 for f in m["flags"] if f["tier"] == "A")

    return calibration


def review_queue(users):
    """
    Routing output ONLY. Deliberately named 'review', and deliberately emits no
    block recommendation - per Part II, a block needs honeypot evidence plus a
    human, neither of which exists in this dataset.
    """
    q = []
    for u in users.values():
        if not u["sufficient_data"] or not u["flags"]:
            continue
        if u["tier_a_flags"] >= 2 and u["n_flags"] >= 3:
            action, why = "T3_SUSPEND_PENDING_HUMAN_REVIEW", "2+ Tier-A signals, 3+ total"
        elif u["tier_a_flags"] >= 1 and u["n_flags"] >= 2:
            action, why = "T2_THROTTLE_AND_ESCROW", "1 Tier-A plus corroboration"
        elif u["n_flags"] >= 2:
            action, why = "T1_COACH", "multiple soft signals"
        else:
            action, why = "T0_MONITOR", "single soft signal"
        q.append({"user_id": u["user_id"], "cohort": u["_cohort"],
                  "n_tasks": u["n_tasks"], "recommended_action": action,
                  "rationale": why, "n_flags": u["n_flags"],
                  "tier_a_flags": u["tier_a_flags"],
                  "signals": [f["signal"] for f in u["flags"]]})
    order = {"T3_SUSPEND_PENDING_HUMAN_REVIEW": 0, "T2_THROTTLE_AND_ESCROW": 1,
             "T1_COACH": 2, "T0_MONITOR": 3}
    q.sort(key=lambda x: (order[x["recommended_action"]], -x["tier_a_flags"], -x["n_flags"]))
    return q


# ---------------------------------------------------------------------------
# distribution report - look before you threshold
# ---------------------------------------------------------------------------

def histogram(vals, lo, hi, bins=24, width=48):
    vals = [v for v in vals if v is not None]
    if not vals:
        return ["  (no data)"]
    step = (hi - lo) / bins
    counts = [0] * bins
    for v in vals:
        counts[min(bins - 1, max(0, int((v - lo) / step)))] += 1
    mx = max(counts) or 1
    out = []
    for i, c in enumerate(counts):
        bar = "#" * int(width * c / mx)
        out.append(f"  {lo + i*step:7.2f} | {bar:<{width}} {c}")
    return out


def main():
    ap = argparse.ArgumentParser(description="Transcriber quality signals (routing, not blocking)")
    ap.add_argument("--data", required=True)
    ap.add_argument("--cohort-cols", default="language,device_class,task_type",
                    help="comma-separated columns defining a cohort; '' for global (NOT recommended)")
    ap.add_argument("--json", default="")
    args = ap.parse_args()

    rows, absent_opt = load(Path(args.data))
    consensus, overlap = build_consensus(rows)
    users = per_user(rows, consensus)

    cohort_cols = [c.strip() for c in args.cohort_cols.split(",") if c.strip()]
    cohort_cols = [c for c in cohort_cols if c in (rows[0].keys())]
    calib = flag(users, cohort_cols)
    queue = review_queue(users)

    print("=" * 78)
    print("  TRANSCRIBER QUALITY ANALYSIS")
    print("=" * 78)
    print(f"  tasks {len(rows)}   users {len(users)}   "
          f"eligible (>= {MIN_TASKS} tasks) {sum(1 for u in users.values() if u['sufficient_data'])}")
    print(f"  cohort definition: {' x '.join(cohort_cols) if cohort_cols else 'GLOBAL (unfair - see Part I s3)'}")

    if absent_opt:
        print(f"\n  !! MISSING OPTIONAL COLUMNS: {absent_opt}")
        print("     Consequences (Part I s4):")
        if "playback_speed_used" in absent_opt:
            print("       - playback_speed_used absent -> Signal 1 CANNOT be trusted for action")
        if "task_type" in absent_opt:
            print("       - task_type absent -> Signal 6 may fire on scripted-read tasks")
        if "language" in absent_opt or "device_class" in absent_opt:
            print("       - no cohort columns -> thresholds will be unfair across languages/devices")
        if "is_honeypot" in absent_opt:
            print("       - is_honeypot absent -> NO BLOCKING SIGNAL EXISTS in this data")

    print("\n" + "-" * 78)
    print("  PEER OVERLAP (enables Signal 2 - the strongest inference available)")
    print("-" * 78)
    print(f"  clips {overlap['clips_total']}   with >{MIN_PEERS_FOR_CONSENSUS} distinct workers "
          f"{overlap['clips_with_overlap']}  ({overlap['overlap_share']*100:.1f}%)")
    print("  Signal 2 " + ("AVAILABLE" if overlap["available"] else
          "UNAVAILABLE - route ~5% of clips to 3+ transcribers (Part II s7)"))

    print("\n" + "-" * 78)
    print("  DISTRIBUTIONS - look at these before accepting any threshold")
    print("-" * 78)
    for label, vals, lo, hi in [
        ("listen_ratio (per task)", [r["_usable_ratio"] for r in rows], 0, 6),
        ("norm_edit (edited tasks)", [r["_norm_edit"] for r in rows if r["_actually_edited"]], 0, 1),
        ("accept_rate (per user)", [u["accept_rate"] for u in users.values()], 0, 1),
    ]:
        print(f"\n  {label}")
        for line in histogram(vals, lo, hi):
            print(line)

    mism = sum(1 for r in rows if r["_flag_mismatch"])
    if mism:
        print(f"\n  !! {mism} task(s) where is_edited disagrees with whisper_text != user_text.")
        print("     Investigate before trusting is_edited anywhere.")

    devs = [u["cps_column_max_deviation"] for u in users.values()
            if u["cps_column_max_deviation"] is not None]
    if devs and max(devs) > 0.5:
        print(f"\n  !! segment_character_per_second disagrees with recomputation "
              f"(max dev {max(devs):.2f}).")
        print("     The supplied column's definition differs from the brief's. Confirm with eng.")

    print("\n" + "-" * 78)
    print("  COHORT-CALIBRATED THRESHOLDS (observed percentiles, not hardcoded)")
    print("-" * 78)
    for cname, c in sorted(calib.items()):
        print(f"\n  cohort: {cname}   users {c['n_users']} (eligible {c['n_eligible']})")
        if not c["thresholds"]:
            print("    too few eligible users to calibrate - no flags raised")
            continue
        for metric, t in c["thresholds"].items():
            print(f"    {metric:<24} cut {str(t['cut']):>8}  "
                  f"median {str(t['cohort_median']):>8}  tier {t['tier']}  ({t['direction']})")

    print("\n" + "=" * 78)
    print("  REVIEW QUEUE - routing only, NOT block decisions")
    print("=" * 78)
    if not queue:
        print("  No users flagged.")
    for q in queue:
        print(f"\n  {q['user_id']}  [{q['cohort']}]  {q['n_tasks']} tasks")
        print(f"    -> {q['recommended_action']}  ({q['rationale']})")
        print(f"       signals: {', '.join(q['signals'])}")

    print("\n" + "=" * 78)
    print("  NO BLOCK RECOMMENDATIONS ARE EMITTED BY DESIGN.")
    print("  Per Part II: these signals measure EFFORT, not ACCURACY. A block requires")
    print("  (1) failed gold-standard honeypots with a known answer, (2) corroborating")
    print("  cohort-relative signals, and (3) a human reviewer's confirmation.")
    print("  This dataset contains no honeypots, so it cannot justify blocking anyone.")
    print("=" * 78)

    if args.json:
        Path(args.json).write_text(json.dumps({
            "summary": {"n_tasks": len(rows), "n_users": len(users),
                        "cohort_cols": cohort_cols, "missing_optional": absent_opt},
            "overlap": overlap, "calibration": calib,
            "users": {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")}
                      for k, v in users.items()},
            "review_queue": queue,
            "disclaimer": "Routing signals only. Not block decisions. See Part II.",
        }, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        print(f"\nWrote {args.json}")


if __name__ == "__main__":
    main()
