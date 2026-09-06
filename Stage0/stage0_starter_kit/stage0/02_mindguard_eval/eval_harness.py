"""
Stage 0 — Turn-Level Classifier Evaluation Harness
=====================================================
Gate this satisfies (Stage table, row 0): "validate the MindGuard integration
... against representative synthetic EMA transcripts before any live use" and
"MindGuard turn-classification precision/recall on EMA-style text meets a
pre-registered threshold."

VERIFIED DIRECTLY FROM THE MODEL CARD (huggingface.co/swordhealth/MindGuard-4B)
-- this replaces guessed repo names from an earlier pass:

  Models: swordhealth/MindGuard-4B, swordhealth/MindGuard-8B (exact case matters)
  Test set: swordhealth/MindGuard-testset (1,134 clinician-annotated turns,
            67 conversations, 94.4% inter-annotator agreement)
  Reported performance: 0.981 AUROC, FPR@90%TPR = 0.041 -- beats Llama Guard 3
  (8B) and gpt-oss-safeguard (120B) despite being smaller.

TWO THINGS THAT CHANGE HOW YOU USE THIS, BOTH FROM THE MODEL CARD DIRECTLY:

1. MULTI-TURN IS REQUIRED, NOT OPTIONAL. Quote: "the model is trained for
   multi-turn and with short contexts or single prompts its performance is
   worse... not meant to be used with single messages or with short context
   (1-2 turns)." synthetic_ema_transcripts.json has been updated to include
   a 'conversation' field (shared 2-turn lead-in + the labeled exchange) for
   exactly this reason -- use that field, not the bare prompt/reply pair,
   once you swap in the real model.

2. LICENSE IS RESEARCH-ONLY. CC-BY-NC-SA-4.0, and the model card is explicit:
   "NO COMMERCIAL APPLICATION PERMITTED." That's fine for the paper and for
   Stage 0 validation. It is NOT fine to ship inside an actual SIH prototype
   or any real MoSJE deployment without a separate commercial license from
   Sword Health -- that's a real constraint on "full implementation," not a
   Stage-0-only detail, and worth resolving (or explicitly scoping around)
   before you build production code around it.

Actual usage, copied from the model card (adapt for the eval loop below):

    from transformers import AutoTokenizer, AutoModelForCausalLM
    tokenizer = AutoTokenizer.from_pretrained("swordhealth/MindGuard-4B")
    model = AutoModelForCausalLM.from_pretrained("swordhealth/MindGuard-4B", device_map="auto")
    inputs = tokenizer.apply_chat_template(
        conversation,  # list of {"role": ..., "content": ...} dicts
        add_generation_prompt=True, tokenize=True,
        return_dict=True, return_tensors="pt",
    ).to(model.device)
    outputs = model.generate(**inputs, max_new_tokens=40)
    text = tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:])
    # Output looks like: "Safety: Unsafe\nCategories: S2" -- parse this,
    # don't assume a clean label string comes back directly.

Requires an HF account + accepting the model's terms (gated, not anonymous
download) and a GPU -- Kaggle's free T4 tier is enough for the 4B variant.

TWO THINGS TO RUN, IN ORDER:

1. THIS SCRIPT, right now, with the naive keyword baseline below. It's
   deliberately crude -- it exists to (a) prove the harness itself works
   end-to-end, and (b) give you a real number to beat, not a fake one.

2. THE REAL THING, on Kaggle with internet + GPU enabled, using the exact
   usage pattern above. Also run this same harness against the real
   swordhealth/MindGuard-testset (1,134 turns) by writing a loader that maps
   its schema onto the {conversation, label} shape used below -- that
   directly replicates the authors' own reported numbers on your own
   infrastructure, which is a much stronger Stage 0 claim than the 24-case
   synthetic set alone.

Run: python3 eval_harness.py
"""

import json
import re
from collections import Counter

LABELS = ["safe", "self_harm", "harm_to_others"]


