# Sentinel — Additions for V4

This document specifies the new architectural content to add to the paper, organized by the section each item belongs in. It captures the design decisions reached through discussion since V3, with the reasoning each one rests on, so it can be drafted into prose directly. A short list of smaller items still outstanding from the V3 review is included at the end for completeness.

---

## 1. Tier 3 Message-Delivery Mechanism (Section 3.6, expanding the existing Table 1 row)

This is not a new escalation tier. Table 1 already names the mechanism — *"optionally, with prior consent, an encrypted context message to a pre-designated contact"* — this section specifies how that mechanism actually works.

**Generation: pre-authored, not live.** No message is composed by Gemma at trigger time. A small, fixed library of templates (2–3 per trigger category) is authored offline and reviewed with the same clinician-input process already applied to the PHQ-9/GAD-7 lexicon in Section 3.3. At trigger time, the system performs two operations only: (1) selects the template matching the signal that fired, and (2) fills a small set of variables — contact's saved name for the user, a coarse tier/category label, the Tele MANAS number. No free text is generated in the moment.

*Rationale to state explicitly:* this extends a principle the paper already applies everywhere else — constrain generation to pre-vetted content wherever the cost of an error is high — to the one channel that didn't yet have it. It also means this channel requires no new live safety layer to design or validate; the safety work happens once, at authoring time, the same way it does for the CBT-nudge lexicon.

**Two template sets, not one.** Self-harm and harm-to-others triggers need separate templates — tone and content that are appropriate for a friend supporting someone in crisis are not appropriate, and may be actively wrong, for a credible-threat-to-a-third-party disclosure.

**Content structure.** Each template contains: (a) the tier/category, not a verbatim transcript or a generated narrative of "the situation"; (b) a direct instruction for the contact to act; (c) a resource for the *contact*, not only the user — Tele MANAS and comparable lines are equipped to take calls from a worried third party, not only from the person at risk. Content should be grounded explicitly in the QPR (Question–Persuade–Refer) gatekeeper-training model — the standard evidence-based framework for what an untrained layperson should do, which itself terminates at *refer* rather than asking the bystander to improvise an intervention. **A citation is needed here** — source a primary or peer-reviewed reference for QPR's evidence base before submission (the same verification standard already applied to other flagged citations in the paper), not a training-provider marketing page.

**Delivery channel.** Text by default. If a call path is included, it is a one-tap call action inside the text — the same pattern Table 1 already uses for Tele MANAS at Tier 2 ("one-tap connection") — so a human places the call, not Sentinel. An autonomous outbound call is not recommended: reliability is uncertain (missed/unanswered calls need a defined fallback), and a synthesized voice describing a mental health crisis is difficult to distinguish from unwanted robocall traffic.

**No retry/escalation-on-no-response logic.** Tele MANAS surfacing to the user already fires immediately and unconditionally at Tier 3, independent of what happens on the friend channel — the friend contact is additive, not a single point of failure, so it doesn't need its own escalation ladder. Adding automatic escalation if the contact doesn't respond would reintroduce the automated-dispatch pattern Section 3.5 already excludes on principle.

**Setup-time preview requirement.** Before a user confirms a Tier 3 contact, they see the literal message text that would be sent. This is what operationalizes the consent-specificity commitment already made in Section 5.5 — "I agree to have my friend contacted" and "I agree to this exact message" are different levels of consent, and only the second is currently satisfied by the design.

---

## 2. Friend-Contact Positioning (Section 2.1 / 3.6 framing)

State explicitly that the friend-contact channel operates **alongside** Tele MANAS, not as a substitute or superior alternative — this should be stated as a design principle, not left implicit.

*Rationale to cite:* QPR's own materials describe trained-layperson gatekeeper response as "a citizen emergency response to a mental health crisis," explicitly distinguished from treatment. Relational closeness provides immediacy and warmth a national helpline cannot; it does not substitute for crisis-specific training. Avoid any framing suggesting the friend channel outperforms or replaces Tele MANAS — it should be positioned as complementary throughout.

---

## 3. Harm-to-Others: Sharpening the Already-Flagged Open Question (Sections 3.6 and 5.2)

Two additions to the existing open-question treatment, which currently asks only "is Tele MANAS the right channel":

- **Name the deeper question directly:** even granting Tele MANAS is the correct channel, what obligation or action does a duty-to-protect disclosure create for a counsellor who has not spoken with the user, regarding a threatened third party they cannot identify or contact? Routing resolves which phone number receives the alert; it does not resolve what that recipient is positioned to do with it.
- **Name a new privacy gap:** a harm-to-others classification necessarily involves information about a person who never enrolled in Sentinel. Section 5.1's zero-knowledge framing is currently scoped entirely to the user's own data. This should be named as open — consistent with how the paper already handles the routing question — rather than left unaddressed by omission.

---

## 4. Financial and Peer-Pressure Signal (Sections 3.2 / 3.6)

- Captured only as explicit, user-typed statements within Sentinel's own first-party text surfaces — the same surfaces Section 3.2 already scopes keystroke-dynamics capture to. This must be stated as explicitly as the IME/AccessibilityService exclusion already is in 3.2, so the scope cannot be read as ambient, system-wide keyboard capture.
- Surfaces to the Tier 2/3 human reviewer as supplementary context only. Does not enter the Phase 2 automated ensemble or the RAG-grounded generation pipeline.
- *Rationale:* no validated clinical instrument exists for these constructs (unlike PHQ-9/GAD-7), so keeping them out of automated pathways preserves the RAG-groundedness discipline the generation-safety argument in Section 2.4/3.3 depends on.

---

## 5. Academic Records (Section 3.2)

- Captured only via voluntary, user-initiated upload (grades, marks, achievements) — not institutional-system integration. This is what keeps the feature consistent with the "user is the sole party with access to their own data" claim that differentiates Sentinel from Beiwe/mindLAMP in Section 2.1.
- Treated the same as the financial/peer-pressure signal: human-facing context at Tier 2/3 only, not an input to the automated ensemble or generation layer at this stage.
- Worth noting explicitly: academic performance has more established published correlation with mental health outcomes than peer or financial pressure does, but still falls well short of PHQ-9/GAD-7's clinical specificity. Name it as a Stage 0 validation target for future work rather than treating the upload mechanism alone as sufficient grounding for automated use.

---

## Also still outstanding (from the V3 review, not addressed since)

| Item | Where |
|---|---|
| ProMind-LLM not yet cited — it is MindGuard's own direct successor, same lab, and its absence is conspicuous given how thoroughly MindGuard is treated | Section 2.1 |
| "Five-stage pipeline" prose numbering bundles three distinct processes (detection, generation, turn-classification) into one stage, inconsistent with Figure 1's separate boxes | Section 3.1 |
| ProKnow's "96% reduction" is glossed as a "knowledge-capture-violation metric" rather than the source's actual term (averaged squared rank error) | Section 2.4 |
| Confirm Table 1 and the Stage table render as actual tables in the final PDF, not run-together prose | Section 3.5 / 4.3 |
