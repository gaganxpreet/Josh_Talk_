#!/usr/bin/env python3
"""
Dukaan Bench - analysis.

Implements exactly the pre-registered plan in rating/RATING_PROTOCOL.md, in that
order, with no extra cuts. If you want a different slice, add it to the protocol
first and label it exploratory - that discipline is the whole point.

Usage
-----
    python analyze.py --ratings ../rating/responses/      # dir of ratings_*.csv
    python analyze.py --ratings all_ratings.csv           # or one combined file
    python analyze.py --ratings ... --gt tf_ground_truth.csv

Outputs
-------
    results.json            machine-readable, consumed by the dashboard
    RESULTS.md              human-readable summary you paste into the main doc
    dashboard_data.js       drop-in data file for ../dashboard/

Standard library only - no install step, nothing to break on a reviewer's machine.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics as st
from collections import defaultdict
from pathlib import Path

random.seed(20260701)  # deterministic bootstrap

HERE = Path(__file__).resolve().parent

MODEL_META = {
    "gpt_image_1":                    ("OpenAI", "GPT Image 1"),
    "gemini_2_5_flash_image":         ("Google", "Gemini 2.5 Flash Image"),
    "gemini_3_1_flash_image_preview": ("Google", "Gemini 3.1 Flash Image Preview"),
}
CONTROL_PROMPT = "P10"          # the English control
B = 10_000                      # bootstrap resamples


# ---------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------

def load_ratings(path: Path) -> list[dict]:
    files = sorted(path.glob("ratings_*.csv")) if path.is_dir() else [path]
    if not files:
        raise SystemExit(f"No ratings CSVs found at {path}")

    rows: list[dict] = []
    for f in files:
        with open(f, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                for k in ("tf", "ca", "cu", "upr", "screen_index",
                          "h2h_winner", "tf_skipped_cannot_read",
                          "is_duplicate_check", "screen_seconds"):
                    v = (r.get(k) or "").strip()
                    r[k] = None if v == "" else int(float(v))
                r["ca_tags"] = [t for t in (r.get("ca_tags") or "").split("|") if t]
                rows.append(r)

    print(f"Loaded {len(rows)} rating rows from {len(files)} file(s), "
          f"{len({r['rater_id'] for r in rows})} rater(s).")
    return rows


def split_duplicate_check(rows):
    """The repeated P01 screen is a reliability probe, not primary data."""
    return ([r for r in rows if not r["is_duplicate_check"]],
            [r for r in rows if r["is_duplicate_check"]])


# ---------------------------------------------------------------------------
# statistics
# ---------------------------------------------------------------------------

def mean(xs):
    xs = [x for x in xs if x is not None]
    return st.mean(xs) if xs else None


def bootstrap_ci_by_rater(rows, field, b=B, alpha=0.05):
    """
    Percentile bootstrap for a mean/proportion, resampling RATERS (not rows).

    Each rater contributes ~30 correlated judgements. Resampling rows would treat
    those as 30 independent observations and produce intervals perhaps 3x too
    narrow - the most common way small human evals overstate their confidence.

    Implemented as a cluster bootstrap on a ratio estimator: aggregate each
    rater to (sum, count) once, then resample those pairs. That keeps the cost
    at O(B x n_raters) instead of rebuilding the full row list B times.
    """
    agg = defaultdict(lambda: [0.0, 0])
    for r in rows:
        v = r.get(field)
        if v is not None:
            agg[r["rater_id"]][0] += v
            agg[r["rater_id"]][1] += 1
    pairs = [(s, n) for s, n in agg.values() if n]
    if len(pairs) < 2:
        return (None, None)

    k = len(pairs)
    stats = []
    for _ in range(b):
        tot = 0.0
        cnt = 0
        for _ in range(k):
            s, n = pairs[random.randrange(k)]
            tot += s
            cnt += n
        if cnt:
            stats.append(tot / cnt)
    if not stats:
        return (None, None)
    stats.sort()
    lo = stats[max(0, int((alpha / 2) * len(stats)) - 1)]
    hi = stats[min(len(stats) - 1, int((1 - alpha / 2) * len(stats)))]
    return (round(lo, 4), round(hi, 4))


def krippendorff_ordinal(rows, axis):
    """
    Krippendorff's alpha, ordinal difference metric.

    Units = images, observers = raters. Returns None when there isn't enough
    overlap to compute it, rather than returning a confident-looking number
    built on two data points.
    """
    units = defaultdict(list)
    for r in rows:
        v = r.get(axis)
        if v is not None:
            units[r["image_id"]].append(v)
    units = {u: vs for u, vs in units.items() if len(vs) >= 2}
    if len(units) < 2:
        return None

    values = sorted({v for vs in units.values() for v in vs})
    if len(values) < 2:
        return 1.0  # everyone agreed on one value everywhere

    idx = {v: i for i, v in enumerate(values)}
    k = len(values)
    o = [[0.0] * k for _ in range(k)]
    for vs in units.values():
        m = len(vs)
        for i in range(m):
            for j in range(m):
                if i != j:
                    o[idx[vs[i]]][idx[vs[j]]] += 1.0 / (m - 1)

    n_c = [sum(row) for row in o]
    n = sum(n_c)
    if n <= 1:
        return None

    def delta(a, b):
        lo, hi = (a, b) if a <= b else (b, a)
        s = sum(n_c[g] for g in range(lo, hi + 1)) - (n_c[a] + n_c[b]) / 2.0
        return s * s

    do = sum(o[a][b] * delta(a, b) for a in range(k) for b in range(k)) / n
    de = sum(n_c[a] * n_c[b] * delta(a, b)
             for a in range(k) for b in range(k) if a != b) / (n * (n - 1))
    if de == 0:
        return None
    return round(1 - do / de, 3)


def interpret_alpha(a):
    if a is None:
        return "not computable"
    if a >= 0.80:
        return "strong - treat as reliable"
    if a >= 0.667:
        return "acceptable - standard threshold for tentative conclusions"
    if a >= 0.50:
        return "weak - INDICATIVE ONLY, do not headline"
    return "poor - do not draw conclusions from this axis"


# ---------------------------------------------------------------------------
# metrics
# ---------------------------------------------------------------------------

def upr(rows):
    v = [r["upr"] for r in rows if r["upr"] is not None]
    return sum(v) / len(v) if v else None


def per_model(rows):
    out = {}
    for mk, (company, name) in MODEL_META.items():
        mr = [r for r in rows if r["model_key"] == mk]
        if not mr:
            continue
        indic = [r for r in mr if r["prompt_id"] != CONTROL_PROMPT]
        ctrl = [r for r in mr if r["prompt_id"] == CONTROL_PROMPT]

        tf_indic, tf_ctrl = mean([r["tf"] for r in indic]), mean([r["tf"] for r in ctrl])
        tagged = sum(1 for r in mr if "rajasthan-default" in r["ca_tags"])
        skipped = sum(1 for r in mr if r["tf_skipped_cannot_read"])

        out[mk] = {
            "model_key": mk, "company": company, "model_name": name,
            "n_ratings": len(mr),
            "upr": round(upr(mr), 4) if upr(mr) is not None else None,
            "upr_ci95": bootstrap_ci_by_rater(mr, "upr"),
            "tf_mean": round(tf_indic, 3) if tf_indic is not None else None,
            "tf_english_control": round(tf_ctrl, 3) if tf_ctrl is not None else None,
            "indic_text_penalty": (round(tf_ctrl - tf_indic, 3)
                                   if None not in (tf_ctrl, tf_indic) else None),
            "ca_mean": round(mean([r["ca"] for r in mr]), 3) if mean([r["ca"] for r in mr]) is not None else None,
            "cu_mean": round(mean([r["cu"] for r in mr]), 3) if mean([r["cu"] for r in mr]) is not None else None,
            "rajasthan_default_rate": round(tagged / len(mr), 4),
            "tf_skipped_rate": round(skipped / len(mr), 4),
        }
    return out


def per_script(rows):
    out = defaultdict(dict)
    scripts = sorted({r["script"] for r in rows})
    for sc in scripts:
        for mk in MODEL_META:
            cell = [r for r in rows if r["script"] == sc and r["model_key"] == mk]
            if not cell:
                continue
            tf = mean([r["tf"] for r in cell])
            out[sc][mk] = {
                "tf_mean": round(tf, 3) if tf is not None else None,
                "upr": round(upr(cell), 4) if upr(cell) is not None else None,
                "n": len(cell),
                "n_tf_scored": sum(1 for r in cell if r["tf"] is not None),
            }
    return dict(out)


def head_to_head(rows):
    """One choice per (rater, screen). Collapse the 3 rows back to 1 decision."""
    seen, choices = set(), []
    for r in rows:
        key = (r["rater_id"], r["screen_index"])
        if key in seen:
            continue
        seen.add(key)
        choices.append(r["h2h_choice"])

    total = len(choices)
    if not total:
        return {}
    none_n = sum(1 for c in choices if c == "none")

    # map winning position back to the model that was in it for that rater/screen
    wins = defaultdict(int)
    for r in rows:
        if r["h2h_winner"]:
            wins[r["model_key"]] += 1

    return {
        "n_decisions": total,
        "none_rate": round(none_n / total, 4),
        "none_count": none_n,
        "win_rate": {mk: round(wins.get(mk, 0) / total, 4) for mk in MODEL_META},
        "win_count": {mk: wins.get(mk, 0) for mk in MODEL_META},
        "win_rate_excluding_none": (
            {mk: round(wins.get(mk, 0) / (total - none_n), 4) for mk in MODEL_META}
            if total > none_n else None),
    }


def duplicate_consistency(dups, primary):
    """Within-rater agreement between the repeated P01 screen and the original."""
    first = {(r["rater_id"], r["image_id"]): r for r in primary if r["prompt_id"] == "P01"}
    pairs = defaultdict(list)
    for d in dups:
        f = first.get((d["rater_id"], d["image_id"]))
        if not f:
            continue
        for ax in ("tf", "ca", "cu", "upr"):
            if f[ax] is not None and d[ax] is not None:
                pairs[ax].append((f[ax], d[ax]))

    out = {}
    for ax, ps in pairs.items():
        exact = sum(1 for a, b in ps if a == b) / len(ps)
        out[ax] = {
            "n_pairs": len(ps),
            "exact_agreement": round(exact, 3),
            "mean_abs_diff": round(mean([abs(a - b) for a, b in ps]), 3),
        }
    return out


def ground_truth_check(rows, gt_path: Path | None):
    """Compare researcher TF_GT against script-native rater TF."""
    if not gt_path or not gt_path.exists():
        return {"status": "no ground-truth file supplied",
                "note": "Run the researcher TF_GT pass and re-run with --gt. "
                        "Without it we cannot validate the instrument."}
    gt = {}
    with open(gt_path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            v = (r.get("tf_gt") or "").strip()
            if v != "":
                gt[r["image_id"]] = int(float(v))

    by_img = defaultdict(list)
    for r in rows:
        if r["tf"] is not None:
            by_img[r["image_id"]].append(r["tf"])

    diffs, exact = [], 0
    for iid, g in gt.items():
        if iid in by_img:
            h = mean(by_img[iid])
            diffs.append(h - g)
            if abs(h - g) < 0.5:
                exact += 1
    if not diffs:
        return {"status": "no overlap between ground truth and rater TF"}
    return {
        "status": "ok",
        "n_images_compared": len(diffs),
        "within_half_point": round(exact / len(diffs), 3),
        "mean_signed_diff_rater_minus_gt": round(mean(diffs), 3),
        "interpretation": ("Positive means raters were more generous than ground truth; "
                           "negative means stricter. A large systematic gap means the "
                           "rubric anchors are mis-specified, not that the raters are wrong."),
    }


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------

def fmt(v, pct=False, nd=2):
    if v is None:
        return "–"
    return f"{v*100:.0f}%" if pct else f"{v:.{nd}f}"


def ci(c):
    return "–" if not c or c[0] is None else f"[{c[0]*100:.0f}–{c[1]*100:.0f}%]"


def write_markdown(res, out: Path):
    L = []
    A = L.append
    n_raters = res["meta"]["n_raters"]
    n_img = res["meta"]["n_images_rated"]

    A("# Dukaan Bench — Results\n")
    A(f"*{n_raters} raters · {n_img} images · {res['meta']['n_ratings']} ratings · "
      f"generated by `analyze.py`*\n")

    A("> **Read the confidence intervals, not the point estimates.** With "
      f"{n_raters} raters the intervals are wide by construction. Where two models' "
      "intervals overlap, this eval does **not** separate them, and no amount of "
      "decimal places changes that.\n")

    A("\n## 1. Headline — Usable Poster Rate\n")
    A("Share of images a rater would post to WhatsApp Status **with no editing**.\n")
    A("| Model | Company | UPR | 95% CI | n |")
    A("|---|---|---|---|---|")
    for m in sorted(res["per_model"].values(), key=lambda x: -(x["upr"] or 0)):
        A(f"| {m['model_name']} | {m['company']} | **{fmt(m['upr'], pct=True)}** "
          f"| {ci(m['upr_ci95'])} | {m['n_ratings']} |")

    h = res["head_to_head"]
    if h:
        A("\n## 2. Head-to-head\n")
        A(f"**“None of these” was chosen in {fmt(h['none_rate'], pct=True)} of "
          f"{h['n_decisions']} decisions.**\n")
        A("| Model | Win rate | Wins |")
        A("|---|---|---|")
        for mk, wr in sorted(h["win_rate"].items(), key=lambda kv: -kv[1]):
            A(f"| {MODEL_META[mk][1]} | {fmt(wr, pct=True)} | {h['win_count'][mk]} |")
        A(f"| *None of these* | *{fmt(h['none_rate'], pct=True)}* | *{h['none_count']}* |")

    A("\n## 3. Indic Text Penalty\n")
    A("Text Fidelity on the English control (P10) minus mean TF across the nine Indic "
      "prompts. This is the number that separates *“bad at text”* from *“bad at **Indic** "
      "text”* — and those point at different fixes.\n")
    A("| Model | TF (Indic) | TF (English control) | **ITP** |")
    A("|---|---|---|---|")
    for m in res["per_model"].values():
        A(f"| {m['model_name']} | {fmt(m['tf_mean'])} | {fmt(m['tf_english_control'])} "
          f"| **{fmt(m['indic_text_penalty'])}** |")
    A("\n*Scale 0–3. A large positive ITP means the model can render text — just not this text.*\n")

    A("\n## 4. Text Fidelity by script\n")
    A("Tests whether “Indic support” is really just “Hindi-ish support”.\n")
    keys = list(MODEL_META)
    A("| Script | " + " | ".join(MODEL_META[k][1] for k in keys) + " |")
    A("|---" * (len(keys) + 1) + "|")
    for sc, cells in res["per_script"].items():
        row = [fmt(cells.get(k, {}).get("tf_mean")) for k in keys]
        A(f"| {sc} | " + " | ".join(row) + " |")

    A("\n## 5. Cultural authenticity\n")
    A("| Model | CA mean | CU mean | “Rajasthan default” tagged |")
    A("|---|---|---|---|")
    for m in res["per_model"].values():
        A(f"| {m['model_name']} | {fmt(m['ca_mean'])} | {fmt(m['cu_mean'])} "
          f"| {fmt(m['rajasthan_default_rate'], pct=True)} |")

    A("\n## 6. Did we measure anything real? (reliability)\n")
    A("| Axis | Krippendorff's α | Verdict |")
    A("|---|---|---|")
    for ax, a in res["reliability"]["krippendorff_alpha"].items():
        A(f"| {ax.upper()} | {a if a is not None else '–'} | {interpret_alpha(a)} |")

    dc = res["reliability"]["duplicate_screen"]
    if dc:
        A("\n**Within-rater consistency** — the repeated P01 screen, positions re-randomised:\n")
        A("| Axis | Exact agreement | Mean abs. difference | n |")
        A("|---|---|---|---|")
        for ax, d in dc.items():
            A(f"| {ax.upper()} | {fmt(d['exact_agreement'], pct=True)} "
              f"| {d['mean_abs_diff']} | {d['n_pairs']} |")

    gtc = res["reliability"]["ground_truth"]
    A(f"\n**Ground-truth check:** {gtc.get('status')}")
    if gtc.get("status") == "ok":
        A(f" — raters landed within half a point of researcher ground truth on "
          f"{fmt(gtc['within_half_point'], pct=True)} of images "
          f"(mean signed difference {gtc['mean_signed_diff_rater_minus_gt']:+.2f}).")

    A("\n## 7. What this sample can and cannot support\n")
    A(f"**Can support.** Large, consistent gaps — a model with UPR near zero across "
      f"{n_raters} raters and 10 prompts is not an artefact. Directional findings about "
      "script coverage. The existence and rough size of the Indic Text Penalty.\n")
    A("\n**Cannot support.** Fine-grained ranking between models whose intervals overlap. "
      "Any per-script claim resting on one prompt and a handful of qualified readers — "
      "see `n_tf_scored` in `results.json` before quoting a script-level number. "
      "Generalisation to real shop owners; this panel is a qualified-reader panel, not a "
      "representative sample of Indian MSMEs.\n")

    out.write_text("\n".join(L), encoding="utf-8")
    print(f"  wrote {out.name}")


def main():
    ap = argparse.ArgumentParser(description="Dukaan Bench analysis")
    ap.add_argument("--ratings", required=True, help="CSV file or directory of ratings_*.csv")
    ap.add_argument("--gt", default="", help="optional researcher TF ground-truth CSV")
    ap.add_argument("--out", default=str(HERE))
    args = ap.parse_args()

    rows = load_ratings(Path(args.ratings))
    primary, dups = split_duplicate_check(rows)

    res = {
        "meta": {
            "eval": "Dukaan Bench v1.0",
            "n_raters": len({r["rater_id"] for r in primary}),
            "n_images_rated": len({r["image_id"] for r in primary}),
            "n_ratings": len(primary),
            "bootstrap_resamples": B,
            "bootstrap_unit": "rater (clustered)",
        },
        "per_model": per_model(primary),
        "per_script": per_script(primary),
        "head_to_head": head_to_head(primary),
        "reliability": {
            "krippendorff_alpha": {ax: krippendorff_ordinal(primary, ax)
                                   for ax in ("tf", "ca", "cu", "upr")},
            "duplicate_screen": duplicate_consistency(dups, primary),
            "ground_truth": ground_truth_check(primary, Path(args.gt) if args.gt else None),
        },
    }

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "results.json").write_text(
        json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print("  wrote results.json")
    write_markdown(res, outdir / "RESULTS.md")
    (outdir.parent / "dashboard" / "dashboard_data.js").write_text(
        "window.DUKAAN_RESULTS = " + json.dumps(res, ensure_ascii=False) + ";",
        encoding="utf-8")
    print("  wrote ../dashboard/dashboard_data.js")

    print("\n--- headline ---")
    for m in sorted(res["per_model"].values(), key=lambda x: -(x["upr"] or 0)):
        print(f"  {m['model_name']:<34} UPR {fmt(m['upr'], pct=True):>5}  "
              f"CI {ci(m['upr_ci95'])}  ITP {fmt(m['indic_text_penalty'])}")
    if res["head_to_head"]:
        print(f"  {'None of these':<34}     {fmt(res['head_to_head']['none_rate'], pct=True):>5}")


if __name__ == "__main__":
    main()
