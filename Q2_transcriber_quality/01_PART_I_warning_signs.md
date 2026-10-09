# Question 2, Part I — Warning signs of low-quality transcription work

Josh Talks AI Product Task · October 2026

---

## 0. The thing to get straight before any metric

Every signal available in this dataset measures **effort**, not **accuracy**.

`is_edited`, `time_taken_by_user`, `segment_character_per_second` and edit distance all describe
*how a transcriber behaved*. None of them describes *whether the final text is right*. Those
come apart in both directions:

- A **diligent but unskilled** transcriber listens carefully, spends 3× the audio duration,
  edits heavily — and produces worse text than Whisper did, because they don't know the
  dialect. Every behavioural metric says "excellent."
- A **fast expert** on a clean Hindi batch accepts 80% of Whisper's output unchanged because it
  was already correct. Every behavioural metric says "rubber-stamper."

So the honest framing is:

> **These signals cannot establish that work is wrong. They can only establish that work was
> not plausibly done.** That is a narrower claim, and it is the only one the data supports.

That distinction drives the whole of Part II: behavioural signals **route attention**;
only ground truth **justifies a block**. Any system that blocks accounts on effort proxies
alone will fire on honest people, and the people it fires on are low-income freelancers whose
income depends on the platform.

---

## 1. Derived features

Nothing below uses a raw column directly; each needs normalising first.

| Feature | Definition | Why |
|---|---|---|
| `listen_ratio` | `time_taken_by_user / duration` | The single most informative ratio in the dataset. Absolute time is meaningless without clip length. |
| `edit_distance` | Levenshtein(`whisper_text`, `user_text`) | `is_edited` is a boolean and trivially gameable; distance is not. |
| `norm_edit` | `edit_distance / max(1, len(whisper_text))` | Scale-free edit magnitude. |
| `is_cosmetic` | `True` if the texts differ but are identical after stripping punctuation, whitespace and case | Catches edits made only to flip the `is_edited` flag. |
| `len_ratio` | `len(user_text) / max(1, len(whisper_text))` | Detects deletion-to-pass. |
| `accept_rate` | Per user: share of tasks with `is_edited == No` | Baseline deference to the AI. |
| `clip_consensus_edit` | Per `recording_url`: share of *other* users who edited it | **The gold in this dataset**, if clips overlap across users. |
| `ADR` | Per user: share of their accepted clips where `clip_consensus_edit ≥ 0.70` | Peer-relative, so it survives easy-batch confounding. |
| `audio_sensitivity` | Per user: Spearman ρ(`duration`, `time_taken_by_user`) | Does this person's time respond to the audio at all? |
| `effective_edit_rate` | `edit_distance / max(1, time_taken - duration)` | Chars changed per second of non-listening time. Catches paste/scripting. |
| `self_dup_rate` | Share of a user's submissions duplicating their own text on a *different* `recording_url` | Templated output. |

**The first thing to check before anything else:** does `recording_url` overlap across users? If
yes, Signal 2 becomes available and is by far the strongest inference the data permits. If no,
getting deliberate overlap into the task allocator is the highest-value engineering change on
this list — see Part II.

---

## 2. The warning signs, ranked by how much weight they can bear

I've ranked these by **evidential strength**, because a flat list invites the mistake of
treating a weak signal like a strong one in a system that blocks people.

---

### 🔴 Signal 1 — Sub-realtime completion *(Tier A: near-dispositive)*

**What it tells us.** You cannot review audio you did not play. If a task was completed in less
time than the clip runs, the transcriber did not hear all of it. This is the only signal in the
dataset that approaches physical impossibility rather than mere improbability, which is why it
ranks first.

Honest work on Indic audio runs roughly **1.5×–4×** the clip duration: play it once, re-scrub the
unclear parts, retype words Whisper got wrong. A population median near 1.0× means the panel is
skimming; an individual consistently below 1.0× is not listening.

**How to measure.**
```
listen_ratio        = time_taken_by_user / duration
sub_realtime_rate   = share of a user's tasks with listen_ratio < 0.9
median_listen_ratio = median(listen_ratio) over the user's tasks
```
Exclude clips under ~4 seconds, where fixed UI overhead swamps the ratio.

**Red-flag thresholds** *(placeholders until calibrated on the real distribution — see the
warning at §4)*

| Level | Condition |
|---|---|
| Monitor | `median_listen_ratio < 1.3` over ≥ 30 tasks |
| Investigate | `sub_realtime_rate > 0.25` over ≥ 30 tasks |
| Strong | `sub_realtime_rate > 0.50` over ≥ 50 tasks **and** `median_listen_ratio < 1.0` |

