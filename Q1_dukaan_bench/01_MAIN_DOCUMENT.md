# Dukaan Bench — Main Document

**A text-to-image evaluation for Indian small-business marketing creatives**

Josh Talks AI Product Task · Question 1 · October 2026

> **Status of numbers in this document.** The eval design, prompt set, instrument, tooling and
> dashboard are complete and runnable. Every results table is marked
> `[AWAITING RATINGS]` until the generation run and the 8–10 participant panel are executed.
> I have deliberately not written in illustrative figures: a fabricated number in a document
> about evaluation integrity would defeat the point of the document. `analysis/analyze.py`
> fills every one of these tables automatically from the collected ratings.

---

## 1. The eval in one paragraph

A kirana-store owner in Kanpur wants a Diwali offer poster for her WhatsApp Status. She types
one prompt. She is not a designer, she will not open Canva to fix the output, and the poster
needs a Hindi headline. **Dukaan Bench** asks whether three frontier image models can serve
that moment — and measures it with one headline number, the **Usable Poster Rate (UPR)**: the
share of generated images a rater would post *as-is, with no editing*. Ten prompts span six
Indic scripts plus a matched English control, so we can separate *"this model can't render
text"* from *"this model can't render **Indic** text."*

---

## 2. Category and use case

| | |
|---|---|
| **Category** | Local commerce / MSME marketing creatives |
| **Use case** | A single festival-or-offer poster, containing Indic-script text, generated in one shot by a non-designer shop owner, for WhatsApp Status and low-cost print |
| **Models** | OpenAI GPT Image 1 · Google Gemini 2.5 Flash Image · Google Gemini 3.1 Flash Image Preview |
| **Headline metric** | Usable Poster Rate (UPR) |
| **Panel** | 8–10 consenting adults, script-qualified for the text questions |

### Why I narrowed this far

The brief warns against a broad benchmark, and I think the reason is worth stating. A broad
"Indian image generation" benchmark produces a number nobody can act on, because "India" is
not a capability. Narrowing to one artefact — *a poster with text on it, made by someone who
can't fix it* — buys three things a broad benchmark can't:

1. **A real decision criterion.** Not "rate this 1–10," but "would you post it." That has a
   defensible right answer for a given rater.
2. **Ground truth.** Because the prompt specifies an exact string, text correctness is
   *checkable*, not a matter of taste. That anchors the subjective axes to something hard.
3. **An actionable failure signal.** If the finding is "Tamil conjuncts break," a model team
   knows what to do on Monday. If the finding is "scores 6.4 on India-ness," they do not.

---

## 3. Why this is useful for India

**The volume is real, not hypothetical.** India has roughly 63–65 million MSMEs, and WhatsApp
is the dominant SMB marketing channel in the country — India is WhatsApp's largest market by
users. The single highest-frequency creative artefact an Indian small business produces is an
offer or festival poster pushed to Status and customer groups. This is not a long-tail use
case dressed up as one; it is close to the modal commercial creative act in the country.
*(Figures here are approximate and should be cited from MSME Ministry / Meta disclosures in a
published version.)*

**The one-shot constraint is what makes it a real test.** A design agency gets a model's output
and fixes the text in Illustrator. The shop owner in this use case does not. She has a phone,
a few minutes between customers, and no design software. So an image with one wrong Devanagari
character is not 90% useful — it is **zero per cent useful**, and worse than nothing, because
posting a misspelt sign makes her shop look careless to her own customers. Partial credit is a
convenient fiction for benchmark authors; it does not exist in this user's life. UPR is binary
because the decision is binary.

**It isolates a gap that is specific to India and genuinely unsolved.** Latin text-in-image
improved dramatically between 2023 and 2025. Indic scripts did not keep pace, for reasons that
are structural rather than accidental:

- **Conjuncts.** Devanagari stacks consonants into ligatures (`ष्ठ`, `न्न`). These are single
  visual units built from multiple code points — a model that has learned letters as
  independent stamps produces visible rubble.
- **Vertical complexity.** Matras sit above *and* below the baseline, and Devanagari carries a
  connecting `शिरोरेखा` headline across the word. Getting glyphs right but the headline wrong
  still reads as broken.
