# Current release gates — 29 October 2026

Current candidate assessment: [PRIVATE_BETA_RELEASE_CANDIDATE.md](../PRIVATE_BETA_RELEASE_CANDIDATE.md). Verdict: **NOT READY FOR CONTROLLED PRIVATE BETA**.

Live:5e0e211 / dep-dbh4jk6c6qcc73cihja0 / schema0003. Candidate:f8619a5 / draft PR3 / additive0004 not deployed. CI40804324589 passed186 Python,87 PostgreSQL,63 browser and8 monitor checks plus restore/fallback-worker scripts. Email recovery and monitoring implementations are disabled pending real configuration and receipt tests.

Hosted recovery copy data matches on11 tables;restored application/worker behavior is blocked by runner DNS. Provider healthCheckPath remains empty. Candidate deployment,external alert receipt,email receipt/private integration,manual accessibility and controlled reliability measurements remain incomplete. See [blockers](../REMAINING_BLOCKERS.md) and [QA evidence](../FINAL_SECURITY_AND_QA_REPORT.md). Older acceptance reports are historical checkpoints. Public signup,payments and untrusted execution stay disabled.
