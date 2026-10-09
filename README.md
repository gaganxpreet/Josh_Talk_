# Josh Talks AI — Product Task submission

**Date:** October 2026

---

## What's here

| | Deliverable | Start here |
|---|---|---|
| **Q1** | Text-to-image eval for India — *Dukaan Bench* | [`Q1_dukaan_bench/02_ONE_PAGE_REPORT.md`](Q1_dukaan_bench/02_ONE_PAGE_REPORT.md) |
| **Q2** | Detecting low-quality transcribers from data signals | [`Q2_transcriber_quality/01_PART_I_warning_signs.md`](Q2_transcriber_quality/01_PART_I_warning_signs.md) |

**If you have five minutes:** read the Q1 one-pager, then open
[`Q1_dukaan_bench/dashboard/dukaan_bench_dashboard.html`](Q1_dukaan_bench/dashboard/dukaan_bench_dashboard.html)
and click the script filter. Then read §8 of the Q2 Part II document — the actual block rule.

---

## ⚠️ Honest status

**The Q1 results tables are empty, on purpose.**

The eval design, prompt set, generation harness, rating tool, analysis pipeline and dashboard
are complete and runnable. What remains is executing the generation run and the 8–10 person
participant panel — the parts that need API access and real humans.

I have deliberately **not** filled in illustrative numbers. A fabricated figure in a submission
about evaluation integrity would defeat the submission. Everywhere a result belongs, you'll find
`[AWAITING RATINGS]` and the command that populates it.

Synthetic-data generators are included for pipeline testing only. Their input fixtures and
generated analysis outputs are excluded from Git by default so test numbers cannot be mistaken
for submission results. Generated real-data results should be reviewed before explicitly adding
them to the repository.

---

## Q1 — Dukaan Bench

> Can a frontier image model make a **usable** festival or offer poster, with correct Indic
> text, for an Indian small business, in one shot?

**Headline metric — Usable Poster Rate:** share of images a rater would post to WhatsApp Status
with no editing. Binary, because the real decision is binary.

**Models:** OpenAI GPT Image 1 · Google Gemini 2.5 Flash Image · Google Gemini 3.1 Flash Image Preview
**Prompts:** 10 — six Indic scripts **+ one matched English control**
**Panel:** 8–10 consenting adults, script-qualified, blinded A/B/C triads

```
Q1_dukaan_bench/
├─ 01_MAIN_DOCUMENT.md          full write-up + final reflection
├─ 02_ONE_PAGE_REPORT.md        the summary a busy reviewer reads
├─ 03_VIDEO_SCRIPT.md           timed 2-minute script
├─ prompts/prompt_set_v1.json   10 prompts, exact strings, per-prompt rationale
├─ generation/                  API harness + manual web-UI workflow
├─ rating/                      protocol, consent form, offline rating tool
├─ analysis/                    UPR, bootstrap CIs, ITP, Krippendorff's α
├─ dashboard/                   leaderboard prototype
├─ images/                      generated images (empty until you run it)
└─ evidence/                    generation manifest, raw API metadata, screenshots
```

### Running it

```bash
cd Q1_dukaan_bench

# 1. Generate — API, manual, or any mix of the two
pip install -r generation/requirements.txt
cp generation/.env.example generation/.env     # add whichever keys you have
python generation/generate.py --all
#   no keys? follow generation/MANUAL_WORKFLOW.md, then:
python generation/generate.py --register-manual
python generation/generate.py --status         # 3x10 coverage grid

# 2. Rate — open in a browser, one rater at a time
#    rating/rater_tool.html   (works offline; nothing is uploaded)

# 3. Analyse
python analysis/analyze.py --ratings rating/responses/

# 4. Dashboard — analyze.py writes dashboard_data.js; just reload the page
#    dashboard/dukaan_bench_dashboard.html
```

### The three ideas worth your attention

1. **The English control prompt.** P10 is P01 in Latin script. The gap — the **Indic Text
   Penalty** — separates *"can't render text"* from *"can't render **this** text."* Same bad
   score, two different roadmaps. Without it you have a complaint, not a diagnosis.
