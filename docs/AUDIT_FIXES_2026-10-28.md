# Audit corrections — 28 October 2026

This follow-up addresses the five defects in `LIVE_QA_AUDIT_2026-10-28.md`. That audit remains a historical report of deployed commit fd8e122; its failures are not retroactively changed to passes.

| Defect | Correction | Regression coverage |
| --- | --- | --- |
| AUDIT-01 Review summary | Spread generated nodes into `replaceChildren`; ZIP shows three rows and contract/GitHub inputs show four | Existing browser workflow asserts real summary rows and absence of object strings; supplemental contract check |
| AUDIT-02 Error headers | Outermost response-header middleware also handles early authentication, redirect and validation returns | Anonymous401, redirect303, registration403, foreign-Origin403 and schema-validation422 assertions |
| AUDIT-03 Dialog name | Associate dialog with its title and description using ARIA | Supplemental named-dialog lookup; cancellation still avoids deletion |
| AUDIT-04 Landing CTA | Workspace links go to `/app`; the server decides whether authentication is required | Signed-in landing link reaches the actual dashboard without another login |
| AUDIT-05 Evidence pointers | Escape dynamic route, media-type and property keys per RFC6901; parameter schemas use array indices | Direct endpoint and nested media/property pointers resolve against baseline fixtures |

The engine/application version is now0.2.1. Existing stored reports retain their original evidence and version. New reports use the corrected pointers. No database migration, registration opening, payment activation or permission expansion is required.

Local verification:110 Python checks passed; one PostgreSQL-only local check skipped. The two former expected failures are now ordinary passing tests. The37-check real-browser workflow passed, including contract/ZIP scans, exports, responsive pages and logout. All9 supplemental browser checks passed. The supplemental browser suite adds the landing CTA, summary and named-dialog checks plus supported accessibility rules; incomplete contrast checks remain outside a conformance claim. It runs in CI after the ordinary browser suite, using a separate local port and the disposable local QA database. CI now installs the pinned axe package and executes the supplemental suite. API and worker logs are captured in ignored artifacts for failure diagnosis.

One browser run during simultaneous local diagnostics saw a500 on logout. It was not reproduced when the suites ran sequentially; the captured rerun showed logout200 and no console errors. The cause is not established. The shared SQLite fixture should not be exercised by multiple browser runners concurrently.

Deployment and live verification must be recorded separately against the resulting commit; local passes alone do not close hosted release gates. Two-user hosted isolation/RBAC, hosted mobile/touch, manual contrast/screen-reader QA, backup restoration and operator recovery exercises remain blocked or not tested. Public-beta readiness is not asserted by this correction.
