# Integration verification — 29 October 2026

Live app5e0e211, schema0003. New candidate d52fead, additive migrations0004/0005 pending deployment. No merge or public-launch approval is implied.

| Integration | Implementation / observed evidence | State / precise remaining requirement |
|---|---|---|
| Render existing Free service | Provider confirms live dep-dbh4jk6c6qcc73cihja0, branch implementation/secure-preflight, auto-deploy off | Candidate not deployed:connector cannot select commit; owner can use Manual Deploy → specific candidate commit after review/CI |
| HTTP health configuration | Blueprint has /health; provider still empty | BLOCKED:Settings → Health Checks → Edit → /health → Save; read back and safely verify failure detection/persistence |
| Neon existing Free PostgreSQL16 | Live schema0003; no enabled retention or applied cleanup; isolated queryable copy has matching11-table content fingerprints | PARTIAL:hosted application recovery/worker/tenant verification blocked by runner DNS; no live restore |
| Email SMTP | TLS465/STARTTLS587, hashed15-minute single-use tokens and recovery UI implemented; fixture transport/logic tests pass | BLOCKED:approved free SMTP provider/sender must be connected via Render secret environment fields; actual inbox receipt, verification and reset not tested |
| External operational monitoring | Fixed-target probe workflow and protected aggregate endpoint implemented; deterministic outage/dedup/recovery tests pass | BLOCKED:review workflow placement, secure monitor-token configuration, opt-in variable and a controlled incident with actual received notification. Default-branch scheduling cannot be claimed for this unmerged branch |
| Public GitHub | Existing prior hosted scan at immutable equal revisions passed with zero findings; live fetcher/engine unchanged;candidate public-fetch regression tests pass | Historical hosted PASS on current live commit; no fresh scan performed in this increment; rate-limit quota must be respected |
| Private GitHub |Repository-specific fine-grained access,encrypted binding,owner connection,revision selection,immutable static fetch and local disconnect implemented;21 provider/security tests and4 UI checks passed |BLOCKED real authorization/hosted acceptance;GitHub App/OAuth remain unavailable;provider PAT revocation is a separate owner action |
| Payments / public registration | Disabled | Intentionally unavailable; no provider or billing activation |
| Customer execution / external AI | Disabled | No customer programs executed or private source transmitted |

## Secure owner configuration

Email fields and operating limits are fully listed in `docs/EMAIL_AND_EXTERNAL_MONITORING.md`. Configure them only in host secret settings after choosing an approved provider and verified sender. Keep `PREFLIGHT_EMAIL_ENABLED` unset until configuration is valid and the delivery test is authorized. Never send credentials in chat. Existing operator recovery remains available through an interactive trusted shell.

For monitoring, privately generate a32+character token and set identical `PREFLIGHT_MONITOR_TOKEN` secrets in Render and GitHub Actions. The workflow needs repository variable `PREFLIGHT_MONITOR_ENABLED=true`, repository Issues enabled and reviewed placement where scheduled Actions can execute. The issue channel must be verified as an actual received external alert, not merely a database audit event or local fixture. The token endpoint reports no tenant names, source, credentials or raw provider errors. Full API error-rate aggregation and idle worker heartbeat detection are not implemented.

Private integration must not reuse this ChatGPT session's GitHub connector authorization as customer SaaS authorization. Do not request unrestricted repository access. The repository-specific integration is now prepared. Configure the host encryption key and enable flag only after deploying the verified migration0005 candidate;then enter a repository-restricted read-only token through the owner form,never through chat. See `docs/PRIVATE_GITHUB.md` for real acceptance steps. GitHub App/OAuth are not claimed.
