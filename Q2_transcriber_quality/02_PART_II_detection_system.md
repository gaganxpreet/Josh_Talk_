# Question 2, Part II — Detection system design

**Recommendations for the engineering team**

Josh Talks AI Product Task · October 2026

---

## 0. The brief's hardest line, answered directly

> *"Keep in mind that the logic/metric you share will be used to block transcribers' accounts,
> so make sure you are 100% sure about the logic."*

I can't be 100% sure about any statistical signal, and neither can anyone else. That isn't
pessimism about the metrics — it's a property of what the data contains. As Part I establishes,
every available column measures **effort**, not **accuracy**. A behavioural outlier is evidence
that work *may not* have been done; it is never proof that work *was* wrong.

So my recommendation is to change what the system is 100% sure *about*:

> ### Statistical signals route attention. Ground truth justifies action.
>
> Build a system that can be 100% sure about a **planted, known-answer task** — and block on
> that. Use the Part I metrics to decide *who gets more planted tasks* and *whose work gets
> reviewed*, never to block on their own.

This is not a softer system. It is a **harder** one: honeypots are unfalsifiable where
percentiles are arguable, they can't be gamed by threshold-hugging, and they survive a legal or
PR challenge in a way "his listen-ratio was in the bottom 5%" does not. It is also cheaper,
because it concentrates expensive human review on the small set of accounts that failed a test
with a known answer.

**If you take one thing from this document: do not ship a system that blocks on Part I metrics
alone. Ship honeypots first.**

---

## 1. System architecture

```
                    ┌─────────────────────────────────────────┐
  every submission  │  1. INGEST                              │
  ───────────────►  │  derive listen_ratio, edit_distance,     │
                    │  is_cosmetic, len_ratio  (per task)     │
                    └──────────────────┬──────────────────────┘
                                       │
                    ┌──────────────────▼──────────────────────┐
                    │  2. COHORT NORMALISE                    │
                    │  percentile within                      │
                    │  (language × device × task_type)        │
                    │  NEVER a global constant                │
                    └──────────────────┬──────────────────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        │                              │                              │
┌───────▼─────────┐        ┌───────────▼───────────┐      ┌───────────▼──────────┐
│ 3a. TQS         │        │ 3b. HONEYPOTS         │      │ 3c. PEER CONSENSUS   │
│ behavioural     │        │ planted known-answer  │      │ ADR vs others on     │
│ score 0–100     │        │ clips → HCR           │      │ the same clip        │
│ ROUTES ONLY     │        │ ► THE BLOCKING SIGNAL │      │ corroborates         │
└───────┬─────────┘        └───────────┬───────────┘      └───────────┬──────────┘
        └──────────────────────────────┼──────────────────────────────┘
                                       │
                    ┌──────────────────▼──────────────────────┐
                    │  4. RESPONSE LADDER                     │
                    │  T0 monitor → T1 coach → T2 throttle    │
                    │  → T3 suspend+review → T4 block         │
                    │  ONLY T4 blocks. A HUMAN SIGNS T4.      │
                    └─────────────────────────────────────────┘
```

---

## 2. The core mechanism: gold-standard honeypots

### 2.1 What it is

Seed the task stream with clips whose correct transcription is already known, where
**Whisper's text has been deliberately altered to contain an unmissable error**. If the
transcriber submits it unchanged, they did not listen. There is no innocent explanation, no
cohort normalisation needed, no threshold argument.

### 2.2 Designing the planted error

The error must be **unmissable to anyone listening** and **invisible to anyone not listening** —
that gap is the entire mechanism.

| Planted error type | Example | Why it works |
|---|---|---|
| **Number substitution** | audio says "तीन सौ" → text says "आठ सौ" | Numbers are salient and unambiguous; no dialect defence |
| **Negation flip** | audio "नहीं आया" → text "आया" | Changes meaning completely; impossible to miss |
| **Name swap** | audio "रमेश" → text "सुरेश" | Clearly wrong, clearly audible |
| **Spliced nonsense word** | a real non-word inserted mid-sentence | Catches partial listening |
| **Extra clause** | a short phrase present in text, absent in audio | Catches "read-only" reviewers |

