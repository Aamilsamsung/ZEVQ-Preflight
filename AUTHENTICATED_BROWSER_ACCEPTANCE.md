# Secure authenticated hosted browser acceptance

Status:prepared;NOT EXECUTED against hosted authenticated workspace. Local fixture validation8pass;JavaScriptsyntax/diffchecks pass. Local browser platform restrictions remain;GitHub CI is the supported runner.

## Owner prerequisite
Create/use a dedicated operator-authorized synthetic QA account with an email such as qa-browser@example.test in an isolated QA organization. Create a completed synthetic breaking-change scan and record at least one review decision through the app. Do not use customer accounts,reports or source. Existing trusted operator provisioning uses python -m app.manage create-user --email qa-browser@example.test --identity-verified on a trusted host with securely configured database access;never expose its password or database URL. This is fixture provisioning,not proof of public email ownership.

In repository Settings → Secrets and variables → Actions → New repository secret,set PREFLIGHT_HOSTED_BROWSER_FIXTURE to JSON with these fields:

```json
{"authorized_synthetic_qa":true,"email":"qa-browser@example.test","password":"YOUR_SYNTHETIC_QA_PASSWORD","organization_id":"ACTUAL_QA_ORGANIZATION_UUID","review_scan_id":"ACTUAL_COMPLETED_QA_SCAN_UUID"}
```

Enter actual values only in the secret UI or trusted local gh secret set flow. Do not use plain repository variables,workflow inputs,source files,issue comments or chat for credentials.

Tell Work only that the secret is ready. Work first checks branch heads,deployments and schema,then commits a fresh BROWSER_RUN_REQUEST.md marker at the current expected head. The workflow starts for that exact revision. Do not advance the branch during the run;source guards refuse session mutation when a newer head appears.

## Execution and evidence
Workflow:.github/workflows/hosted-authenticated-acceptance.yml. Uses existing hosted_browser_qa.cjs on the actual fixed staging origin. It exercises synthetic login,refresh persistence,nine workspace views at390/768/1440px,axe checks,overflow,mobile navigation,review history,JSON download,keyboard/reducedmotion,logout andconsoleerrors. Uses provided organization explicitly instead of defaulting to another organization.

Passwords are held in0600temporary runner fixtures. Screenshots are disabled;the uploaded artifact is only sanitized results.json. Failure DOM/source fragments,raw console messages,passwords and email identities are excluded from this CI artifact. Do not broaden upload paths to the credential files or raw reports.

This suite is authenticated workspace acceptance,not received-email verification,private-token authorization,a full screen-reader audit or every scan-creation journey. Real scan-creation browser acceptance can use the existing hosted_scan_journeys.cjs after its separate synthetic fixture prerequisites are securely prepared. No stub/provider mock is a substitute for those gates.
