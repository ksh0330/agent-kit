---
name: review
description: Read-only review of a diff, plan or finished slice. Reports evidence-backed defects ordered by severity; changes nothing.
---

# Review

This mode is read-only: no edits to tracked files, no commits, no configuration changes, nothing sent externally. Temporary scratch directories for running checks are fine.

1. Establish the base commit and the exact diff under review.
2. For a plan: does it match the request, are the criteria observable, are any numbers or confirmations invented?
3. For code, prioritise real execution paths: wrong results, missing input validation, permission or storage boundaries, regressions, and docs that disagree with behaviour.
4. Read and run only what is needed to confirm a finding. Never run checks that modify real data or external systems.
5. Report findings only when you can point to evidence:

   | ID | Severity | file:line | How to reproduce | Impact | Suggested fix |
   |----|----------|-----------|------------------|--------|---------------|

6. If nothing is found, say "no findings in the reviewed scope" and list what was and was not checked. Do not pad the list.
7. If the review ran in the same session that wrote the code, say so; it is not an independent review.

Done when each finding links to a reproduction or file location and the builder can act on it. The builder records fix / defer / reject with a reason.