The *rate across many tasks* is what carries the signal. A single sub-realtime task is noise.

**When good transcribers show this innocently.** This list is longer than it first appears, and
every item is a real false-positive route:

- **Playback speed.** If the platform offers 1.5×/2×, a fluent listener legitimately finishes
  below 1.0× ratio. **This single question can invalidate the entire signal** — and the dataset
  as described has no speed column. Resolve it with engineering before using this metric for
  anything.
- **Timer semantics.** Does the timer start on page load, on audio load, or on first play? Does
  it pause on tab blur? Does it keep counting if the user walks away? Each answer changes the
  threshold, and two of them break it.
- **Re-served clips.** A user who already heard a clip (resubmission, overlap, a retry after a
  network error) legitimately needs no replay.
- **Very short clips.** A 2-second clip with 3 seconds of UI overhead gives ratio 1.5 for zero work.
- **Clean, high-resource audio.** Studio-quality Hindi where Whisper is already correct needs a
  listen and a glance, not a listen and a rewrite.
- **Fast devices and fluent readers.** Reading speed varies severalfold between people.

---

### 🔴 Signal 2 — Anomalous deference *(Tier A: strongest available inference)*

**What it tells us.** Accept rate alone is confounded: a user with a 95% accept rate might
simply have been served easy clips. The fix is to compare a user against **peers who worked the
same audio**. If a clip was edited by 90% of the people who heard it, and this user accepted it
unchanged, the easy-batch explanation is gone. What remains is that they didn't listen.

This is the most defensible inference in the dataset because it is **peer-relative** — it
automatically normalises for clip difficulty, language, audio quality and Whisper's per-language
strength, all of which otherwise require separate correction.

**How to measure.**
```
clip_consensus_edit[url] = share of OTHER users who set is_edited=Yes on that url
ADR = share of the user's ACCEPTED tasks where clip_consensus_edit >= 0.70
```
Count only clips with ≥ 3 other workers, so consensus means something.

**Red-flag thresholds**

| Level | Condition |
|---|---|
| Monitor | `ADR > 0.30` over ≥ 15 qualifying clips |
| Investigate | `ADR > 0.50` over ≥ 20 qualifying clips |
| Strong | `ADR > 0.70` over ≥ 25 qualifying clips |

**When good transcribers show this innocently.**
- **They were right and the crowd was wrong.** A dialect specialist may correctly accept text
  that non-specialists "fixed" into error. This is a genuine and uncomfortable failure mode —
  consensus measures agreement, not truth, and a true expert in a crowd of novices looks like a
  deviant. Mitigate by weighting consensus by rater trust and by checking whether the user's
  *edits elsewhere* show expertise.
- **Guideline drift.** If the crowd edits punctuation because they believe guidelines require it
  and this user correctly doesn't, they'll look deferential while being right.
- **Thin overlap.** With 3 peers, "70% consensus" is 2 people. Require real volume.
- **Different task vintages.** Guidelines change over time; a clip worked in January under
  different instructions isn't comparable to one worked in July.

---

### 🟠 Signal 3 — Cosmetic-only editing *(Tier B: strong behavioural)*

**What it tells us.** Once transcribers learn that editing looks like work, the cheapest way to
appear productive is to add a full stop. `is_edited` flips to `Yes` and the task passes a naive
quality filter. This signal catches the specific response to a naive filter — which is why any
system built on `is_edited` alone will be gamed within weeks of launch.

It matters because **real Indic transcription corrections change words**: Whisper's actual errors
on Indian audio are wrong words, dropped words, code-mix failures, Hinglish-versus-Devanagari
script inconsistency, and mangled proper nouns. They are not missing commas.

**How to measure.**
```
strip(s)   = remove punctuation, collapse whitespace, lowercase
is_cosmetic = (whisper_text != user_text) and (strip(whisper_text) == strip(user_text))
cosmetic_share = share of the user's EDITED tasks that are cosmetic
median_norm_edit = median(edit_distance / len(whisper_text)) over edited tasks
```

**Red-flag thresholds**

| Level | Condition |
|---|---|
| Monitor | `cosmetic_share > 0.40` over ≥ 20 edited tasks |
| Investigate | `cosmetic_share > 0.60` **and** `median_norm_edit < 0.03` |
| Strong | `cosmetic_share > 0.75` over ≥ 30 edited tasks **and** low `listen_ratio` |

**When good transcribers show this innocently.**
- **The guidelines may actually ask for punctuation normalisation.** If so, this is *correct work*
  and the signal is inverted. **Check the live annotation guidelines before shipping this metric** —
  this is not a hypothetical; punctuation and casing conventions are common ASR dataset requirements.
