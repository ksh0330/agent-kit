---
name: verify
description: Before claiming something works, match each acceptance criterion against fresh command output. Use before handoff, release or "it's done".
---

# Verify

1. For every claim, choose the command that would prove it and run it now. Read the full output, exit code and any skipped tests.
2. Scale the check to the change: wording needs a look, a function needs its tests, shared modules and storage need the affected paths, a release needs the full suite from a clean checkout.
3. Cover the edges the change touches: empty input, malformed input, boundaries, permission denials, duplicate writes, persistence after restart.
4. Keep mock, local and real-integration results apart. Never present an earlier run as a current one.
5. Fill in a table:

   | Criterion | Met / Partial / Not met / Unverified | Evidence (command, test name, file:line) |
   |-----------|--------------------------------------|------------------------------------------|

6. For a UI, check input -> processing -> saved -> reload, plus error states. If you cannot drive the UI, give the user the exact URL, steps and expected result, and mark it unverified.
7. Fix defects inside your mandate and rerun the affected checks. Ask only about actions outside it.
8. Test servers started for verification must be stopped afterwards.

Done when every criterion has a current result. Unverified stays unverified; a required failure means fix it or report the limitation.
