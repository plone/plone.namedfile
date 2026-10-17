# Local wayfinder tracker

This directory is the issue tracker for the brain-aware `@@images` effort. It is
deliberately outside `docs/` so the plan does not mix with package documentation.

## Layout

- `MAP.md` — the map: destination, notes, closed-ticket index, fog, out of scope.
- `tickets/NNN-<slug>.md` — one ticket per decision, question, or prerequisite.
- `research/<ID>-<slug>.md` — findings produced by research tickets.
- `frontier.py` — prints the current frontier from ticket frontmatter.
- `SPEC.md` — written and approved by the specification ticket.
- `TEST-PLAN.md` — written by the test-plan ticket.

## Ticket frontmatter

```yaml
---
id: D1
title: "Short searchable title"
type: grilling        # research | prototype | grilling | task
mode: HITL            # HITL | AFK
status: open          # open | closed
claimed_by: null      # the session/agent that claimed it
blocked_by: []        # ticket ids that must be closed first
---
```

A ticket is **claimable** when it is `open`, `claimed_by` is null, and every id in
`blocked_by` is `closed`. Claim it by setting `claimed_by` before doing any work.
Close it by setting `status: closed` and appending a `## Resolution` section.

## Commands

```sh
python .imagesplan/frontier.py            # open, unclaimed, unblocked tickets
python .imagesplan/frontier.py --all      # every ticket with status and claim
python .imagesplan/frontier.py --research # open research tickets
```

## Rules

- Never write to GitHub. No issues, comments, PRs, pushes, or releases without an
  explicit order from the user.
- Decisions are recorded in the ticket, not in the map. The map only gists closed
  tickets and links to them.
- Research tickets may be resolved in parallel. Do not resolve more than one
  non-research ticket per session.
- Refer to a ticket by its title in narration, never by a bare id.
