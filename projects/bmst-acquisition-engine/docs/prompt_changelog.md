# Prompt Changelog — BMST Acquisition Engine

Track every change to agent prompts. Include the reason and measurable outcome so future tuning has a baseline.

---

## Format

```
### YYYY-MM-DD — <prompt name>
**Change:** what was modified
**Reason:** why (data, observation, or hypothesis)
**Outcome:** measurable result after N conversations (fill in after 2–4 weeks live)
```

---

## Entries

### 2026-04-29 — Qualification Bot: all prompts (SYSTEM + Q1–Q4 + pass/fail/booking)
**Change:** Initial implementation of all 10 qualification bot prompts (PRD §12.4–12.14).  
**Reason:** Phase 5 baseline — no prior version.  
**Outcome:** Pending first live conversations.

---

### 2026-04-29 — Qualification Bot: QUALIFY_FAIL_PROMPT
**Change:** Added instruction to avoid the words "qualificação" and "score" in the message body.  
**Reason:** Early testing showed the bot was explaining the scoring system to leads, which felt mechanical and reduced trust.  
**Outcome:** Pending.

---

### 2026-05-01 — Content Engine: LINKEDIN_POST_PROMPT + INSTAGRAM_POST_PROMPT
**Change:** Initial implementation (PRD §12.17–12.18).  
Embedded the five `FORBIDDEN_PHRASES` directly in the prompt as negative examples.  
LinkedIn prompt requests `suggested_visual` alongside `linkedin_body` in a single LLM call to reduce latency.  
**Reason:** Phase 8 baseline — no prior version.  
**Outcome:** Pending first published posts.

---

### 2026-05-01 — Nurture Sequence: NURTURE_TOUCH_1/2/3 + REQUALIFY_PROMPT + REQUALIFY_REPLY_PROMPT
**Change:** Initial implementation (PRD §12.15–12.16 + inbound reply handler).  
Day-14 touch: content share, no CTA.  
Day-30 touch: references `main_challenge` from qualification conversation.  
Day-60 touch: new sector angle referencing `priority_process`.  
Day-75 touch: direct re-qualification offer.  
Reply handler: distinguishes positive (→ Q2) from negative/neutral (→ nurture) responses.  
**Reason:** Phase 9 baseline — no prior version.  
**Outcome:** Pending first full 75-day nurture cycle.

---

### 2026-05-01 — Qualification Bot: REQUALIFY_PROMPT — new_stage instruction
**Change:** Clarified that `new_stage` should be `"requalify"` (not `"Q2"`) in the outbound generation case. The transition to `"Q2"` is handled by `REQUALIFY_REPLY_PROMPT` when an inbound reply is received.  
**Reason:** Initial REQUALIFY_PROMPT instruction was ambiguous — said "new_stage = Q2 se responderem positivamente" in the context of the OUTBOUND message, which caused the graph to immediately set `conversation_stage = Q2` before any reply was received.  
**Outcome:** Fixed routing bug where nurture leads were skipping the re-qualification dialogue.

---

## Tuning Notes

When adjusting prompts, update this log **before** deploying to production. Include:
- The git commit SHA of the prompt change
- The number of conversations in the sample that motivated the change
- Any A/B test structure if running parallel versions

**Do not delete old entries** — the diff history shows how prompts evolved and why.
