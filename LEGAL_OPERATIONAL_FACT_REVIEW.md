# Legal draft: implemented-behavior fact review

**Draft review only. No legal approval, jurisdiction-specific assessment or compliance certification.** The current UI/legal gate remains version `2026-10-29`; no approval flag or deployed policy text has been changed.

| Topic | Product behavior checked in source | Draft improvement needed |
|---|---|---|
| Source and evidence | ZIP/repository source is stored in queued/running work payloads; terminal paths clear payloads; reports can retain evidence and paths | Explain transient work inputs separately from retained report evidence |
| Private credentials | Optional repository-scoped tokens use authenticated encryption with a host-held key | Disclose credential handling when that feature is actually offered; do not imply provider-token revocation on SaaS disconnect |
| Account mail | Mailbox address, token hashes and account events support the gated verification/reset flow | Describe provider processing only after the sender/provider is selected; do not claim delivered email today |
| Retention | Scheduled cleanup disabled; manual 7–3650-day policy with preview/confirmation, bounded batches, review-history preservation | Replace vague automatic-retention language with the actual manual controls and remaining operator decisions |
| Deletion/export | Owned organizations must be removed before account deletion; account event export is bounded; copies/backups may persist | Avoid promising immediate erasure from every backup; state export scope/limits |
| Infrastructure | Existing Render, Neon and GitHub; SMTP provider not configured | Identify actual processors and locations only after verification; do not invent contracts or guarantees |
| Cookies/logs | Essential revocable session cookie, hashed rate buckets, operational/audit records | Explain security/operational records without claiming no data is ever logged |
| Incident handling | Support/disclosure email exists; no complete on-call or incident-response SLA | Provide contact and verified process; do not invent guaranteed response times |
| Availability/limitations | Free service can sleep; static analysis can miss issues; no customer code execution | Retain clear availability and analysis limitations |

## Proposed operational wording for owner review

**Source and credentials.** Supported uploads and repository inputs are processed for static analysis without executing customer programs. Work inputs can be stored while a job is queued or running. Terminal-job handling clears work payloads, but findings, reports, paths and relevant evidence can remain in organization records. Optional private-repository access uses an encrypted repository-scoped credential with a key held outside the database. Removing stored access from Preflight does not itself revoke the credential at GitHub.

**Retention, deletion and exports.** Automatic scheduled cleanup is not enabled. Owners can configure manual retention and review a bounded cleanup preview before applying it; records with review history are protected by those cleanup rules. Authorized organization/account deletion and export controls apply to active application records. Export scope can be bounded. Deletion from the active application is not a verified guarantee of immediate removal from provider backups or isolated recovery copies. The operator must finalize the retention and recovery-copy policy before public launch.

**Email and operational services.** If verification/reset email is enabled after acceptance, the selected approved mail provider processes the destination address and necessary message content. Existing hosting/database and repository integrations use Render, Neon and GitHub. The mail provider and applicable operational details must be finalized before publishing this paragraph as an active service description.

**Support and incidents.** Contact zevqlabs@gmail.com with sanitized request/scan references. Do not email credentials, bearer links or confidential source. No response-time or availability guarantee is currently implemented. The operator must define and approve the final public support and incident-handling process.

These proposals are not deployed or approved. If accepted, reconcile the UI policy text, version/consent requirements and tests before changing any legal-approval flag. Preserve historical consent records; do not silently treat old acceptance as acceptance of revised text.
