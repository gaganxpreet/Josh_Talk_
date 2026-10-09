# Manual generation workflow (no API keys needed)

The eval is designed so that **every image can be produced by hand in a browser** and still
end up with the same provenance record an API run would produce. Use this if you don't have
API access, or mix it freely with the API path — `generate.py --status` tracks coverage
across both.

---

## The contract

Whatever you do, you must end with:

| Requirement (from the brief) | Where it lives |
|---|---|
| exact company name | `manifest.csv` → `company` |
| exact model name | `manifest.csv` → `model_name` |
| exact prompt | `manifest.csv` → `prompt_text` |
| where you generated it | `manifest.csv` → `generation_surface` |
| settings / variations | `manifest.csv` → `settings_json`, `deviation_notes` |
| proof of generation | `evidence/screenshots/` |

---

## File naming — get this right, everything downstream depends on it

```
Q1_dukaan_bench/images/<model_key>/<prompt_id>__<model_key>__run<N>.png
```

Example:

```
images/gpt_image_1/P01__gpt_image_1__run1.png
images/gemini_2_5_flash_image/P01__gemini_2_5_flash_image__run1.png
images/gemini_3_1_flash_image_preview/P01__gemini_3_1_flash_image_preview__run1.png
```

The three `model_key` values are exactly:

- `gpt_image_1`
- `gemini_2_5_flash_image`
- `gemini_3_1_flash_image_preview`

`--register-manual` refuses to register anything that doesn't match the pattern, so a typo
becomes a loud error rather than a quietly mislabelled row. That matters: a mislabelled
image means the leaderboard credits the wrong model, which is the single worst failure an
eval can have.

---

## Step 1 — copy the prompt *exactly*

Open `prompts/prompt_set_v1.json` and copy the `full_prompt` field. Do not retype it.

> **Devanagari, Tamil, Bengali, Gurmukhi, Telugu and Urdu text does not survive retyping.**
> Copy-paste only. If you retype and get a different Unicode sequence, you are no longer
> testing the same prompt across models and the comparison is void.

Sanity check before you paste: the quoted target text in the prompt box should look
identical to the `target_text` field. If your browser renders it as boxes (`□□□`), you're
missing a font — the *prompt* is still fine, but install Noto Sans for that script before
you try to *judge* the output.

## Step 2 — generate, one model at a time

### OpenAI — GPT Image 1
1. Go to **chatgpt.com**
2. Paste the prompt. Nothing else in the message — no "please", no follow-up instructions.
3. If it asks a clarifying question, **do not answer it conversationally**. Start a new chat
   and paste again. A clarifying exchange changes the effective prompt and breaks fairness.
4. Download the image at full resolution.
5. Record which surface produced it. ChatGPT's image pipeline and the `gpt-image-1` API are
   not guaranteed to be identical builds — note `ChatGPT web UI` in `generation_surface`
   and flag it in `deviation_notes`.

### Google — Gemini 2.5 Flash Image
1. Go to **aistudio.google.com**
2. Select model `gemini-2.5-flash-image`.
3. Set aspect ratio to portrait (3:4) if the control is available. If not, leave default and
   **write that in `deviation_notes`**.
4. Paste the prompt. Generate. Download.

### Google — Gemini 3.1 Flash Image Preview
1. Same as above, model `gemini-3.1-flash-image-preview`.
2. Preview models change without notice. Screenshot the model selector showing the exact
   model string — this is your proof you used the preview model and not the stable one.

## Step 3 — screenshot as you go

For **each model**, capture at minimum:

- `evidence/screenshots/<model_key>__model_selector.png` — the UI showing the exact model name
- `evidence/screenshots/<model_key>__P01_generation.png` — one full generation in context,
  showing the prompt box and the resulting image together
- `evidence/screenshots/<model_key>__settings.png` — any aspect-ratio / quality controls

You don't need 30 screenshots. You need enough that a reviewer can verify you used the
models you claim, with the prompts you claim.

## Step 4 — register

```bash
python generate.py --register-manual
```

This hashes every file, writes `evidence/manifest.csv`, and prints the coverage grid.

## Step 5 — fill in what the script cannot know

`--register-manual` writes a placeholder in `settings_json` because it has no way to see
your browser. Open `evidence/manifest.csv` and replace it, e.g.:

```json
{"surface":"Google AI Studio","aspect_ratio":"3:4","temperature":"default","date":"2026-07-14"}
```

Then re-run `python generate.py --status` to confirm nothing is outstanding.

---

## Handling the awkward cases honestly

These will happen. The brief explicitly asks you to document them, and documenting them is
worth more than a clean-looking run that hides them.

**A model refuses the prompt.**
Record the refusal text in `deviation_notes`, leave `output_path` empty, set `error`. A
refusal is a *result* — "this model won't generate Eid imagery" would be a significant
India-relevant finding. Do not quietly swap in a reworded prompt.

**A model returns a cropped or square image when you asked for portrait.**
Keep it. Record the actual aspect in `deviation_notes`. Do not re-roll to get a nicer one —
that is cherry-picking, and it biases the whole eval toward whichever model you were most
patient with.

**You accidentally generated twice.**
Keep the **first** generation and discard the rest, unless you are deliberately running the
variance sub-study. Write down that you did this. The rule is *first output, not best
output*, because the shop owner in the use case gets the first output too.

**The web UI silently rewrites your prompt.**
ChatGPT in particular may expand prompts. If you can see a revised prompt, save it to
`evidence/raw/<image_id>.json`. If you can't see it, note in `deviation_notes` that prompt
rewriting may have occurred on this surface and could not be verified. That caveat belongs
in the limitations section of the main document.

---

## Cost estimate (API path)

| Model | Images | Rough cost |
|---|---|---|
| GPT Image 1 (1024×1536, high) | 10 | ~$1.5–2.5 |
| Gemini 2.5 Flash Image | 10 | ~$0.3–0.5 |
| Gemini 3.1 Flash Image Preview | 10 | ~$0.3–0.5 |
| Variance sub-study (+12) | 12 | ~$1 |

Total well under $10 for the full primary run. Check current pricing before you run —
these are order-of-magnitude figures, not quotes.
