# Finding review decisions

Completed scans support per-finding human decisions: open, acknowledged, false positive, and suppressed. Owners, administrators and developers can record decisions; only owners and administrators can suppress. Viewers can read decisions and history. Suppressions require a reason and an expiry within 90 days. Expired suppressions read as open. Decisions apply only to the selected scan, including when another scan has the same finding ID.

Every change requires a 10–2000 character reason and the current decision version. Stale updates return HTTP409. PostgreSQL serializes updates using a scan row lock. Current decisions and append-only API history are committed with an audit event. History is not tamper-evident against database administrators and follows scan/organization deletion. Avoid entering confidential source or credentials in reasons.

The report displays decisions alongside original evidence. JSON and CSV downloads include current decisions. Original findings, severity and risk scores remain unchanged; a human false-positive label is not a scanner conclusion. No deployment policy is automatically changed. History is available to organization members in the UI and in pages of 100 through GET `/api/orgs/{org}/scans/{scan}/findings/{finding}/reviews?offset=0`.

Migration 0002 adds `finding_reviews` and `finding_review_events`. Startup runs the migration with the owner connection and then refreshes restricted runtime grants. Roll back application code while retaining these additive tables; do not downgrade the production schema and discard review history. Existing scans remain readable without decisions.

Validation errors omit rejected input values, protecting passwords and submitted source from error-response reflection. This does not replace server-side authorization, CSRF protection or safe handling of review text.

## Verification at implementation

Local Python regression: 131 passed, 2 PostgreSQL-only skips (133 collected). Alembic schema check: no pending operations. PostgreSQL concurrency, migration roundtrip, synthetic backup/restore and browser checks must pass CI before deployment. Hosted results are recorded separately after deployment. Public release remains restricted; this feature does not close the full commercial release checklist.