- **Cursive positional shaping.** Urdu Nastaliq changes letter shape by position and runs
  right-to-left.
- **Native numerals.** Bengali `৫০` is not `50`. Models substitute Latin digits almost reflexively.
- **Data scarcity.** There is far less high-quality image–text paired data showing correct Indic
  typography than there is for Latin.

**And it surfaces a representation failure that only an India-focused eval would catch.** The
prompt set deliberately spans Hindu, Muslim, Sikh and regional-solar festivals across six
scripts, because most "Indian" eval sets are implicitly Hindu-default and North-Indian-default.
I expect to find what I have named the **"Rajasthan default"**: models collapsing all of India
into camels, forts, turbans and marigolds regardless of whether the prompt said Chennai,
Kolkata or Amritsar. A model that has learned "India" as a single visual token rather than as
28 states will fail a Tamil textile shop while scoring well on an aggregate "India" metric.
The rubric caps cultural authenticity at 1 when this is tagged — because for the shop owner in
Chennai, a Rajasthani poster is simply **the wrong poster**, however pretty.

---

## 4. Why an AI lab building for India would care

**It converts a vibe into a regression test.** "Does our model work for India?" is unanswerable
and therefore unfundable. "Our Usable Poster Rate on Devanagari is X%, Tamil is Y%, and our
Indic Text Penalty is Z points" is a dashboard you can watch across training runs. That is the
difference between a market-research question and an engineering metric.

**The per-script breakdown is a data-budget allocation tool.** The heatmap in the dashboard
tells a lab *which* script to spend the next tranche of annotation budget on. An aggregate
India score cannot do this; it averages away the only actionable information in the result.

**The English control tells them which team owns the fix.** This is the most useful single
design choice in the eval. If the Indic Text Penalty is large, the problem is Indic-specific —
tokenisation, script coverage in training data, font diversity in the image corpus. If the
penalty is near zero and absolute scores are low, the problem is the general text renderer.
Same headline number, two completely different roadmaps. Without a matched control you cannot
tell them apart, which is why P10 exists.

**It is cheap, continuous and repeatable.** Thirty images cost under $10 to generate. The rating
task is under two minutes per screen. This can be re-run on every model release and tracked
longitudinally — which is what makes it a *leaderboard* rather than a one-off report.

**It is commercially load-bearing.** Distribution in India for OpenAI, Google and Meta runs
substantially through exactly this user: a small business owner on a phone. Whoever fixes
Indic creative generation first gets a defensible wedge into the largest untapped SMB market in
the world. A lab that cannot render `दिवाली धमाका` correctly cannot credibly sell creative
tooling to Indian SMBs, no matter how good its English output is.

---

## 5. How the evaluation works

### 5.1 Fairness controls

Every model receives a **byte-identical prompt string**. No per-model prompt tuning, no negative
prompts, no reference images, no retries, **first output not best output**. The last rule
matters most: re-rolling until a model produces something nice biases the whole eval toward
whichever model you were most patient with. The shop owner gets the first output, so the eval
scores the first output.

All ten prompts share an identical five-part structure — `[business + scene]` + `[occasion]` +
`[EXACT TEXT, quoted]` + `[style]` + `[vertical portrait]` — so differences in score reflect
model capability rather than differences in prompt complexity.

### 5.2 The prompt set

Ten prompts. Full text, exact target strings, and a written rationale for each are in
[`prompts/prompt_set_v1.json`](prompts/prompt_set_v1.json).