**Do not** plant subtle errors — ambiguous phonemes, dialect variants, punctuation. A subtle
honeypot fails honest transcribers and destroys the one signal you can be certain about.

Each honeypot carries a difficulty label, and **only `obvious`-tier honeypots are admissible as
blocking evidence.**

### 2.3 Metrics

```
HCR (Honeypot Catch Rate) = honeypots where the user corrected the planted error
                            ─────────────────────────────────────────────────────
                                    honeypots served to the user

HFR (Honeypot False-edit Rate) = share of CLEAN control honeypots the user "corrected"
                                 (a sanity check: someone editing everything blindly
                                  catches planted errors by accident, and HFR exposes it)
```

**Serve clean controls too.** Roughly one clean control per two planted ones. Without them, a
user who edits every single task indiscriminately scores a perfect HCR while doing no real work.
This asymmetry is how naive honeypot systems get gamed, and the control arm closes it.

### 2.4 Rates and schedule

| Account state | Honeypot rate |
|---|---|
| New (first 50 tasks, probation) | 1 in 8 |
| Established, good standing | 1 in 25 |
| Flagged by TQS | 1 in 6 |
| Post-appeal / reinstated | 1 in 10 |

Rotate the honeypot pool continuously and never serve the same honeypot to the same user twice.
Keep the pool size well above what any individual sees, or the pool leaks through word of mouth —
assume transcribers talk to each other, because they do.

### 2.5 Thresholds for action

| Condition | Action |
|---|---|
| `HCR < 0.70` over ≥ 10 obvious honeypots | T2 throttle + coaching |
| `HCR < 0.40` over ≥ 10 obvious honeypots | T3 suspend pending human review |
| `HCR < 0.25` over ≥ 15 obvious honeypots | T3 → T4 recommended; **human confirms** |
| `HCR < 0.40` **and** `HFR > 0.60` | T3 — blind-editing pattern, strongest case |

Minimum 10 honeypots before any action. At a 1-in-25 rate that's ~250 tasks, which is why the
probation rate is 1-in-8 — a bad actor hits the evidence bar in ~80 tasks, not 250.

---

## 3. TQS — the routing score (and what it must never do)

A 0–100 composite, computed **per cohort percentile**, used to allocate review attention and
honeypot density. **It does not block anyone.**

| Component | Weight | Source |
|---|---|---|
| Sub-realtime rate | 30 | Signal 1 |
| Anomalous deference (ADR) | 30 | Signal 2 |
| Cosmetic-edit share | 15 | Signal 3 |
| Audio insensitivity | 15 | Signal 4 |
| Throughput + degenerate output | 10 | Signals 5–6 |

Each component maps to a cohort percentile, then weights combine. Minimum 30 completed tasks
before TQS is computed at all; below that it is reported as `insufficient_data`, not as a
flattering or punitive default.

**Why weights, honestly.** These are judgement calls reflecting evidential strength from Part I,
not fitted parameters. They should be **re-fitted by logistic regression against honeypot
outcomes** once 4+ weeks of shadow data exist — at which point the weights become empirical and
this table becomes a historical note. Until then, treat TQS as a triage heuristic and say so
internally, so nobody mistakes it for a calibrated probability.

---

## 4. The response ladder

The key design claim: **most low-quality transcribers are untrained, not malicious.** Coaching
them is cheaper than replacing them, and good Indic transcribers are scarce — a wrongly blocked
one is a lost supply-side asset in a market where supply is the constraint.

| Tier | Trigger | Action | User-visible? | Reversible? |
|---|---|---|---|---|
| **T0 Monitor** | TQS bottom 20% of cohort | Raise honeypot rate. Nothing else. | No | n/a |
| **T1 Coach** | TQS bottom 10%, or `HCR < 0.70` | In-app message showing a **specific diff** of a task they rushed, next to the correct text. Short retraining module. | Yes | n/a |
| **T2 Throttle** | T1 unimproved after 50 tasks, or `HCR < 0.70` sustained | Daily task cap reduced. 100% of output to QC review. **Payment escrowed, not forfeited.** | Yes | Auto-lifts on improvement |
| **T3 Suspend** | `HCR < 0.40` over ≥ 10, or T2 unimproved | Account paused. Human reviewer listens to 20 sampled clips. Appeal opens immediately. | Yes | Yes |
| **T4 Block** | T3 human review confirms non-listening | Account blocked. Written reason. Appeal preserved. | Yes | Via appeal |

