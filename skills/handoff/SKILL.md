---
name: handoff
description: Preserve the real state of the work when pausing, changing direction, running low on context or passing to someone else. Writes a note; does not commit or switch sessions by itself.
---

# Handoff

1. Gather the state: `PLAN.md`, `BOARD.md`, `git status`, the relevant diff and the last few commits.
2. Write `HANDOFF.md` (or the location the project uses) with:
   - goal, scope, current slice, base commit
   - what is done and the evidence (commands, results, environment)
   - files in progress, whether they are saved, anything broken right now, user changes to leave alone
   - the very next action and the remaining list
   - exact commands to run and verify, ports or services that are running
   - key decisions and why, known problems, excluded scope, repeated failures
   - open review findings and their status
3. Record unverified or failing changes as exactly that. Do not stage or commit anything just to make the handoff look clean.
4. Re-read the note against the real repository: paths, hashes and commands must match.
5. Give the next person a one-line starting instruction, for example:
   "Read README, PLAN.md, BOARD.md and HANDOFF.md, check git status and the recorded environment, then continue from the next action."

Done when someone with no context could resume from the note alone. Writing the note is not the same as the next person accepting it.