| ID | Script | Business · Occasion | Target text | What it probes |
|---|---|---|---|---|
| P01 | Devanagari | Kirana · Diwali | `दिवाली धमाका` / `50% छूट` | Baseline; easiest possible Hindi |
| P02 | Devanagari | Sweet shop · Diwali | `मिष्ठान्न भंडार` / `ताज़ा मिठाई` | **Conjuncts + nukta** — the real stress test |
| P03 | Devanagari + Latin | Salon · Wedding | `Bridal Makeup` / `शादी स्पेशल` / `₹2999 से` | Code-mixing + `₹` glyph |
| P04 | Devanagari | Mobile repair · Offer | `मोबाइल रिपेयरिंग` / `30 मिनट में` | English loanwords in Devanagari |
| P05 | Tamil | Textiles · Pongal | `பொங்கல் சிறப்பு சலுகை` | Does "Indic" generalise past Hindi? |
| P06 | Bengali | Clothing · Durga Puja | `পূজা স্পেশাল` / `৫০% ছাড়` | **Native numerals** `৫০` not `50` |
| P07 | Gurmukhi | Dhaba · Baisakhi | `ਵਿਸਾਖੀ ਦੀਆਂ ਵਧਾਈਆਂ` | Lower-resource script; finds the floor |
| P08 | Telugu | Electronics · Ugadi | `ఉగాది ఆఫర్` | Second South Indian script |
| P09 | Urdu (Nastaliq) | Bakery · Eid | `عید مبارک` | **RTL + cursive shaping**; hardest case |
| P10 | **Latin** | Kirana · Diwali | `DIWALI DHAMAKA` / `50% OFF` | **CONTROL** — matched to P01 |

Devanagari is over-weighted (4 of 10) because it is the highest-volume case. The five
non-Devanagari scripts exist to test whether "Indic support" is really just "Hindi-ish support."

### 5.3 Generation

Modular by design — [`generation/generate.py`](generation/generate.py) runs the full set via
API, a partial set if you only hold some keys, or registers images you produced by hand in
ChatGPT / Google AI Studio. All three paths write the **same** manifest, so the rest of the
pipeline is indifferent to how an image was made.

Per image we record: company, model name, API model ID, exact prompt, generation surface, all
settings, SHA-256 hash, byte size, timestamp, and a `deviation_notes` field for any
per-model workflow difference. `--status` prints the 3×10 coverage grid.

**Deviations are recorded, not hidden.** If OpenAI returns a `revised_prompt` that differs from
what we sent, the script flags it automatically — a model silently rewriting the prompt is a
genuine fairness caveat and belongs in the limitations section, not buried. Likewise for
aspect-ratio controls that differ across APIs, and for outright refusals: a refusal is a
*result*, logged as one, never worked around by rewording.

### 5.4 Predicted failure taxonomy

Written in advance so failures get counted consistently rather than described ad hoc. Each
image is tagged with whichever apply:

| Tag | Failure |
|---|---|
| `pseudo-script` | Shapes resembling the script that are not real characters |
| `broken-conjunct` | `ष्ठ`/`न्न` rendered as separated or malformed components |
| `floating-matra` | Vowel signs detached or attached to the wrong consonant |
| `broken-shirorekha` | Devanagari headline absent or discontinuous |
| `script-substitution` | Wrong script entirely (e.g. Devanagari where Tamil was asked) |
| `latin-digit-substitution` | `50` where `৫০` was specified |
| `rtl-reversed` | Urdu letter order mirrored or joined wrongly |
| `truncated` | Text correct but cut off by the frame |
| `duplicated-text` | The string rendered two or more times |
| `transliterated-not-rendered` | Romanised text supplied instead of the requested script |

---

## 6. How participants judged

Full specification in [`rating/RATING_PROTOCOL.md`](rating/RATING_PROTOCOL.md). The working
tool is [`rating/rater_tool.html`](rating/rater_tool.html) — offline, single file, nothing uploaded.

### 6.1 Blinding

Each rater sees 10 screens, one per prompt, with the three model outputs side by side as
**A / B / C**. Model identity is never shown. Position and prompt order are randomised per
rater from a hash of their participant ID — so position bias cancels across the panel, and any
session is exactly reproducible from the ID alone if a result is ever questioned.

### 6.2 The four axes

- **TF — Text Fidelity (0–3)**, scored against the displayed ground-truth string. 3 = every
  character correct; 0 = pseudo-script or none.
- **CA — Cultural Authenticity (0–3)**, with the Rajasthan-default cap described in §3.
- **CU — Commercial Usability (0–3)** — composition only, ignoring text, since TF covers that.
- **UPR — "Would you post this, as-is, right now?"** Yes/No. The headline.
- **Head-to-head** — which of the three you'd actually use, **or "none of these."**

Every level of every scale has a written, observable anchor. Ordinal scales without anchors are
the main source of noise in human evals.

