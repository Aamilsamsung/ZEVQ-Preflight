# Final security and QA report

29 October 2026, Asia/Calcutta. Candidate **f8619a5e6fb83ab8fcc4b4b094c8a3d2501bb7c7** is verified in CI, not deployed. Live remains **5e0e211fe10045d6fbb4ee8c6b3c0b31cd706c70**, Render dep-dbh4jk6c6qcc73cihja0, schema0003. Candidate migration0004 is additive and tested in disposable databases only.

## Executed tests

GitHub Actions run **40804324589**, job **123219506461**, completed successfully. Logs were retrieved and inspected, not inferred from a green badge alone.

| Suite | Executed result | Evidence |
|---|---|---|
| General Python |186 passed,4 skipped |Final CI log;43.06seconds |
| PostgreSQL boundaries/concurrency |87 passed |Final CI log;42.40seconds; includes parallel reset-token consumption |
| Main real local browser |37 passed,zero failures/errors |Final CI and separate isolated local run |
| Supplemental browser |19 passed |Final CI and separate isolated local run |
| Recovery screens |7 passed |Real local rendering and disabled backend; enabled email API responses explicitly mocked; zero axe violations in tested mobile reset success state |
| External monitoring |8 deterministic checks passed |Fixed-target, failure/degraded handling, three-probe threshold, duplicate suppression and recovery; real inbox delivery NOT TESTED |
| Backup/restore helper |PASS |Actual disposable PostgreSQL16 pg_dump/pg_restore, preserved session, restored queued static job, report/reviews/history/retention and isolation |
| Previous-source helper |PASS |Exact9e78cde source, restored session/report/history/isolation and fallback static worker on schema0004 |
| Dependency advisories |34 dependencies,zero known vulnerabilities,zero skips |Fresh pip-audit execution; requirements unchanged |
| Bounded local static batch |3 completed,expected finding in each |Two threads,three controlled OpenAPI inputs; static inspection only |

**344 reported test/check cases passed across CI suites, plus two recovery helper runs.** Four skips in the general suite are PostgreSQL-only cases covered by the separate87-test PostgreSQL run. Suite cases overlap in requirements; this is not344 unique product features. The separate local batch and repeated local test runs are not inflated into the CI total. No final CI failures remain.

Earlier runs failed during development:the recovery screen exposed a global history-name collision; a harness used a nonexistent `.venv` path on CI; malformed credential regression tests reproduced TypeError crashes. Each was fixed and the applicable suite rerun. A local browser run against an old repeatedly seeded fixture hit the real20-scan quota; it was rerun against a fresh isolated local database and passed37/37. No quota was raised or data deleted to hide that result.

## Findings and acceptance matrix

| Feature | Expected | Actual observed | State | Severity / required fix |
|---|---|---|---|---|
| Email tokens |Hash-only,expiring,single-use |Invalid,expired,wrong-purpose,replayed,resend and concurrent-reset cases pass; password changes/operator reset invalidate links | PASS in candidate |Complete received-email test before enabling |
| Account recovery |Generic responses,session revocation |Unknown/unverified accounts receive same request response;provider failure generic;all sessions revoked after valid reset | PASS in candidate |No formal constant-latency or complete enumeration-resistance guarantee |
| Provisioning |Pending mailbox can be confirmed |CLI pending account cannot sign in before verification;verification does not register absent users | PASS in candidate |Operator identity checks still required |
| SMTP transport |TLS before credentials |SSL465 and STARTTLS587 ordering and hostname verification tested using a fixture | PASS deterministic |Real provider/inbox BLOCKED |
| Credential-header handling |Malformed input rejected |Reproduced non-ASCII failures locally;byte comparison now yields401/403/404 as appropriate | PASS in candidate |Medium;deployed source still awaits fix promotion;no live attack performed |
| Recovery fragment/UI |No token in HTTP URL;clear status |History-name collision fixed;fragment removed;POST payload used;password mismatch announced | PASS local/CI |Hosted candidate not yet tested |
| Public access boundary |No public signup or tenant bypass |Existing isolation/roles/CSRF regression suite passes;new public recovery routes reveal no tenant/source data | PASS tested cases |Not an ASVS certification |
| ZIP/resources/review/retention |Existing guards preserved |Full regression and PostgreSQL boundary suites passed;live cleanup remains disabled | PASS tested cases |No hosted destructive test performed |
| Health dependency failure |Generic503 on failed DB probe |Dedicated-pool SELECT1 and local failure test pass | PASS local |Provider path remains BLOCKED;no staged outage induced |
| External alerting |Operator receives incident/recovery |Workflow/endpoint fixtures pass;no deployed schedule or received notification | BLOCKED |High;configure/review and verify actual receipt |
| Hosted copy integrity |Records copied without live overwrite |All11 table count/content fingerprints match schema0003 | PASS narrow scope |Not restored authentication/worker proof |
| Hosted recovery/failover |Application and workers verified on restored target |Runner DNS prevents application connection | BLOCKED |High;complete isolated hosted rehearsal |
| Private GitHub |Authorized private scan and revoke |No customer-facing integration implemented;no private fixture scan | FAIL |Engineering plus secure authorization required |
| Fresh hosted full acceptance |Tested candidate equals deployed commit |Candidate f8619a5 differs from live5e0e211 | BLOCKED |Deploy exact verified candidate after review,then rerun hosted suites |
| Complete manual accessibility |Keyboard/contrast/assistive technology |Automated coverage passes;full manual assessment unperformed | NOT TESTED |Medium;retain explicit incomplete assessment |
| Controlled idle cold start |Defined idle interval and app-ready duration |One30-second public request timed out;cloud browser later showed Render wake-up,then login after reload | NOT TESTED as benchmark |Medium;do not invent cold-start latency or always-on behavior |
| Public launch / billing |Disabled pending approval |Remain disabled | PASS guard |No release approval implied |

