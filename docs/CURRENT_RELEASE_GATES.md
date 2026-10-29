# Current release gates — 29 October 2026

Current candidate assessment: [PRIVATE_BETA_RELEASE_CANDIDATE.md](../PRIVATE_BETA_RELEASE_CANDIDATE.md). Verdict: **NOT READY FOR CONTROLLED PRIVATE BETA**.

Live:5e0e211 / dep-dbh4jk6c6qcc73cihja0 / schema0003. Candidate:d52fead / draft PR3 / additive0004/0005 not deployed. CI40851366795 passed207 Python,108 PostgreSQL,67 browser and8 monitor checks plus restore/fallback-worker scripts. Email recovery,repository-specific private GitHub and monitoring implementations are disabled pending real configuration and receipt tests.

Hosted recovery copy data matches on11 tables;restored application/worker behavior is blocked by runner DNS. Provider healthCheckPath remains empty. Candidate deployment,external alert receipt,email receipt/real private authorization,manual accessibility and controlled reliability measurements remain incomplete. See [blockers](../REMAINING_BLOCKERS.md) and [QA evidence](../FINAL_SECURITY_AND_QA_REPORT.md). Older acceptance reports are historical checkpoints. Public signup,payments and untrusted execution stay disabled.
