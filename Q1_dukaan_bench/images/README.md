# images/

Generated images go here, one subfolder per model:

```
images/
├─ gpt_image_1/
│  ├─ P01__gpt_image_1__run1.png
│  └─ ...
├─ gemini_2_5_flash_image/
└─ gemini_3_1_flash_image_preview/
```

**Naming is strict** — `<prompt_id>__<model_key>__run<N>.png`. The registration script
rejects anything that doesn't match, so a filename typo becomes a loud error rather than a
quietly mislabelled manifest row. A mislabelled image means the leaderboard credits the wrong
model, which is the worst failure an eval can have.

Created automatically by `generation/generate.py`, or by hand if you're using the web-UI
workflow. The rating tool asks you to point at this folder.

See [`../generation/MANUAL_WORKFLOW.md`](../generation/MANUAL_WORKFLOW.md).
