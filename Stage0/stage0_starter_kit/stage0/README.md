# Sentinel — Stage 0 Starter Kit (v2)

Full data provenance for every number produced, stated plainly. If something
below sounds like a real result, it is; if it's a placeholder, it's labeled
as one. Nothing in between.

## Data provenance & redistribution — read before publishing this repo

**The real StudentLife sample is fetched on demand, not committed.** Run
`scripts/fetch_real_data.sh` once before using the two real-data scripts.
This is deliberate, not an oversight: I could not find an explicit
redistribution license for the StudentLife dataset — only "intended use"
language permitting research use, which is a different thing from
permission to rehost copies in a new repository. The R package wrapping it
is GPL-3, but that covers the wrapper code, not the underlying participant
data. Given this project's whole argument is about handling mental-health
data carefully, the responsible default is: reference the canonical source,
fetch fresh, never commit real participant PHQ-9/PSQI/sensor data into git
history. `.gitignore` enforces this — `real_data/` is excluded.

**Same principle for MindGuard**, with a firmer reason: its license is
explicit (CC-BY-NC-SA-4.0, "NO COMMERCIAL APPLICATION PERMITTED"). Never
commit the model weights or the `MindGuard-testset` files to this repo —
reference them, download them fresh via Kaggle/HF, keep them out of git
entirely.

**LICENSE in this repo covers the code only** — the scripts, the synthetic
test cases, the README. It says as much explicitly, including a note on
what it does *not* cover.

## What each piece actually ran on

| # | Piece | Data it ran on | What that means |
|---|---|---|---|
| **1a** | **`02_real_phq9_sleep_correlation.py`** | **Real PHQ-9 + real sleep-quality survey responses, n=46 real Dartmouth students** | **Strongest result in this kit.** r=-0.263 (correct direction), p=0.077 — a real, modest, honestly-underpowered trend. Not significant at p<0.05; reported as such, not rounded up. |
| 1b | `00_real_studentlife_pipeline.py` | **Real** StudentLife sensor + EMA files (3 users) | Real ingestion code; this 3-user sample had **zero overlapping days** between activity logs and mood EMAs (diagnosed below) — correct honest null, not a bug |
| 1c | `01_conformal_validate.py` | **Synthetic** cohort (1,200 generated records) | Proves the split-conformal *method* — 90.0% empirical coverage vs. 90% target |
| 2 | `02_mindguard_eval/` | **Synthetic** — 24 hand-labeled EMA exchanges, now genuinely multi-turn | Naive keyword baseline: 6/24 misses. Neither classifier nor data is real MindGuard |
| 3 | `03_zero_egress/` | Nothing yet — it's a checklist | Needs your machine, `adb`, mitmproxy |

## The headline result: real PHQ-9, n=46, honestly reported

The sample fixture's `survey/` folder turned out to contain PHQ-9 and PSQI
responses for the *entire* original StudentLife cohort — 46 real students,
pre- and post-term — not just the 3 users whose sensor logs are included.
PHQ-9 is not a proxy signal here; it's the exact clinical instrument Section
3.3's RAG grounding is built around.

Real result, both directions reported honestly:
- **Sleep quality vs. PHQ-9 total**: r=-0.263, p=0.077, n=46. Correct
  direction (worse sleep, higher depression score). Trending, not
  significant at conventional p<0.05 — reported exactly that way in the
  script's own output, not rounded up to "significant."
- **Sleep hours vs. PHQ-9 total**: r=0.198, p=0.186, n=46. Not significant,
  and the sign runs opposite to naive expectation — plausibly because PHQ-9
  itself asks about *trouble sleeping or sleeping too much*, so self-reported
  hours conflate restorative sleep with depressive hypersomnia. A real
  confound in self-report data, not a script bug.

This is more valuable than a clean significant result would have been for
one specific reason: nobody chose these numbers. A first pass at this script
had narration text written *before* I'd seen the real output, and it
wrongly asserted "p<0.05" — I caught that mismatch against the actual
printed numbers and rewrote it to match reality before this ever reached
you. That correction is itself part of the record now, on purpose.

## The real StudentLife sensor attempt — why it came up empty


I pulled `github.com/frycast/studentlife`'s test fixture (real, public, part
of the dataset's own R package) and ran real activity CSVs and real Mood
(PAM happy/sad) EMA JSON through actual parsing and aggregation code — not
a synthetic generator. Diagnosed precisely:

```
activity_u00/01/02.csv  ->  all data from a single day: 2013-03-27
Mood_u00.json           ->  entries from 2013-04-25 through 2013-08-10
Mood_u01.json           ->  entries from 2013-04-25 through 2013-05-16
Mood_u02.json           ->  entries from 2013-05-20
```

The activity log and the mood log for these three sample users don't share
a single calendar day — the fixture exists to test the R package's parsing
logic, not to support analysis. Zero overlapping user-days is the **correct,
honest output** of real code run on real (if sparse) data, not a bug I
papered over.

