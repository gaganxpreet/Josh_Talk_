# evidence/

Provenance and proof. The brief requires that every submitted image can be traced to an exact
company, model, prompt, surface and set of settings — this folder is that record.

```
evidence/
├─ manifest.csv       one row per image: company, model_name, api_model_id, exact prompt,
│                     generation_surface, settings_json, sha256, bytes, timestamp,
│                     deviation_notes. Written by generate.py (API or manual path).
├─ raw/               raw API response metadata, one JSON per image. Includes OpenAI's
│                     revised_prompt where returned — i.e. evidence of whether the model
│                     silently rewrote our prompt.
├─ screenshots/       proof of generation. Per model, at minimum:
│                       <model_key>__model_selector.png
│                       <model_key>__P01_generation.png
│                       <model_key>__settings.png
└─ consent/           signed consent forms + participants.csv
```

## consent/ — handle with care

`participants.csv` is the **only** file in this repository that should contain participant
names and email addresses. Everywhere else uses participant IDs (`R01`…`R10`).

The brief requires you to share these details; it does not require you to scatter them across
every spreadsheet. Keeping them in one file means you can honour a withdrawal request by
editing one row.

Required columns:

```
participant_id, name, email, age, city_state, scripts_read,
small_business_experience, consent_given, consent_statement,
started_at, completed_at
```

The rating tool exports a matching `participant_<ID>.csv` per session; concatenate those.

**Consent must be signed before the participant sees any image.** Not after, not alongside.