- **Genuinely good Whisper output.** On clean, high-resource Hindi, punctuation may be the only
  thing left to fix.
- **Script/spelling normalisation** (ZWJ/ZWNJ, nukta forms, Unicode normalisation) can be
  semantically important yet look cosmetic to a naive string comparison. Normalise Unicode
  (NFC) before comparing, or this metric will mislabel careful work as lazy.

---

### 🟠 Signal 4 — Audio insensitivity *(Tier B: robust, threshold-free)*

**What it tells us.** A person actually doing the work takes longer on longer clips. Their time
*responds* to the audio. Someone clicking through at a fixed rhythm shows near-zero correlation
between clip length and time spent — they're working to a cadence, not to the content.

I like this signal because it is **robust to the absolute-threshold problem** that plagues
Signals 1 and 3. It doesn't care whether a user is fast or slow, only whether they are
*responsive*. That makes it far less sensitive to device class, language and literacy — the
exact confounders that make absolute-time thresholds unfair.

**How to measure.**
```
audio_sensitivity = Spearman rho(duration, time_taken_by_user) over the user's tasks
```
Require ≥ 50 tasks and a real spread in `duration` (e.g. IQR ≥ 3s) — correlation is undefined
in substance when every clip is the same length.

**Red-flag thresholds**

| Level | Condition |
|---|---|
| Monitor | `rho < 0.35` with n ≥ 50 and adequate duration spread |
| Investigate | `rho < 0.20` with n ≥ 50 |
| Strong | `rho < 0.10` with n ≥ 100 **and** low `median_listen_ratio` |

**When good transcribers show this innocently.**
- **Low duration variance in their assignments.** If the allocator gave them all 8-second clips,
  ρ is noise. This is the dominant false-positive route and must be gated on spread.
- **Difficulty dominates length.** A hard 5-second clip with heavy background noise can take
  longer than an easy 20-second one, which legitimately weakens the correlation.
- **Batching behaviour.** Someone who listens to three clips then types all three produces
  per-task times that don't track per-task duration, while doing the work properly.
- **Fixed overhead dominance.** If UI overhead is ~10s and clips run 5–15s, overhead compresses
  the observable relationship.

---

### 🟡 Signal 5 — Implausible typing throughput *(Tier C: supporting)*

**What it tells us.** If a user shows a large edit distance but had almost no time in which to
type it, the text wasn't typed. It was pasted, scripted, or copied from another field.

**How to measure.**
```
typing_window        = max(1, time_taken_by_user - duration)
effective_edit_rate  = edit_distance / typing_window      # chars/sec
```
Sustained human typing: roughly 1–2 chars/sec on an Indic phone keyboard, 3–5 chars/sec on
desktop with transliteration input. Restrict to tasks with `edit_distance ≥ 20` so tiny
denominators don't manufacture outliers.

**Red-flag thresholds**

| Level | Condition |
|---|---|
| Monitor | median `effective_edit_rate > 6` chars/sec over ≥ 20 qualifying tasks |
| Investigate | `> 8` chars/sec sustained, **and** `listen_ratio < 1.2` |
| Strong | `> 12` chars/sec sustained over ≥ 30 tasks |

**When good transcribers show this innocently.**
- **Legitimate copy-paste.** Repeated filler phrases, speaker labels, standard tags — pasting a
  recurring phrase is correct and efficient work.
- **Desktop power users** with Inscript or Google Input Tools training are genuinely fast.
- **Deletion.** Removing a long hallucinated Whisper run is a huge edit distance in one keystroke.
  **Edit distance should be decomposed into insertions versus deletions** before this metric is
  trusted at all.
- **Overlapping work** — if time is logged per task but a user prepared text while the previous
  clip played, the window is understated.

---

### 🟡 Signal 6 — Degenerate output *(Tier C: supporting, but sometimes dispositive)*

**What it tells us.** Two distinct behaviours, both visible in the text itself:
- **Templating** — submitting the same string across different clips.
- **Deletion-to-pass** — truncating Whisper's output so the task registers as edited and submits fast.

**How to measure.**
```
self_dup_rate   = share of submissions exactly duplicating the user's own text on a different url
median_len_ratio = median(len(user_text) / len(whisper_text))
empty_rate      = share of submissions with len(strip(user_text)) == 0
```

**Red-flag thresholds**

