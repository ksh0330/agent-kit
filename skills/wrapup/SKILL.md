---
name: wrapup
description: Close out a task or session - run verify, reconcile docs with behaviour, record lessons, and give the user an honest final summary.
---

# Wrap up

1. Prefer fixing remaining defects in required criteria over adding features.
2. Run `verify`. Follow the README from a clean start and confirm the main run and test commands still work.
3. Compare every claim in the docs with the code and tests. Fix or remove claims that are not true.
4. Do not delete files you did not create. Do not hide failing checks or create a "ready" commit over them.
5. Commit only verified, owned files. Run `python -m agentkit guard scan` before any push to confirm the history is clean.
6. Update `BOARD.md` to its final state and add durable lessons to `LEARNING.md`: what happened, why, and the rule to follow next time.
7. Write `HANDOFF.md` if anyone will continue the work.
8. Final summary for the user, short:
   - what was delivered and where (paths, commits)
   - what was verified and how; what was not
   - known limitations and risks
   - decisions made on their behalf and the reasoning
   - anything that still needs the user (review, push, release)

Done when the user can see what is true, what is not yet proven, and what they need to do next. Publishing or pushing stays with the user unless they said otherwise.
