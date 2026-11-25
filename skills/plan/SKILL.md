---
name: plan
description: Turn a new or unclear request into a short written plan with observable acceptance criteria and small slices. Skip it for an obvious one-line fix.
---

# Plan

1. Read what already exists before proposing anything: the request, README, entry points, `git status` and recent commits. Do not crawl the whole tree.
2. Separate three lists: confirmed facts, unverified assumptions, and candidate approaches. Never promote an assumption to a fact without evidence.
3. Ask the user only about ambiguities that change the outcome. If the request is clear and the decision was delegated, write down the reasoning and move on.
4. Write `PLAN.md` (template in `templates/PLAN.md`):
   - goal in one sentence, in scope / out of scope
   - acceptance criteria that someone else could check by running a command or following an example input and expected output
   - slices: each one is a single end-to-end flow that can be built and verified on its own
   - risks and open questions, each with who or what can resolve it
5. For a consequential choice, list two or three alternatives, the recommended one, why, and what would make you switch. Record the user's actual answer; silence is not agreement.
6. Update `BOARD.md` with the current slice and next action.

Done when every acceptance criterion names how it will be verified and the first slice is ready to build.