### 6.3 Two choices I'd defend hardest

**"None of these" carries equal weight.** Most arena-style evals force a choice, which
manufactures a winner even when every option is unusable. In a category where failure is the
*expected* outcome, suppressing that option is the single biggest available route to a
misleading leaderboard. If the NoneRate is high, that is the finding.

**Raters may only score text in scripts they read natively.** Every screen has a first-class
**"I can't read this script"** button, and using it is the *correct* action. A Hindi reader
guessing at Tamil spelling produces numbers that look like data and aren't. The honest cost is
thin coverage on minority scripts at n=10; the dashboard marks any cell resting on fewer than
four qualified readers with an asterisk and labels it anecdote rather than measurement.

### 6.4 Quality control on our own raters

Mirroring Question 2 — if we're measuring quality, we should measure the measurers:

1. **Duplicate screen.** P01 is shown again at the end with positions re-randomised; within-rater
   agreement across the pair is reported.
2. **Researcher ground truth.** I score TF for all 30 images against the target strings
   independently (`TF_GT`), and we report agreement with the script-native raters. A large
   systematic gap means the *rubric* is mis-specified, not that the raters are wrong.
3. **Time floor.** Screens completed under 15 seconds are flagged for review.

### 6.5 Pre-registered analysis

Fixed before any ratings were collected, so there is no fishing for the cleanest cut: UPR with
95% bootstrap CIs → head-to-head and NoneRate → TF and ITP → per-script TF → CA/CU and
Rajasthan-default rate → reliability checks. **Analysed once, after all ratings are in.** No
interim peeking, no adding raters because the result looked unclear.

**Bootstrap resamples raters, not rows.** Each rater contributes ~30 correlated judgements;
resampling rows would treat those as 30 independent observations and yield intervals roughly
three times too narrow. That is the most common way small human evals overstate their
confidence, and avoiding it is why the intervals here look honestly wide.

**What would falsify the framing.** I expect a large Indic Text Penalty. If ITP ≈ 0 across all
three models, my framing is wrong and the real story is general text rendering, not Indic
specifically. That outcome gets reported as readily as the expected one.

---

## 7. Results

Run `python analysis/analyze.py --ratings rating/responses/` and these tables populate from
`analysis/RESULTS.md`.

### 7.1 Headline — Usable Poster Rate

| Model | Company | UPR | 95% CI | n |
|---|---|---|---|---|
| GPT Image 1 | OpenAI | `[AWAITING RATINGS]` | | |
| Gemini 2.5 Flash Image | Google | `[AWAITING RATINGS]` | | |
| Gemini 3.1 Flash Image Preview | Google | `[AWAITING RATINGS]` | | |

### 7.2 Head-to-head

| Choice | Share | Decisions |
|---|---|---|
| *(per model)* | `[AWAITING RATINGS]` | |
| **None of these** | `[AWAITING RATINGS]` | |

### 7.3 Indic Text Penalty

| Model | TF (Indic avg) | TF (English control) | **ITP** |
|---|---|---|---|
| | `[AWAITING RATINGS]` | | |

### 7.4 Text fidelity by script

| Script | GPT Image 1 | Gemini 2.5 | Gemini 3.1 |
|---|---|---|---|
| Devanagari / Tamil / Bengali / Gurmukhi / Telugu / Urdu / Latin | `[AWAITING RATINGS]` | | |

### 7.5 Reliability

| Axis | Krippendorff's α | Verdict |
|---|---|---|
| TF / CA / CU / UPR | `[AWAITING RATINGS]` | |

### 7.6 Early observations

*To be written after the run.* The template below is deliberately structured so that a null or
inconvenient result is as easy to report as a clean one:

- Where did all three models fail together? *(a category-level finding, more useful than a ranking)*
- Where did they diverge beyond their confidence intervals? *(the only place a ranking claim is legitimate)*
- Which failure tags dominated, per script?
- Did the Rajasthan default appear, and was it concentrated in non-Devanagari prompts?
- Did any model's ranking **change** between the global and per-script views? *(the product thesis)*

---

## 8. Limitations — stated plainly

A reviewer should not have to find these for themselves.