### Non-negotiable rules

1. **No tier above T2 fires on behavioural metrics alone.** T3 and T4 require honeypot failure
   or human review.
2. **A human signs every T4.** No automated permanent block, ever.
3. **Escrow, never confiscate.** Withheld payment is released if review clears the user.
   Confiscating pay on an unproven statistical flag is the worst possible failure mode — it
   takes real income from someone who may well be innocent.
4. **Appeals resolve in < 48 hours**, reviewed by someone who did not raise the flag.
5. **Publish the quality bar up front.** Tell transcribers at onboarding what good work looks
   like — listen fully, fix words not punctuation, expect spot-checks. Most "bad actors"
   genuinely don't know the standard. A system that enforces a secret standard is a trap.
6. **Cold start protection.** First 50 tasks are probation: 3× honeypots, 100% QC sample, paid
   normally, **and not blockable on TQS.** A new user has no history, so their percentile is noise.

---

## 5. Validation before launch — the actual answer to "100% sure"

**Do not ship this live. Ship it in shadow mode.**

### Phase 1 — Shadow (4 weeks)
Compute every score, take **zero** user-facing action, log everything. Serve honeypots (they're
harmless and generate the labels you need).

### Phase 2 — Measure against truth
Hand-audit **200 flagged + 200 unflagged** tasks with expert transcribers who don't know the
flag status. This produces the only numbers that matter:

- **Precision at the T4 threshold** — of accounts the system would have blocked, how many were
  genuinely not listening?
- **Recall** — of accounts experts judged bad, how many did the system catch?
- **Disparate impact** — flag rate by language, device class, region and gender.

### Phase 3 — Launch gates
Every one of these must hold:

| Gate | Requirement | Why |
|---|---|---|
| T4 precision | **≥ 0.95** | ≤ 1 in 20 recommended blocks wrong — and a human still reviews each |
| T2 precision | ≥ 0.80 | Throttling is reversible, so a looser bar is acceptable |
| Disparate impact | No cohort flagged > 2× the overall rate without an explanation grounded in audited quality | Prevents the system from penalising low-resource languages and cheap devices |
| Honeypot validity | Expert panel confirms every `obvious` honeypot is unmissable | A bad honeypot poisons the only clean signal |
| Timer semantics | Documented and verified by engineering | Signal 1 is void without this |
| Appeal path | Live and staffed before the first T2 fires | Don't build enforcement before recourse |

### Phase 4 — Ongoing
- Re-validate quarterly. **Whisper improves, so accept rates legitimately rise over time** —
  a threshold frozen in July 2026 becomes wrong by 2027.
- Monitor for **threshold-hugging**: users clustering just above a cutoff are gaming it, which is
  itself a signal and a reason not to publish exact numbers.
- Track appeal overturn rate. **Rising overturns mean the thresholds are wrong**, not that
  appeals are too generous.

---

## 6. Gaming resistance

Whatever you deploy, people adapt. Design for it from day one.

| Attack | Defence |
|---|---|
| Add a full stop to flip `is_edited` | Signal 3 (cosmetic detection) — already covered |
| Idle on each task to inflate `time_taken` | Timer must pause on blur; detect suspiciously *uniform* times; high time with zero edits is its own flag |
| Learn the exact thresholds | Publish the *standard*, never the *cutoffs*. Jitter the review sample. Monitor threshold-hugging. |
| Recognise and only fix honeypots | Clean control honeypots + HFR; large rotating pool; never repeat a honeypot to a user |
| Script/paste submissions | Signal 5, plus keystroke-cadence telemetry if available |
| Farm multiple accounts | Device fingerprint, payment-account overlap, submission-timing correlation across accounts |

---

## 7. Engineering requirements

**Data the platform must start capturing** (the current schema cannot support a defensible system):

