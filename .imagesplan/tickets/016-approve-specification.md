---
id: D11
title: "Approve the specification"
type: grilling
mode: HITL
status: closed
claimed_by: erral
blocked_by: [R1, R2, R3, R4, T1, D1, D2, D3, D4, D5, D6, D7, D8, D9, D10]
---

## Question

Synthesize the closed decisions into `.imagesplan/SPEC.md` and
`.imagesplan/TEST-PLAN.md`, resolve any inconsistencies, and obtain explicit
human approval before implementation tickets are created or started.

Steps:

1. Read `MAP.md` and every closed ticket.
2. Draft `SPEC.md`: goal, non-goals, public API, registration, the
   metadata/fallback contract, security, compatibility, and docs/release.
3. Draft `TEST-PLAN.md` from the test-plan decision.
4. Present both to the user, in a live exchange, and iterate.
5. Record approval in `## Resolution` and mark this ticket closed.

Do not write implementation code in this ticket.

## Draft

- `SPEC.md` drafted from all closed decisions and the research findings.
- `TEST-PLAN.md` reviewed against the specification; it remains the test
  artifact referenced by the spec.
- Awaiting explicit human approval before implementation tickets are created.

## Resolution

Approved by the user on 2026-10-17.

- `.imagesplan/SPEC.md` is the approved contract.
- `.imagesplan/TEST-PLAN.md` is the approved verification plan.
- The implementation slices were graduated from the map fog into tickets
  I1-I10, with blocking edges matching the spec's implementation outline.
- No implementation code was written in this ticket.

Implementation may now start. Each implementation ticket is AFK and must leave
the full suite green; no GitHub writes, no version bump, no release.
