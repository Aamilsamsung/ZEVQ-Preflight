# ZEVQ Preflight

Read-only API change-risk analyzer for public GitHub repositories and uploaded ZIP files.

## Local setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000 and API docs at /api/docs.

Run tests with `python -m pytest -q`.

The MVP uses deterministic heuristic static checks; it **does not** execute untrusted repository code, predict all business outcomes, or provide an enterprise-ready security assessment. ZIP uploads should not be used with confidential code on public deployments. GitHub scans support public repos only.

**Roadmap:** API contract diffs, authenticated scans, isolated test runs, change history, integrations, deployment and audit logs.