| Field | Why it's required |
|---|---|
| `playback_speed_used` | **Signal 1 is void without it** |
| `audio_play_events[]` (timestamps, seek positions, replays) | Turns "time spent" into "actually listened", the single biggest accuracy upgrade available |
| `timer_semantics_version` | So thresholds can be re-derived when timer behaviour changes |
| `device_class`, `connection_type` | Required for fair cohort normalisation |
| `task_type` (free speech vs scripted read) | Signal 6 is invalid without it |
| `guideline_version` | Signal 3 inverts if guidelines require punctuation work |
| `is_honeypot`, `honeypot_id`, `planted_error_span` | The blocking signal |
| `keystroke_count` | Distinguishes typing from pasting |

**Changes to task allocation:**
1. **Deliberate overlap** — route ~5% of clips to 3+ transcribers. This single change enables
   Signal 2, the strongest statistical inference available, and gives you a continuous quality
   baseline for free.
2. **Honeypot injection** at the rates in §2.4.
3. **Duration stratification** — ensure each user receives a spread of clip lengths so Signal 4
   is computable and fair.

**Build order** (highest value first):
1. Honeypot infrastructure + `audio_play_events` — *this is the whole system; everything else is triage*
2. Cohort normalisation + TQS in shadow mode
3. Overlap allocation for peer consensus
4. Coaching UI (T1) — likely the highest ROI item, since it converts bad workers into good ones
5. Throttle/escrow (T2), then review queue + appeals (T3/T4)

---

## 8. The recommendation, in the form the brief asked for

> **If a transcriber exhibits X, Y, and/or Z behaviour, block the user.**

Here is that rule, stated exactly as I would be willing to defend it:

### 🔴 Block (T4) — all four must hold

1. **`HCR < 0.40`** across **≥ 10 obvious-tier honeypots**, *and*
2. **≥ 2 corroborating behavioural signals** in the bottom 5% of their **cohort** (language ×
   device × task type) — e.g. `sub_realtime_rate > 0.50` and `ADR > 0.70`, *and*
3. **A human reviewer has listened to ≥ 20 of their clips** and confirmed the work is not
   plausibly done, *and*
4. The user has **already passed through T1 coaching and T2 throttling** without improvement,
   **or** `HCR < 0.15` (which is deliberate, not untrained).

### ⚡ Immediate T3 suspend — any one, pending human review within 48h

- `HCR < 0.25` over ≥ 15 obvious honeypots
- `empty_rate > 0.05` over ≥ 30 tasks (submitting blanks)
- Multi-account farming confirmed by device/payment fingerprint
- `sub_realtime_rate > 0.90` over ≥ 50 tasks **with playback speed confirmed at 1×**

### 🟠 Throttle + escrow (T2) — reversible, no human needed
`HCR < 0.70` over ≥ 10 honeypots, **or** TQS in the bottom 10% of cohort over ≥ 50 tasks.

### 🟡 Coach (T1) — the tier that should fire most often
TQS in the bottom 20% of cohort, or any single Tier-A signal breaching its investigate threshold.

**Explicitly NOT grounds for a block, on their own, ever:**
a high accept rate · a low listen ratio · a high cosmetic-edit share · low audio sensitivity ·
a low TQS · any global (non-cohort) threshold breach · anything at all computed from fewer than
30 tasks.

---

## 9. What I'd want to be asked in review

Three places this design could be wrong, so a reviewer doesn't have to find them:

1. **Honeypots cost real money.** At 1-in-25 you're paying for ~4% of tasks that produce no
   usable data, plus the cost of authoring and rotating the pool. I think that's clearly worth it
   versus the cost of bad data reaching a training run — but it is a real budget line and
   someone should price it properly rather than take my word for it.
2. **Peer consensus can punish genuine experts.** A dialect specialist who is right while the
   crowd is wrong looks deviant. Trust-weighting consensus helps but doesn't fully solve it, and
   the error lands on exactly the most valuable contributors. This is the weakest part of the
   design and I'd want a specialist-identification path before leaning on ADR hard.
3. **Everything here measures listening, not skill.** A transcriber who listens attentively and
   still gets the dialect wrong passes every check in this document. Catching *that* needs
   genuine inter-annotator agreement on overlapping work and a language-expert review layer —
   a bigger build than this one, and the natural next project.

---

→ [Part I: the warning signs](01_PART_I_warning_signs.md) ·
→ [Runnable analysis script](analysis/transcriber_quality.py)
