# responses/

Real participant ratings go here, one CSV per rater, exported by `rater_tool.html`:

```
responses/
├─ ratings_R01.csv
├─ ratings_R02.csv
└─ ...
```

Then:

```bash
python ../analysis/analyze.py --ratings . --gt ../analysis/tf_ground_truth.csv
```

---

**Do not mix synthetic data in here.** `analysis/make_synthetic_ratings.py` writes to
`responses_synthetic/` precisely so the two can never be confused. Delete that folder before
you submit.
