# Finding review staging increment — 28 October 2026

Application commit `576fd92012851bf32b8613d2b73c81848e43125e` is live in Render deploy `dep-dbh05h5g1s2s73ce96a0`. Neon migration revision0002 and runtime grants on both new tables were independently read back. Existing Free Render/Neon resources are retained; no payments or paid resources were activated. This verification commit does not change the deployed application.

## Executed checks

| Feature | Expected | Observed | State | Evidence | Required follow-up |
|---|---|---|---|---|---|
| Python regression | Existing and review behavior remains correct | 131 passed, 2 PG-only local skips | PASS | CI40703211126 | None for executed suite |
| PostgreSQL | Migration roundtrip, scoped API, concurrent review conflict | 41 passed | PASS | Job122868291450 | None for executed suite |
| Restore | Decisions/history and tenant access survive dump/restore | Synthetic restore passed | PASS | CI job logs | Hosted Neon restore remains NOT TESTED |
| Browser regression | Existing workflow, review persistence/history | 37 workflow +13 supplemental checks passed | PASS | CI and local Chromium | Hosted responsive/manual checks remain open |
| Hosted review permissions | Viewer cannot write; outsider cannot read/write | HTTP403/404 as expected | PASS | Verification JSON | None for tested boundaries |
| Hosted exports | Current review included; original analysis unchanged | JSON/CSV match expected values | PASS | Verification JSON | PDF remains incomplete |
| Hosted expiry/concurrency token | Expiry reopens finding; stale update rejected | Expiry became open; HTTP409 | PASS | Verification JSON | No cross-scan/global suppression supported |
| Performance | Measure actual controlled requests | Scan13.422s; review save7.95s | PASS | Timed HTTPS test client | Investigate latency before broader beta |
| Hosted mobile/accessibility | Full responsive and manual assessment | Not executed in hosted browser | NOT TESTED | Local automation has narrower scope | Complete hosted/mobile/manual checks |
| Production readiness | Commercial release gates met | Email, private integration, monitoring, retention, billing and full roadmap incomplete | FAIL | Existing release inventory | Keep registration/launch closed |

Current verdict: **NOT READY FOR PRIVATE BETA** under the complete release checklist. This is a verified increment for restricted evaluation. It is not a new complete independent audit or a security certification.

## User guidance and rollback

See FINDING_REVIEWS.md for roles, expiry, review version conflicts, history pagination and per-scan scope. Review decisions do not hide evidence or reduce the scanner score. API-only append history is not protected against database-administrator changes. Organization deletion removes associated review data.

For application rollback use the prior tested application commit `0ec00899b75006235d956b0cbd032b0d949ed910` and retain additive migration0002 tables. Do not downgrade staging schema and discard decisions. Verify session/login, scan/report retrieval and worker progress after rollback. A rollback drill against the actual hosted database has not been executed.
