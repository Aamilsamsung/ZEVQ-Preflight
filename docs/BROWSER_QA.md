# Browser QA evidence

Local Chromium/Playwright QA executed against the actual FastAPI application, local database and separate static worker. No scan API responses were mocked.

**32 checks passed, zero browser console errors/uncaught exceptions.** The same workflow also passed in GitHub Actions at application commit `4a06fa7f93e34b2acc8e45d61807daef8d79d625` ([run 40652078061](https://github.com/Aamilsamsung/ZEVQ-Preflight/actions/runs/40652078061)); screenshots and results are downloadable from its test-results artifact. Results and screenshots are held under ignored `artifacts/` for local review. These checks are local; deployed browser QA remains BLOCKED by hosting.

Coverage: 12 public pages; sign-in; refresh persistence; repository connection; OpenAPI comparison that detects a removed endpoint; finding evidence/rule display; authenticated JSON and CSV downloads; ZIP processing through the worker; history/team/audit/settings views; data-control presence; mobile navigation; 390/768/1440-pixel dashboard layouts without document overflow; keyboard skip navigation; sign-out. Account/organization deletion controls were inspected but destructive clicks were not executed in this browser run; API tests cover their authorization behavior. Complete WCAG 2.2 AA conformance has not been assessed.

Browser inspection found and fixed mobile layout overflow and a browser-invalid repository input pattern. Unsupported navigation glyphs were replaced with SVG icons. Custom frontend 404 is served with HTTP 404; its final styling is not included in the original 32-check run.

## Reproduce

Install Playwright 1.62.1/Chromium in the test environment; this is test tooling, not a runtime dependency. Provision a disposable local account with `app.manage`, and put its email/password in ignored `artifacts/qa-credentials.json`. Do not use customer credentials. Alternatively, after migrating a disposable default local SQLite database, run `python -m scripts.seed_local_qa` to generate a random QA credential and fixture. The runner also expects `artifacts/qa-source.zip`, containing a supported small Python source. Run:

```bash
node scripts/browser-qa.cjs
```

Set `QA_BASE_URL` for a running target. `QA_START_SERVICES=1` starts local API/worker processes for the run. `QA_CREDENTIALS_FILE` can point at an alternate ignored credential file. `QA_CHROMIUM_MODULE` optionally points at an installed Chromium binary module when browser downloads are unavailable. The script writes `artifacts/browser-qa-results.json` and screenshots. It does not seed accounts or invent scan results.

A staging target additionally requires HTTP Basic staging access; configure the runner/browser's authentication explicitly before running against it. Deployed QA is not considered passed by these local results.
