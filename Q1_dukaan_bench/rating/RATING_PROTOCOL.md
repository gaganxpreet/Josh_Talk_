# Dukaan Bench — Rating Protocol

This document is the full judging specification. It exists so that (a) another person could
re-run this eval and get comparable numbers, and (b) a reviewer can see exactly how a score
was produced.

---

## 1. What we are measuring, and the one number that matters

A shop owner with no design skills types one prompt and gets one image. The only question
that actually matters to them is: **can I post this, as-is, right now?**

So the headline metric is:

> ### UPR — Usable Poster Rate
> The percentage of a model's images that a rater says they would post **without any editing**.

Everything else in this protocol exists to explain *why* a model's UPR is what it is.

**Why UPR and not a 1–10 quality score.** Three reasons:

1. **It's a decision, not an opinion.** "Would you post this?" has a right answer for a given
   rater in a way "rate the aesthetics 1–10" does not. Binary decisions are far less prone
   to rater scale-drift — the problem where one rater's 7 is another's 4.
2. **It matches the actual economics.** There's no partial credit in the real use case. An
   image with one wrong Devanagari character is not 90% useful; it's unusable, because posting
   a misspelt sign makes the shop look careless to its own customers.
3. **It's legible to a decision-maker.** "GPT Image 1 produces a usable Hindi poster 2 times
   in 10" is a sentence that survives being repeated in a meeting. "GPT Image 1 scores 6.4"
   is not.

### The four diagnostic axes

| Axis | Abbr | Type | What it isolates |
|---|---|---|---|
| Indic Text Fidelity | **TF** | 0–3 ordinal, **ground-truth checkable** | Is the requested text actually spelled correctly? |
| Cultural Authenticity | **CA** | 0–3 ordinal | Does this look like a real Indian shop, or a foreign stock photo with Indian props? |
| Commercial Usability | **CU** | 0–3 ordinal | Composition, legibility, does it work as a poster |
| Head-to-head preference | **Win** | forced choice + "none" | Which would you actually use |

### Derived metrics

- **ITP — Indic Text Penalty** = `TF(P10, English control) − mean TF(P01…P09, Indic)`
  Separates *"bad at text in images"* from *"bad at Indic text in images"*. These two findings
  point at completely different fixes, and no amount of aggregate scoring distinguishes them
  without a matched control.
- **NoneRate** = % of head-to-head rounds where the rater picked "none of these."
  The most brutally honest number in the eval. If it's high, the category isn't served by
  *any* current model, and that is the finding.
- **Script-level TF** — TF broken out by script. Tests whether "Indic support" is really just
  "Hindi-ish support."

---

## 2. The rubrics

Raters see these anchors on screen at all times. Ordinal scales without written anchors are
the main source of noise in human evals, so every level below is defined by an observable
property, not by a vibe.

### TF — Indic Text Fidelity (0–3)

The rater is shown the **exact target string** and compares character by character.

| Score | Anchor |
|---|---|
| **3** | All requested text is present, **every character correct**, and comfortably readable. A native reader would see nothing wrong. |
| **2** | Text present and readable; meaning fully clear; **one** minor defect — a single wrong or missing matra/diacritic, slightly odd letter spacing, or minor baseline wobble. A native reader notices but understands instantly. |
| **1** | Text present but **wrong enough to look bad to a customer** — misspelt words, dropped or duplicated characters, broken conjuncts, mangled letter-joining — OR text is correct but cut off / overlapping / partially hidden. |
| **0** | **Pseudo-script**: shapes that resemble the script but are not real characters, or the wrong script entirely, or no text at all. |

**Critical rule — rater qualification.** TF may **only** be scored by someone who natively
reads that script. Every rating screen has an explicit **"I can't read this script"** button,
and skipping is the *correct* action, not a failure. A Hindi reader guessing at Tamil
spelling would produce numbers that look like data and aren't.

**Ground truth.** The researcher independently scores TF for all 30 images against the target
strings (`TF_GT`). We report agreement between `TF_GT` and the script-native raters as a check
on the instrument itself. Where they disagree systematically, the rubric is at fault and we
say so.

### CA — Cultural Authenticity (0–3)

| Score | Anchor |
|---|---|
| **3** | Looks unmistakably like the real Indian setting named in the prompt. Shop layout, products, clothing, signage density and lighting are all plausible. |
| **2** | Broadly and recognisably Indian, but with details that are off — wrong regional cues, implausibly tidy/affluent for the business type, generic product packaging. |
| **1** | Generic international imagery with Indian motifs applied on top. Would read as "AI's idea of India" to an Indian viewer. |
| **0** | Clearly not India, **or** stereotyped/exoticised — the failure we call the **"Rajasthan default"**: camels, forts, turbans and marigolds pasted onto a prompt about a Kolkata clothes shop or a Chennai textile store. |

> **Note on the Rajasthan default.** We call this out as its own named failure mode because it
> is the most common and most revealing India-specific error. A model that collapses all of
> India into one tourist-poster aesthetic has learned "India" as a single visual token rather
> than as 28 states. Raters are asked to tag it explicitly so we can count it, and a tag of
> this type **caps CA at 1 regardless of image quality** — because for the shop owner in
> Chennai, a Rajasthani poster is simply the wrong poster.