1. **n=10 raters, 1 image per cell.** Fine for detecting large effects; useless for fine ranking.
   Where confidence intervals overlap, this eval does not separate those models, and no number
   of decimal places changes that.
2. **Minority scripts are thinly covered.** With 10 raters, Telugu or Gurmukhi may rest on 1–2
   qualified readers. Those cells are flagged and should be read as anecdote. This is a
   recruitment problem, not a statistics problem.
3. **Side-by-side triads make ratings partly relative.** A mediocre image looks better beside two
   bad ones. Blind pairwise avoids this but needs far more comparisons than 10 raters can supply.
   I chose power over contrast purity, and the absolute ordinal scores should be read as
   within-screen comparative judgements. UPR and win rates are unaffected.
4. **The panel is not representative of Indian MSME owners.** It is a script-qualified reader
   panel. Claims about what shop owners would *actually* do are directional at best.
5. **One generation per cell** conflates model capability with sampling luck on any single
   prompt. The variance sub-study (4 runs on P01 and P05) bounds this but does not remove it.
6. **Web-UI surfaces may rewrite prompts** invisibly, and preview models change without notice.
   Both are recorded where detectable and flagged where not.
7. **I wrote the prompts and the rubric and will score the ground truth.** That is a real
   single-author bias. At scale this separates into different people; see §9.

---

## 9. How I would scale this

### Stage 1 — Harden (2–4 weeks)
Prompt set 10 → ~200, stratified across 12 scripts × 8 business types × 6 occasions, **authored
by native speakers per script rather than by one person**. 3–5 generations per cell to separate
capability from sampling noise. Add Ideogram 3.0 as a fourth model — it markets text rendering
as its differentiator, so it directly tests whether strong Latin typography transfers to Indic
at all.

### Stage 2 — Josh Jobs as the rating layer (the real unlock)
**Josh Talks already owns the hardest input this eval needs.** ~20,000 daily active transcribers
across 25+ languages *is* a script-qualified rater panel — the one asset that cannot be
cheaply assembled by a competitor. The rating screen is already shaped like a Josh Jobs task:
a blinded triad, four taps, under two minutes.

That changes the achievable design:
- **500+ raters, genuinely script-native**, with per-script panels instead of best-effort coverage
- **Blind pairwise with Bradley–Terry / Elo** rather than triads, which removes the contrast-effect
  caveat entirely
- **Rater quality control borrowed wholesale from Question 2**: gold-standard honeypot images
  with known-wrong text, graduated trust scores, and weighting by demonstrated reliability
  rather than one-rater-one-vote
- **Recruit actual MSME owners** for the UPR question specifically, which is the one axis where
  the panel's non-representativeness genuinely bites

### Stage 3 — Automate the screen, keep humans as truth
Indic OCR (Google Vision / Surya / Tesseract Indic) can pre-score text fidelity at near-zero
marginal cost. The discipline that makes this safe: **measure OCR-versus-human agreement per
script first, and only automate where agreement is high.** Indic OCR is itself imperfect, so
OCR is a *screen* and humans remain *truth* — with a continuously audited sample. This is the
same "statistical signal routes attention, ground truth justifies the call" principle that
drives my answer to Question 2.

### Stage 4 — Product
Public per-script leaderboard, re-run on every model release, with longitudinal tracking so a
lab can see whether its Indic investment moved the number. Failure explorer for model teams.
Published methodology and open prompt set, so the result is citable and contestable.

---

## 10. UI / dashboard / leaderboard

Working prototype: [`dashboard/dukaan_bench_dashboard.html`](dashboard/dukaan_bench_dashboard.html)
— open it directly; it reads `dashboard_data.js` if `analyze.py` has run, and otherwise renders
blank with a prominent warning rather than showing invented numbers.

**The central product argument: one global leaderboard is the wrong product for India.**

The dashboard's script filter re-ranks every chart. A model that leads on Devanagari can sit at
the floor on Tamil or Gurmukhi — so a single "best image model" badge actively misinforms a
business owner in Chennai or Amritsar. **The per-script view is the product; the global average
is the marketing.** I don't know of a major image leaderboard that does this, and for a
multi-script market it is the difference between a useful tool and a decorative one.