## Browser and accessibility coverage limits

Current CI covers local main workflows and supplemental mobile/table/keyboard behavior; the new recovery state is tested at390×844. Its enabled-provider responses are mocked; API/token behavior is separately tested against the real backend. This is not an executed real-email journey.

Historical hosted suites on the still-live5e0e211 passed62 workspace checks,37 informational-page checks and three actual OpenAPI/GitHub/ZIP submissions with JSON/CSV/history. Those were not rerun against f8619a5 because it is not deployed. This session's independent cloud browser displayed the provider wake-up page,then the actual5e sign-in page after one reload. No user password was entered into that browser.

Existing automated axe coverage is not a WCAG2.2AA certificate. Incomplete automated rules include contrast and certain ARIA/link checks;manual screen-reader,full contrast and physical-touch-device assessment remain incomplete. Existing visual identity was preserved.

## Performance and resource observations

Read-only live Neon EXPLAIN ANALYZE for the synthetic QA organization's scan list:25 total table rows,13 matched,0.742ms planning,0.088ms execution,26KB in-memory sort. A sequential scan is reasonable for this small table. No index change was made from one small-sample plan.

Render metrics from2026-10-29T01:40–01:50UTC:three memory samples138469380–138477570bytes (about132.06MiB),limit536870900bytes (about512MiB);two CPU samples0.001888–0.001928CPU. These mostly idle samples do not prove peak capacity,leak freedom or scan throughput.

Local two-thread/three-fixture static batch:execution times0.76/2.60/3.44ms,p50=2.60ms,p95 nearest-rank=3.44ms,batch wall17.03ms. Three samples are too few for a stable tail estimate. Claims were admitted serially because SQLite does not implement PostgreSQL SKIP LOCKED semantics. This is not a hosted/concurrent admission benchmark.

Earlier hosted20-sample warm medians remain historical:report265.5ms and review-save301.5ms,with p95286ms/335ms. No new candidate hosted latency,controlled idle cold-start,memory stress,full API error-rate aggregation or long-running leak test was established. Source-point and compute-start timestamps are not recovery RTO.

## Security posture and conclusion

No customer source executed,no TLS bypass,no production restore,no live cleanup,no public registration,no payment activation,and no private connector credentials reused. Locked dependency audit is limited to known advisories;FastAPI TestClient deprecation warnings remain. Email dispatch is an after-response task,not a durable retry outbox;process interruption requires requesting another link. SMTP submission is not proof of receipt. Idle-worker heartbeat and full API error-rate monitoring remain incomplete.

**NOT READY FOR CONTROLLED PRIVATE BETA**. Neither the full planned scope nor a reduced scope has all mandatory operational gates verified. Restricted-scope approval was not requested as a substitute for fixing monitoring/recovery. See remaining blockers for exact next actions.