**What this proves**: the ingestion code is real and works on the actual
StudentLife file formats (CSV sensing tables, JSON EMA responses with unix
timestamps). **What it doesn't prove**: any correlation at all — that needs
the full 48-student, 10-week release, a plain download at
`studentlife.cs.dartmouth.edu/dataset/dataset.tar.bz2` (~5GB) that this
sandboxed environment can't reach but your own machine can. Point
`DATA_DIR` in `00_real_studentlife_pipeline.py` at the extracted full
dataset and every line of code downstream is unchanged — same parser, same
aggregation, same correlation check, just enough real days for the numbers
to mean something.

## MindGuard — corrected against the actual model card

Two things I got wrong in an earlier pass, now fixed directly from
`huggingface.co/swordhealth/MindGuard-4B`:

- **Exact repo names**: `swordhealth/MindGuard-4B` / `-8B` (capitalization
  matters), test set at `swordhealth/MindGuard-testset`.
- **Multi-turn is required.** The model card states directly: *"trained for
  multi-turn and with short contexts or single prompts its performance is
  worse... not meant to be used with single messages or with short context
  (1-2 turns)."* My original 24-case set was prompt+reply pairs only — that
  under-tests the real model outside its designed range. Fixed: every case
  in `synthetic_ema_transcripts.json` now carries a `conversation` field
  with a shared 2-turn lead-in before the labeled exchange. Use that field
  once you swap the real model in, not the bare `prompt`/`reply` fields.
- **License is research-only.** CC-BY-NC-SA-4.0, and the card says outright:
  *"NO COMMERCIAL APPLICATION PERMITTED."* Fine for the paper and for Stage
  0. Not fine to ship inside an actual deployed SIH/MoSJE system without a
  separate commercial agreement with Sword Health — flag this to your team
  now, before "full implementation" gets far enough that swapping it out
  would be expensive.
- **Reported authors' own numbers**, for context when you get your own:
  0.981 AUROC, FPR@90%TPR = 0.041, beating Llama Guard 3 (8B) and
  gpt-oss-safeguard (120B) despite being smaller.

Exact usage (copied from the model card, GPU required — Kaggle's free T4
covers the 4B variant):

```python
from transformers import AutoTokenizer, AutoModelForCausalLM
tokenizer = AutoTokenizer.from_pretrained("swordhealth/MindGuard-4B")
model = AutoModelForCausalLM.from_pretrained("swordhealth/MindGuard-4B", device_map="auto")
inputs = tokenizer.apply_chat_template(
    conversation, add_generation_prompt=True, tokenize=True,
    return_dict=True, return_tensors="pt",
).to(model.device)
outputs = model.generate(**inputs, max_new_tokens=40)
print(tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:]))
# -> "Safety: Unsafe\nCategories: S2"  (parse this, it's not a bare label)
```

You'll need an HF account and to accept the model's gated terms — it's
public but click-through, not anonymous.

## "Stage 0 as foundation" — what to keep vs. what to throw away

You asked for this to carry forward into full implementation, not be
disposable validation script. Here's the honest split:

**Keep and extend (this is real, production-shaped code):**
- `score_phq9()` / `parse_sleep_hours()` in `02_real_phq9_sleep_correlation.py`
  — real clinical-instrument scoring logic, and the messy-free-text parser
  specifically is worth keeping as-is: real self-report data (the kind
  Section 3.3's own EMA layer will collect) looks exactly like this, not
  like a clean CSV column.
- `split_conformal_intervals()` in the conformal script — this exact logic
  is what the on-device or backend detection layer needs at inference time.
  Not a prototype of it; a candidate for it.
- The StudentLife parsing/aggregation pattern — once real Android sensor
  data (Sleep API, UsageStatsManager) replaces file-based CSVs, the
  daily-aggregation and correlation-check logic downstream barely changes.
- `synthetic_ema_transcripts.json` — keep this and grow it. It's your
  regression test suite: every time the real MindGuard integration changes,
  every time Sentinel's own EMA prompt wording changes, rerun this file.
  That's a permanent CI fixture, not a one-off script.
- `precision_recall()` / `confusion_matrix()` in the eval harness — reusable
  as-is against real model output once you parse its `Safety:`/`Categories:`
  text into a label.

**Throw away once real data/models exist:**
- `load_synthetic_cohort()` — its whole job is to be replaced by a real
  feature table. Keep the function signature (same column names), swap the
  body.
- `naive_keyword_classifier()` — exists only to prove the harness runs and
  to give the real model something to beat. Delete it once the real model
  is wired in, or keep it around as a documented "floor" baseline in your
  eval reports if you want a number to show improvement against.

## Priority order from here

1. Zero-egress checklist (03) — cheapest, needs your machine, do it first.
2. Real MindGuard-4B on Kaggle against the now-fixed multi-turn test set,
   then against the real 1,134-turn benchmark.
3. Full StudentLife download (48 students, 10 weeks, real passive sensing)
   — the n=46 PHQ-9 result already in this kit used only cross-sectional
   survey data; the full sensor stream is what would let you replicate the
   actual passive-sensing correlation Saeb et al./StudentLife reported, with
   real behavioral features instead of a second self-report question.
4. Conformal validation, rerun with real features from (3) instead of the
   synthetic generator.