Three surfaces, one pipeline:

| Surface | Job |
|---|---|
| **Leaderboard** | Makes the gap citable. Stat tiles, UPR with confidence whiskers, ITP dumbbell, per-script heatmap, head-to-head with "none" at full weight, and a published reliability table. |
| **Rating tool** | The collection surface — already shaped like a Josh Jobs task. |
| **Failure explorer** *(next build)* | Filter to every image tagged `rajasthan-default` or scored 0 on text, and see the actual failures. A leaderboard tells a lab *that* it lost; an example tells it *why*. |

Design decisions worth noting: confidence intervals are drawn, not hidden in a footnote, so
overlapping whiskers visibly refuse to support a ranking. Colour follows the model as a fixed
identity, so filtering never repaints the survivors. Every chart ships a table view. The
reliability table is on the dashboard rather than in an appendix, because an eval that publishes
scores while hiding whether its judges agreed is asking to be trusted on faith.

---

## 11. Final reflection

**1. Why did you choose this eval?**
Because it has a failure mode that is objectively checkable, commercially real, and currently
unsolved. Most image evals grade taste, which makes disagreement unresolvable. Here the prompt
specifies `मिष्ठान्न भंडार` and either the model rendered those exact characters or it didn't.
That hard anchor is what lets the softer axes mean anything. I also wanted the one-shot
constraint, because it converts a fuzzy quality question into a binary business decision: the
shop owner posts it, or she doesn't.

**2. Why is it useful for India?**
It targets the modal commercial creative act in a country of ~63 million MSMEs — a poster with
text on it, made by someone with a phone and no design software — and it tests the specific
thing that breaks for Indian users and nobody else: Indic script rendering across six writing
systems. It also catches a failure an India-blind eval would never look for, the collapse of 28
states into one Rajasthani tourist aesthetic.

**3. Why would an AI lab building for India care?**
It turns "does this work for India" into a metric you can regress against training runs, and the
English control tells them *which team owns the fix* — Indic tokenisation and data, or the
general text renderer. The per-script heatmap tells them where to spend the next annotation
budget. It costs under $10 a run and can gate every release.

**4. What did you learn from running the sample?**
*To complete after the run.* What I learned from **building** it: the English control was the
highest-leverage decision in the whole design — without it, a low Indic score is
uninterpretable and the result is a complaint rather than a diagnosis. The second thing was
that rater qualification is not a detail. My first instinct was to have all raters score all
scripts; that would have filled the spreadsheet with confident noise on five of six scripts.
Making **"I can't read this"** a first-class answer costs coverage and buys validity, and I'd
make that trade again.

**5. What would you improve with more time?**
In order of value: (a) **native-speaker prompt authors per script** — I wrote all ten prompts
and that is the biggest single-author bias in the design; (b) 3–5 generations per cell, since
n=1 conflates capability with sampling luck; (c) blind pairwise with Bradley–Terry to remove the
contrast-effect caveat; (d) **actual MSME owners** on the UPR question, the one axis where my
panel's non-representativeness genuinely bites; (e) the automated Indic-OCR pre-score, validated
per script before being trusted anywhere.

---

## Appendix — repository map

```
Q1_dukaan_bench/
├─ prompts/prompt_set_v1.json        10 prompts, exact strings, per-prompt rationale
├─ generation/
│  ├─ generate.py                    API + manual, same manifest either way
│  ├─ MANUAL_WORKFLOW.md             web-UI steps, naming, screenshot checklist
│  └─ requirements.txt · .env.example
├─ rating/
│  ├─ RATING_PROTOCOL.md             rubrics, blinding, pre-registered analysis
│  ├─ CONSENT_FORM.md                18+, consent statement, withdrawal rights
│  └─ rater_tool.html                blinded triad UI, offline, CSV export
├─ analysis/
│  ├─ analyze.py                     UPR, CIs, ITP, per-script, α, ground-truth check
│  └─ make_synthetic_ratings.py      PIPELINE TEST ONLY — never a result
├─ dashboard/dukaan_bench_dashboard.html
├─ images/<model_key>/               generated images
└─ evidence/                         manifest.csv, raw/, screenshots/, consent/
```
