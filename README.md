# ZEVQ Preflight

**Know what breaks before it breaks.** Evidence-backed static change analysis by ZEVQ Labs.

This branch is a closed-evaluation MVP, not a commercially released or enterprise-certified SaaS. Public registration, payment collection, AI transmission, private GitHub authentication and customer-code execution are disabled.

## Working capabilities

- Provisioned accounts, Argon2 passwords, persistent HttpOnly sessions, expiry and session revocation.
- Organizations, owner/administrator/developer/viewer permissions and server-side tenant isolation.
- Public GitHub repository comparisons, bounded source ZIP uploads and OpenAPI 3 JSON comparisons.
- Durable database jobs, process-separated static workers, lease recovery, cancellation and admission quotas.
- Python AST syntax/routes/function-signature checks, selected security-review rules and configuration-change review.
- Reproducible findings with rule/version, location, evidence, confidence and remediation.
- Dashboard, repository workspace, scan progress/history, evidence reports, JSON/CSV exports, team membership and audit events.
- Account export, organization/account deletion and closed-staging protection.

Read [release status](docs/RELEASE.md), [operations](docs/OPERATIONS.md) and [browser QA](docs/BROWSER_QA.md) before deployment.

## Local development

Python 3.12 is the tested runtime. SQLite is supported for local development only.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m alembic upgrade head
python -m app.manage create-user --email you@example.com --identity-verified
```

The operator must first verify the supplied email owner's identity. This provisioning command is not an email-delivery or automated verification integration. It prompts securely for a password; there are no default accounts/passwords.

Start the application and static worker in separate terminals:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
python -m app.worker
```

Open http://127.0.0.1:8000. Environment values are read from the process environment; `.env` files are not automatically loaded.

## Use

1. Sign in and select an organization.
2. Connect a permitted public GitHub `owner/repository`, or choose an authorized ZIP/OpenAPI upload.
3. Choose baseline and proposed revisions. Prefer immutable commit SHAs for reproducibility.
4. Submit the comparison and wait for the worker to complete it.
5. Review evidence, confidence, coverage gaps and limitations. Download JSON/CSV reports.
6. Owners can add already provisioned accounts to their organization; email invitations are unavailable.

The risk score is a prioritization index, not a probability that deployment will fail. A completed scan means supported static analysis finished. It does not prove safety. Import relationships are declared imports with unresolved targets, not a verified runtime impact graph.

## Tests

```bash
python -m pytest -q
python -m pip check
```

CI runs the regression suite plus API boundaries against PostgreSQL 16, including upgrade/downgrade/upgrade migration checks. `TEST_DATABASE_URL` is destructive test-only configuration: the API fixtures recreate its schema. Never point it at a staging or production database.

Browser QA uses Playwright and a real running API/worker. See [instructions](docs/BROWSER_QA.md).

## Deployment

`render.yaml` now configures one **Free** Render web instance with a process-separated static worker (`python -m app.serve`). A dedicated external Free PostgreSQL database must be supplied through the host secret store. No paid worker, Render database, disk or upgrade is configured. Render can sleep/restart; jobs remain in external PostgreSQL and recover on restart. No public launch is implied. Staging refuses to start without PostgreSQL and a strong staging password. See the free-tier limitations in the operator guide.

Support: [zevqlabs@gmail.com](mailto:zevqlabs@gmail.com).