| Level | Condition |
|---|---|
| Monitor | `self_dup_rate > 0.10` across distinct urls |
| Investigate | `median_len_ratio < 0.50` over ≥ 30 tasks |
| Strong | `empty_rate > 0.05`, or `self_dup_rate > 0.25` on clips with distinct consensus text |

**When good transcribers show this innocently.**
- **Short clips genuinely repeat.** `हाँ जी`, `ठीक है`, `नहीं`, digits, names. In a corpus of
  2–4 second conversational chunks, high duplication is *expected*, not suspicious.
- **Prompt-based recording tasks.** If contributors read a scripted sentence, many speakers
  produce identical text and duplication is the correct answer. **Condition this metric on task
  type or it will fire hardest on exactly the cleanest data.**
- **Whisper hallucination.** Whisper is known to emit repeated or invented runs on silence and
  noise. Correctly deleting that rubbish produces a low `len_ratio` and looks like
  deletion-to-pass while being the single most valuable edit a transcriber can make.

---

## 3. The confounder that outranks all six

**A global threshold is not fair across this workforce, and unfairness here has a specific shape.**

Consider two honest transcribers:

| | Transcriber A | Transcriber B |
|---|---|---|
| Language | Hindi (high-resource; Whisper strong) | Bhojpuri (low-resource; Whisper weak) |
| Device | Laptop, broadband | ₹7,000 Android phone, 4G |
| Realistic `listen_ratio` | ~1.4× | ~3.0× |
| Realistic `accept_rate` | high — Whisper is often right | low — Whisper is often wrong |

A single global cutoff on either metric flags a different *population* rather than a different
*behaviour*. Worse, it flags them in a systematically biased direction: slower devices, weaker
Whisper coverage, less-represented languages — which is precisely the population Josh Jobs
exists to include, and precisely the data the dataset most needs.

**Therefore every threshold in this document must be expressed as a percentile within a
cohort**, where cohort = (language × device class × task type), not as an absolute constant.
"Bottom 5% of Bhojpuri-on-mobile workers" is a defensible comparison. "Below 1.3× listen ratio"
is not.

This is the single most important recommendation in Part I, and it is why Part II treats
cohort-relative scoring as a hard requirement rather than a refinement.

---

## 4. What I would verify before trusting any number above

The thresholds in this document are **structurally sound and numerically provisional**. They are
placed where behaviour becomes implausible in principle; they are not yet calibrated to the real
distribution, because I don't have the dataset. Before any of them drive an action:

1. **Plot every distribution first.** Per-cohort histograms of `listen_ratio`, `norm_edit`,
   `accept_rate`. Set thresholds at observed percentiles. A threshold chosen before seeing the
   data is a guess wearing a decimal point.
2. **Resolve the five platform questions** that can invalidate specific signals outright:
   - Is there a **playback-speed control**? *(breaks Signal 1)*
   - What exactly does the timer measure — start, pause-on-blur, idle behaviour? *(breaks Signal 1)*
   - Do the **guidelines require punctuation normalisation**? *(inverts Signal 3)*
   - Do **`recording_url`s overlap** across users? *(enables or kills Signal 2)*
   - Are any tasks **prompt-based/scripted** reads? *(breaks Signal 6)*
3. **Check `segment_character_per_second` against a recomputation** from `user_text` and
   `time_taken_by_user`. If the supplied column disagrees with the recomputation, the definition
   differs from the brief's and every derived metric inherits the discrepancy.
4. **Hand-audit before launch.** Take 200 flagged and 200 unflagged tasks to expert transcribers
   and get actual precision and recall. Until that exists, these are hypotheses.

`analysis/transcriber_quality.py` computes all of this — including the distribution plots and
the auto-calibrated percentile thresholds — the moment the CSV lands.

---

## 5. Summary

| # | Signal | Tier | Core metric | Can it justify a block? |
|---|---|---|---|---|
| 1 | Sub-realtime completion | 🔴 A | `sub_realtime_rate` | Only with verified timer semantics and no speed control |
| 2 | Anomalous deference | 🔴 A | `ADR` | Strongest statistical case; still needs human review |
| 3 | Cosmetic-only editing | 🟠 B | `cosmetic_share` | No — corroborating only |
| 4 | Audio insensitivity | 🟠 B | Spearman ρ | No — corroborating only |
| 5 | Implausible throughput | 🟡 C | `effective_edit_rate` | No |
| 6 | Degenerate output | 🟡 C | `self_dup_rate`, `len_ratio` | Only the empty-submission case |

**No row in that final column says "yes, on its own."** That is the finding, not a hedge — and
Part II is built around it.

→ **[Part II: the detection and enforcement system](02_PART_II_detection_system.md)**