# ---------------------------------------------------------------------------
# NAIVE BASELINE -- replace this function's body with a real MindGuard call.
# Keep the same input/output contract: str, str -> one of LABELS.
# ---------------------------------------------------------------------------
SELF_HARM_TERMS = [
    "kill myself", "end it", "end things", "ending things", "want it all to end",
    "hurt myself", "hurting myself", "cutting", "suicide", "suicidal",
    "don't want to be here", "better off without me", "no point", "painkillers",
    "bridge", "saving up my medication",
]
HARM_OTHER_TERMS = [
    "kill him", "kill her", "hurt him", "hurt her", "make him pay", "make her pay",
    "regret it", "his spare key", "his car",
]


def naive_keyword_classifier(prompt: str, reply: str) -> str:
    text = reply.lower()
    if any(t in text for t in HARM_OTHER_TERMS):
        return "harm_to_others"
    if any(t in text for t in SELF_HARM_TERMS):
        return "self_harm"
    return "safe"


# ---------------------------------------------------------------------------
def load_cases(path="synthetic_ema_transcripts.json"):
    with open(path) as f:
        data = json.load(f)
    return data["cases"]


def evaluate(cases, classify_fn):
    y_true, y_pred = [], []
    misses = []
    for c in cases:
        pred = classify_fn(c["prompt"], c["reply"])
        y_true.append(c["label"])
        y_pred.append(pred)
        if pred != c["label"]:
            misses.append((c["id"], c["label"], pred, c["reply"], c.get("note", "")))
    return y_true, y_pred, misses


def confusion_matrix(y_true, y_pred, labels):
    idx = {l: i for i, l in enumerate(labels)}
    m = [[0] * len(labels) for _ in labels]
    for t, p in zip(y_true, y_pred):
        m[idx[t]][idx[p]] += 1
    return m


def precision_recall(y_true, y_pred, labels):
    out = {}
    for l in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == l and p == l)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != l and p == l)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == l and p != l)
        prec = tp / (tp + fp) if (tp + fp) else float("nan")
        rec = tp / (tp + fn) if (tp + fn) else float("nan")
        out[l] = (prec, rec, tp, fp, fn)
    return out


def main():
    cases = load_cases()
    y_true, y_pred, misses = evaluate(cases, naive_keyword_classifier)

    print("=" * 66)
    print("STAGE 0 — TURN-LEVEL CLASSIFIER EVAL (naive keyword baseline)")
    print("=" * 66)
    print(f"Cases: {len(cases)}   Label distribution: {dict(Counter(c['label'] for c in cases))}")
    print()

    pr = precision_recall(y_true, y_pred, LABELS)
    print(f"{'label':<16}{'precision':<12}{'recall':<10}{'tp/fp/fn'}")
    for l in LABELS:
        p, r, tp, fp, fn = pr[l]
        p_s = f"{p:.2f}" if p == p else "n/a"
        r_s = f"{r:.2f}" if r == r else "n/a"
        print(f"{l:<16}{p_s:<12}{r_s:<10}{tp}/{fp}/{fn}")

    print()
    cm = confusion_matrix(y_true, y_pred, LABELS)
    print("Confusion matrix (rows=true, cols=predicted):")
    print(" " * 17 + "".join(f"{l:>15}" for l in LABELS))
    for l, row in zip(LABELS, cm):
        print(f"{l:<17}" + "".join(f"{v:>15}" for v in row))

    print(f"\nMisclassified: {len(misses)} / {len(cases)}")
    for cid, true, pred, reply, note in misses:
        print(f"  #{cid}: true={true} pred={pred}  \"{reply[:60]}...\"")
        if note:
            print(f"        -> {note}")

    print()
    print("EXPECTED RESULT: the misses above should cluster almost entirely on")
    print("cases 3, 4, 5, 12, 20, 22 -- the metaphor/history/hyperbole/direction-")
    print("of-threat traps. If it also misses the genuine risk cases (6-11, 17,")
    print("21, 23), that's a bigger problem worth looking at before you even get")
    print("to the real model, since those are the ones a keyword list should")
    print("catch by construction.")
    print("=" * 66)


if __name__ == "__main__":
    main()
