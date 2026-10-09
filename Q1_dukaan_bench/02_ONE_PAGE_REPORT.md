# Dukaan Bench — One-Page Report

**Can frontier image models make a usable poster for an Indian small business?**
Josh Talks AI Product Task · Q1 · October 2026

---

### The eval

A kirana-store owner in Kanpur wants a Diwali offer poster for WhatsApp Status. She types one
prompt, she isn't a designer, and she won't open Canva to fix the output. **Dukaan Bench** tests
whether three frontier models can serve that moment.

**Category:** local commerce / MSME marketing creatives.
**Use case:** one-shot festival or offer poster containing Indic-script text.
**Headline metric — Usable Poster Rate (UPR):** share of images a rater would post **as-is, with
no editing**. Binary, because the real decision is binary — a poster with one wrong Devanagari
character isn't 90% useful, it's unusable, and posting a misspelt sign makes the shop look
careless to its own customers.

### Why it matters for India, and to a lab building for it

India has ~63 million MSMEs, and WhatsApp is their dominant marketing channel — a poster with
text on it is close to the modal commercial creative act in the country. Latin text-in-image
largely got solved between 2023 and 2025; **Indic scripts did not**, for structural reasons:
stacked conjuncts (`ष्ठ`, `न्न`), matras above and below the baseline, the connecting
`शिरोरेखा`, right-to-left cursive shaping in Urdu, native numerals (`৫০` ≠ `50`), and far less
paired training data showing correct Indic typography.

For a lab, this converts an unfundable question — *"does our model work for India?"* — into a
metric you can regress against training runs and gate releases on, for under $10 a run.

### Core setup

| | |
|---|---|
| **Models** | OpenAI GPT Image 1 · Google Gemini 2.5 Flash Image · Google Gemini 3.1 Flash Image Preview |
| **Prompts** | 10 — six Indic scripts (Devanagari ×4, Tamil, Bengali, Gurmukhi, Telugu, Urdu) **+ one matched English control** |
| **Images** | 30 (1 per model per prompt; first output, not best output) |
| **Panel** | 8–10 consenting adults, 18+, script-qualified |
| **Presentation** | Blinded A/B/C triads; position and order randomised per rater from their ID |
| **Axes** | Text Fidelity (0–3, ground-truth checkable) · Cultural Authenticity · Poster Usability · "Would you post it?" · head-to-head with **"none of these"** |

**Three design choices that carry the eval:**

1. **The English control (P10).** Identical to P01 except the script. The gap —
   the **Indic Text Penalty** — separates *"can't render text"* from *"can't render **this**
   text."* Same headline number, two completely different roadmaps; without the control you
   can't tell which you're looking at.
2. **"None of these" at equal weight.** Most arenas force a choice, manufacturing a winner even
   when every option fails. Where failure is the expected outcome, hiding that option is the
   fastest route to a misleading leaderboard.
3. **Raters only score text in scripts they read natively.** "I can't read this script" is a
   first-class button. A Hindi reader guessing at Tamil spelling produces numbers that look like
   data and aren't.

### Main findings

> **`[AWAITING RATINGS]`** — design, prompt set, tooling and dashboard are complete and
> runnable; the generation run and participant panel are the remaining steps. I have not written
> in illustrative figures: a fabricated number in a document about evaluation integrity would
> defeat the document. `analysis/analyze.py` populates every table automatically.

Pre-registered expectations, recorded before collection so they can be scored as right or wrong:

- A **large Indic Text Penalty** on all three models — the eval's central hypothesis. *If ITP ≈ 0,
  the framing is wrong and the story is general text rendering; that gets reported too.*
- **Devanagari ≫ Tamil/Bengali/Telugu/Gurmukhi ≫ Urdu**, i.e. "Indic support" is really
  "Hindi-ish support."
- A **non-trivial NoneRate** — the category may not be served by any current model.
- The **"Rajasthan default"**: models collapsing 28 states into camels, forts and marigolds
  regardless of whether the prompt said Chennai or Kolkata. Tagged explicitly, and it caps
  cultural authenticity at 1 — for a shop owner in Chennai, a Rajasthani poster is simply the
  wrong poster.

### The most important takeaway

> **One global leaderboard is the wrong product for India.**
>
> The dashboard's script filter re-ranks every chart, and a model that leads on Devanagari can
> sit at the floor on Tamil or Gurmukhi. A single "best image model" badge actively misinforms a
> business owner in Chennai or Amritsar. **The per-script view is the product; the global average
> is the marketing.**

And the thing that makes this defensible rather than just another arena: **Josh Jobs already has
~20,000 daily active contributors across 25+ languages.** Script-qualified raters at scale are
the single hardest input to assemble and the one Josh Talks already owns. The rating screen is
already shaped like a Josh Jobs task — a blinded triad, four taps, under two minutes. The
leaderboard is just the visible end of that panel.

### Honest limits

n=10 raters and one image per cell detects large effects and cannot support fine ranking —
where confidence intervals overlap, this eval does **not** separate those models. Minority
scripts may rest on 1–2 qualified readers and are flagged as anecdote. Side-by-side triads make
ratings partly relative. The panel is script-qualified, not representative of MSME owners. I
wrote all ten prompts myself, which is the design's biggest single-author bias — native-speaker
prompt authors per script is the first thing I'd fix with more time.

---

**Full detail:** [`01_MAIN_DOCUMENT.md`](01_MAIN_DOCUMENT.md) ·
**Live prototype:** [`dashboard/dukaan_bench_dashboard.html`](dashboard/dukaan_bench_dashboard.html)
