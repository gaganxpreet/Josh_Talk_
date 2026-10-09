# Video walkthrough — script (2:00 max)

Hard ceiling is 2 minutes, and the brief asks for three things: **what eval you chose, what you
found, why it matters.** Below is a 115-second script with ~5 seconds of headroom.

**Record this in one take with the dashboard already open.** Don't screen-share your file
explorer, don't walk through the repo. Reviewers watching ten of these will remember one sharp
idea, not a tour.

---

## Timed script

### 0:00 – 0:18 · The use case (talking head or a single slide)

> "A kirana store owner in Kanpur wants a Diwali offer poster for her WhatsApp Status. She types
> one prompt. She's not a designer, and she is not going to open Canva to fix the text.
>
> So I built **Dukaan Bench** — can a frontier image model actually serve that moment?"

*On screen: one slide, the sentence "One prompt. One poster. No editing."*

### 0:18 – 0:40 · What's being measured

> "Three models — OpenAI's GPT Image 1, and Google's Gemini 2.5 and 3.1 Flash Image.
> Ten prompts, six Indic scripts, every model gets the identical prompt and I keep the **first**
> output, not the best one — because that's what she gets.
>
> The headline metric is the **Usable Poster Rate**: would you post this, as-is, right now?
> Binary, because the real decision is binary. A poster with one wrong Devanagari character
> isn't ninety per cent useful. It's unusable — it makes her shop look careless."

*On screen: the prompt grid, then a triad of three generated posters side by side.*

### 0:40 – 1:00 · The one design idea to remember

> "The most important prompt in the set is the tenth one. It's the **same poster in English**.
>
> That gap — I call it the **Indic Text Penalty** — is what separates 'this model can't render
> text' from 'this model can't render *this* text.' Same bad score, two completely different
> fixes: one's your text renderer, the other's your Indic training data. Without that control
> you've got a complaint instead of a diagnosis."

*On screen: the ITP dumbbell chart. Let it sit — this is the idea worth remembering.*

### 1:00 – 1:30 · Findings

> "`[STATE YOUR ACTUAL TOP THREE FINDINGS HERE — see the fill-in guide below]`"

*On screen: leaderboard, then the per-script heatmap.*

### 1:30 – 1:52 · Why it matters

> "Two reasons this matters.
>
> For a lab, it turns 'does our model work for India?' — which is unanswerable and therefore
> unfundable — into a number you can watch across training runs, for under ten dollars a run.
> And the per-script breakdown tells you *which* script to spend your next annotation budget on.
>
> For the product: **one global leaderboard is the wrong product for India.** Filter by script
> and the ranking changes. A single 'best image model' badge actively misinforms a shop owner in
> Chennai. The per-script view is the product; the global average is marketing."

*On screen: click the script filter live and let the leaderboard visibly re-rank. This is the
single most persuasive five seconds in the video — make sure it works before you record.*

### 1:52 – 2:00 · Close

> "And the panel this needs — script-qualified raters at scale — is the one thing Josh Jobs
> already has. Twenty thousand people a day, twenty-five languages. That's the moat; the
> leaderboard's just the visible end of it."

---

## Fill-in guide for 1:00–1:30

Once you have real numbers, pick **three** findings using this priority order, highest first:

1. **A failure all three models share.** Category-level findings beat rankings — "none of them
   can do Tamil conjuncts" is more useful to a lab than "model B is 4% better."
2. **The NoneRate**, if it's high. "In X% of cases my raters said none of the three was good
   enough to post" is the most quotable sentence available and costs you nothing to say.
3. **A ranking flip between the global and per-script views.** This proves the product thesis
   live rather than asserting it.

Say the number, then say the consequence. One sentence each.

**If the results are boring** — all three models roughly equal, no clear winner — say that
plainly. "Nobody's solved this yet" is a real finding and it is the honest one. Do not inflate
a null result into a ranking; a reviewer evaluating judgment will notice, and it's the cheapest
possible way to lose their trust.

---

## Recording notes

- **Do** have the dashboard open and interact with it live. The filter re-rank is your best moment.
- **Do** say the actual model names once, clearly — the brief asks for exact company and model names.
- **Don't** read the main document aloud. Different artefact, different job.
- **Don't** apologise for sample size on camera. State it once as a limit if it comes up naturally;
  the written limitations section covers it properly.
- **Don't** run over 2:00. A reviewer who stops the video at the cap misses your close.
- Record at 1080p, use a headset mic, and do one practice run for timing — the 1:00–1:30 block
  is where people overrun.