Raters also tag, multi-select, whichever apply:
`rajasthan-default` · `wrong-region` · `wrong-festival-iconography` ·
`non-indian-faces` · `implausibly-affluent` · `stereotyped-poverty` · `none`

### CU — Commercial Usability (0–3)

Judged **ignoring text correctness** (TF already covers that) — this is about the poster as a
poster.

| Score | Anchor |
|---|---|
| **3** | Clear focal hierarchy, text has room to breathe, high contrast, reads at thumbnail size on a phone. Looks professionally made. |
| **2** | Decent but imperfect — slightly cramped, mildly awkward crop, a little cluttered. Still clearly usable. |
| **1** | Significant problems — important elements near/off the edge, low contrast, busy background behind text, unreadable at thumbnail size. |
| **0** | Not usable as a poster — no space for text, chaotic composition, visible artefacts or mangled hands/objects in a prominent position. |

### The UPR question

> **"Imagine you own this shop. Would you post this image to your WhatsApp Status right now,
> with no editing at all?"** → **Yes / No**

Asked separately from CU so the two cross-check each other. A rater who gives CU=3 but says
"No" is telling us something the ordinal scale missed, and we read those cases individually.

### Head-to-head

Three images for the same prompt, shown side by side, **blinded and position-randomised**:

> **"Which one would you actually use?"** → A / B / C / **None of these**

"None of these" is deliberately given equal visual weight to the other options. Most arena-style
evals force a choice, which manufactures a winner even when every option is unusable. In a
category where failure is the expected outcome, suppressing "none" would be the single biggest
way to produce a misleading leaderboard.

---

## 3. Study design

### Presentation: blinded triads

Each rater sees **10 screens**, one per prompt. Each screen shows the 3 model outputs for that
prompt, side by side, labelled only A/B/C.

- **Model identity is hidden.** Filenames are mapped to opaque IDs by the rating tool.
- **Position is randomised per rater**, so position bias cancels across raters.
- **Prompt order is randomised per rater**, so fatigue doesn't systematically hit later prompts.

### The trade-off we are accepting, stated openly

Side-by-side triads make ratings partly *relative* — a mediocre image looks better next to two
bad ones (contrast effects). Pure blind pairwise comparison, as Chatbot Arena and Artificial
Analysis use, avoids this but needs far more comparisons than 8–10 raters can supply.

We chose triads because with n=10 raters, statistical power matters more than contrast purity,
and because the side-by-side view mirrors how a shop owner would actually choose between
options. **The absolute ordinal scores should therefore be read as within-screen comparative
judgments, not as calibrated absolute quality.** The head-to-head win rates and UPR are
unaffected by this concern. At scale (§ scaling plan in the main document) we move to blind
pairwise with Bradley–Terry.

### Rater load

10 screens × (9 ordinal ratings + 1 choice + 3 UPR yes/no) ≈ 18–22 min. Piloted with 1 rater
before launch to confirm. Anything over ~25 minutes and quality degrades measurably, which is
why the set is 10 prompts and not 30.

### Rater recruitment and qualification

Target: **8–10 raters**, all 18+, with written consent.

We record for each rater:
- scripts they read natively (drives TF eligibility)
- whether they have ever run or worked in a small business / family shop
- city / state (so we can see whether non-Rajasthani raters penalise the Rajasthan default more)
- age bracket

**We do not pretend this is a representative sample of Indian shop owners.** It isn't, at n=10.
What it is: a qualified-reader panel sufficient to detect large effects. The main document
states exactly which conclusions this supports and which it doesn't.

### Attention / quality checks on raters themselves

Mirroring the logic of Question 2 — if we're measuring quality, we should measure our own
raters' quality too:

1. **A planted-failure screen.** One image in the set has unambiguous pseudo-script. A rater who
   scores it TF≥2 is either not looking or can't read the script; their TF data is excluded.
2. **Duplicate screen.** One prompt is shown twice, late in the session, with positions
   re-randomised. Within-rater consistency across the two gives us a per-rater reliability figure.
3. **Time floor.** Screens completed in under 15 seconds are flagged for review.

### Reliability reporting

We report **Krippendorff's α** (ordinal) for TF, CA and CU, and **% agreement** on the UPR
binary. If α < 0.6 for an axis, we report that axis as *indicative only* and say so in the
headline. Publishing an unreliable axis as if it were solid is worse than not measuring it.

---

## 4. Analysis plan (pre-registered — written before ratings were collected)

Fixing this in advance prevents us from fishing for whichever cut makes the story cleanest.

**Primary**
1. UPR per model, with 95% bootstrap CIs (10,000 resamples, clustered by rater).
2. Head-to-head win rate per model + NoneRate.

**Secondary**
3. Mean TF per model, overall and per script.
4. ITP per model.
5. Mean CA and CU per model.
6. Rajasthan-default tag frequency per model.

**Checks**
7. Krippendorff's α per axis.
8. `TF_GT` vs script-native rater agreement.
9. Within-rater consistency on the duplicate screen.
10. Variance sub-study: run-to-run TF spread on P01 and P05.

**Stopping rule.** We analyse once, after all ratings are in. No interim peeking, no adding
raters because the result looked unclear.

**What would falsify our hypothesis.** We expect a large ITP (models much worse at Indic than
Latin text). If ITP ≈ 0 across all three models, our framing is wrong and the interesting
story is general text rendering, not Indic specifically. We report that outcome if we see it.