2. **"None of these" at full weight.** Most arenas force a choice and manufacture a winner even
   when every option is unusable. Where failure is the expected outcome, that's the fastest
   route to a misleading leaderboard.
3. **One global leaderboard is the wrong product for India.** The dashboard's script filter
   re-ranks everything; a model that leads on Devanagari can sit at the floor on Tamil. The
   per-script view is the product; the global average is the marketing.

---

## Q2 — Transcriber quality

```
Q2_transcriber_quality/
├─ 01_PART_I_warning_signs.md       6 signals, ranked by evidential strength
├─ 02_PART_II_detection_system.md   the system, the ladder, the block rule
└─ analysis/
   ├─ transcriber_quality.py        runnable the moment the CSV lands
   └─ make_synthetic_tasks.py       test fixture with a planted answer key
```

```bash
cd Q2_transcriber_quality/analysis
python make_synthetic_tasks.py                            # fixture with known bad actors
python transcriber_quality.py --data synthetic_tasks.csv  # fixture; see limitation below
# The fixture has too few users per language/device cohort for reliable percentile
# calibration, so safe abstention is expected; it does not validate review-queue recall.
# when the real data arrives:
python transcriber_quality.py --data ../../tasks.csv --cohort-cols language,device_class
```

### The argument in three lines

1. **Every column in this dataset measures effort, not accuracy.** A diligent-but-unskilled
   transcriber scores perfectly on all six signals and still produces bad text. So these signals
   can show that work *wasn't plausibly done* — never that it was *wrong*.
2. **Therefore: statistical signals route attention; ground truth justifies action.** Plant
   gold-standard honeypots with known answers and deliberately wrong Whisper text. Block on
   those. Use the behavioural signals to decide who gets more honeypots and whose work gets
   reviewed.
3. **Every threshold must be a percentile within a cohort** (language × device × task type),
   never a global constant. A global cutoff on listen-time flags a *population*, not a
   *behaviour* — and it flags the slow-device, low-resource-language workers Josh Jobs exists to
   include.

The script enforces point 1 in code: it emits a review queue and **refuses to output block
recommendations**, printing why.

### The block rule (full version in Part II §8)

Block only when **all four** hold: honeypot catch rate < 0.40 over ≥ 10 obvious honeypots;
**and** ≥ 2 corroborating signals in the bottom 5% of their cohort; **and** a human reviewer has
listened to ≥ 20 clips and confirmed; **and** the user already failed coaching and throttling.

Explicitly **not** grounds for a block on their own: a high accept rate, a low listen ratio, a
high cosmetic-edit share, a low composite score, or anything computed from fewer than 30 tasks.

---

## What I'd want a reviewer to push on

Listed so you don't have to find them yourself:

- **Q1 is designed but not yet run.** The thinking is complete; the evidence isn't. That's the
  honest state and it's visible on every results table.
- **I wrote all ten prompts myself.** Single-author bias is the biggest weakness in the Q1
  design, and native-speaker prompt authors per script is the first thing I'd fix.
- **Q2 thresholds are structural, not calibrated.** They sit where behaviour becomes implausible
  in principle. Real numbers need the real distribution, which is why the script calibrates
  percentiles from the data rather than hardcoding my guesses.
- **Q2's peer-consensus signal can punish genuine experts.** A dialect specialist who is right
  while the crowd is wrong looks deviant. That's the weakest part of the design and I say so in
  Part II §9.

---

## The thread connecting both answers

Both questions are the same problem seen from two sides: **define what "good" means, then
measure it without fooling yourself.**

Q1 does it with humans judging machines — so the work goes into blinding, rater qualification,
pre-registration, and publishing the inter-rater agreement rather than hiding it.

Q2 does it with data judging humans — so the work goes into knowing what the data *can't* tell
you, and refusing to let a proxy metric take someone's income away.

In both, the same discipline: **be explicit about what your evidence can't support**, and build
the system so that limit is enforced in code rather than remembered in a footnote.
