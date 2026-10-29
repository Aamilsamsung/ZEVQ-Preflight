# ZEVQ Preflight private-beta release candidate

29 October 2026, Asia/Calcutta. **NOT READY FOR CONTROLLED PRIVATE BETA**.

## Reconciled source and deployment

- Existing repository: https://github.com/Aamilsamsung/ZEVQ-Preflight
- Actual staging: https://zevq-preflight-staging.onrender.com
- Live commit: `5e0e211fe10045d6fbb4ee8c6b3c0b31cd706c70`; deployment `dep-dbh4jk6c6qcc73cihja0`; live schema `0003`.
- New implementation candidate: `d52feadf19ef7d3608124544c71012361c4e39d6`, on `implementation/beta-recovery-20261029`, draft https://github.com/Aamilsamsung/ZEVQ-Preflight/pull/3.
- PR1 remains draft against main; PR2 remains draft verification-only against the implementation branch; PR3 builds on PR2's audit checkpoint. No PR was merged or protected branch force-pushed. Staging has not been redirected to a new database or repository.

The new candidate is **not deployed**. The Render connector can trigger only the configured service branch and cannot select a commit or update the service. That branch remains `implementation/secure-preflight` at the previously tested live commit. No authenticated Render CLI credential is available. Triggering it now would redeploy the old build, so this was not represented as deploying the candidate.

After final CI succeeds and the code is reviewed, the owner can choose Render service → Manual Deploy → Deploy a specific commit → candidate SHA above. This is a deployment action, not approval for public launch. Do not merge unreviewed branches to work around the connector limitation.

## Implemented in this increment

Email verification and password recovery for provisioned accounts: opaque single-use15-minute tokens, SHA256 hash storage, TLS-only SMTP, generic request responses, rate limits, origin checks, session revocation, outstanding-link invalidation and token-safe audit actions. Tokens are delivered as fragments and submitted by POST, not in HTTP request URLs. Owner CLI can provision a pending-email account. Accessible request/confirmation/reset screens preserve the existing dark theme. Delivery remains disabled pending configuration and a received-message test.

Database-aware `/health`: dedicated small pool, explicit connection/statement timeouts and generic503 on dependency failure. Separate bearer-protected operational endpoint reports aggregate repeated failures, stale running jobs and queue delays. The external GitHub monitor implements fixed-target probes, thresholds, incident deduplication and recovery notifications, but remains opt-in and unactivated. A scheduled workflow on an unmerged branch is not a deployed monitor.

Fixed the global `history` function collision that broke recovery fragment removal. Fixed non-ASCII authentication/CSRF/monitor values causing500s; comparisons now fail closed using bytes. These fixes are verified locally; they are not yet fixes on staging.

## Private-source increment — verified candidate d52fead

Added opt-in,repository-specific fine-grained GitHub tokens encrypted with Fernet and bound to org,repository,name and credential version. Owner-only connection/rotation;scoped repository/revision lists;private static worker resolution to immutable SHAs;bounded HTTPS archives with no credential forwarding to codeload;disconnect cancellation and safe provider errors. Existing public scanning is preserved. GitHub App/OAuth are not implemented. No real private token or repository was used.

CI40851366795 passed207 Python tests (4 PostgreSQL-only skips),108 PostgreSQL tests,67 browser checks,8 monitor checks and both recovery scripts. Dependency audit:35 packages,zero known vulnerabilities. Migration0005 and runtime grants were exercised in disposable CI. The feature remains disabled until explicit host configuration and received authorization through the application's owner form. See `docs/PRIVATE_GITHUB.md`.

## Scope assessments

**A. Full planned private beta: NOT READY.** Email receipt/reset, private GitHub authorization/scanning, HTTP probe configuration, external alert receipt and full hosted recovery remain mandatory gaps. Repository-specific private GitHub access is now implemented and tested with a controlled provider fixture; real private authorization and hosted scan acceptance remain unverified. GitHub App and OAuth are still unavailable.

**B. Restricted evaluation: NOT APPROVED and not ready to recommend.** Provisioned accounts with public GitHub/ZIP/OpenAPI only remain the existing evaluation mode. Monitoring and recovery cannot be waived by reducing integration scope. No owner approval to use restricted scope as the release recommendation is assumed.

## Safety and operations

Existing accounts, organizations, reports, review decisions and audit history were preserved. Staging remains schema0003; the new additive migrations0004/0005 exist only in the candidate and were tested in disposable databases. Existing verified accounts are not silently reclassified as newly email-verified. Retention remains disabled; live applied-cleanup count is zero. Public signup, payments, customer-code execution and external AI remain disabled. Existing Free Render and Neon resources are used; no plan upgrade, purchase or live payment was performed.

Two isolated Neon branches were created for non-destructive recovery preparation; see the runbook for exact IDs, verified data-copy evidence, access restrictions and remaining application-level verification. They are not a substitute for an off-provider backup. Cleanup must target only these copies after the required approval and evidence preservation.

See `FINAL_SECURITY_AND_QA_REPORT.md`, `RECOVERY_AND_ROLLBACK_RUNBOOK.md`, `INTEGRATION_VERIFICATION.md` and `REMAINING_BLOCKERS.md`. Raw sanitized evidence is under `docs/release-candidate-2026-10-29/`. Earlier acceptance files are historical checkpoints, not proof of this candidate's hosted acceptance.
