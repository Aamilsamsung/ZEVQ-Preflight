# Private GitHub integration — gated beta implementation

This implementation uses a fine-grained personal access token for one named private repository. It is not GitHub App installation or OAuth. The feature is disabled by default and has NOT passed a real authorized private-repository acceptance test. Mock-provider tests do not establish real access.

## Operator setup

Store a privately generated Fernet key in the existing host secret store as `PREFLIGHT_CREDENTIAL_KEY`; set `PREFLIGHT_PRIVATE_GITHUB_ENABLED=1` only for an approved test after deploying and verifying migration0005. Generate the key on a trusted operator machine using `cryptography.fernet.Fernet.generate_key()`. Never put the key in chat,Git,logs or a browser URL. Preserve it securely:losing/changing it makes stored credentials unreadable. There is no automatic key-rotation ring yet;disconnect/reconnect credentials under a planned key rotation. Do not enable this against the older live schema0003.

Only organization owners can connect or replace credentials. In Repositories,enter the exact owner/name and an expiring fine-grained token restricted to **only that repository**,with **Contents:read-only** and required Metadata access. Request no write/admin/organization permissions. Classic tokens are rejected. GitHub organization approval may be required. The server cannot introspect/prove every permission on a supplied fine-grained token;the operator must verify the provider's selected-repository/read-only settings. Regardless of broader provider grants,application use is confined to the one bound repository.

The application verifies matching private metadata and a Contents-read branch request before storing the credential. It does not enumerate unrelated repositories. Connected repositories are listed only within the authorized organization. Branch and commit endpoints return up to50 entries per page,max20pages;the UI currently shows the first50 and allows manual refs for others. Commit messages and raw provider error bodies are not returned. The API resolves requested refs to immutable SHAs before downloading archives;the report records those resolved values.

## Storage and access boundaries

Fernet authenticated encryption protects the token at rest using a host key outside PostgreSQL. Encrypted claims bind org ID,repository ID,name and credential version. Cross-tenant lookups and swapped ciphertext fail closed. Raw tokens are never returned by API/report/account export. Job payloads contain only a repository ID and credential version,not the credential or private source. Credentials are decrypted in the trusted static worker when needed. No private source is sent to AI or executed.

Only fixed HTTPS api.github.com requests receive Bearer authorization. Archive redirects must point to codeload.github.com;the Authorization header is removed for that request. HTTPX INFO request logging is disabled because signed download URLs can contain temporary credentials. Archive size/parsing bounds remain in force. Private provider error bodies and signed URLs are not serialized into scan errors. Rate-limit responses stop without automatic retry.

## Disconnect and rotation

Removing a stored credential cancels queued/running scans for that repository,clears their payload/lease and prevents late report publication. Replacing a credential increments its version and cancels old jobs. This does not abort an already in-flight network request immediately,but its result cannot be published after cancellation. Existing completed reports remain tenant-scoped and follow retention policy.

**Application disconnect does not revoke a PAT at GitHub.** Revoke the token separately in GitHub's settings. Administrators can remove a repository under the existing repository-management policy;only owners can connect/replace raw credentials. No provider-wide token revocation API is claimed.

Deleted/renamed repositories,invalid refs,expired/revoked tokens,permissions,network failures and rate limits produce bounded honest errors. Renames are not followed automatically;reconnect the correct name. The existing public workflow remains independent of credentials.

## Rollback limitations

Migration0005 adds source_kind and repository_credentials;existing repositories default to public. Older source can read its known columns against the additive schema. Older workers do not implement private payloads;the rollback regression verifies they fail closed without a report. Cancel/drain private jobs before an approved rollback. Never downgrade/drop the credential table on live data as a substitute for application rollback.

## Required real acceptance

1. Deploy the exact CI-verified candidate to protected staging and verify0005/runtime grants.
2. Configure the encryption key securely,enable only for the approved synthetic owner and create a token through GitHub's own secure UI. Never send it in chat.
3. Connect an authorized private fixture repository containing known safe/breaking revisions. Confirm provider permission and repository selection.
4. Select branch/commit SHAs,start the scan,verify progress,evidence,resolved revisions,JSON/CSV and history.
5. Verify another organization cannot access repositories,revisions,scans or reports. Verify viewer/administrator credential-write restrictions.
6. Remove stored access during an eligible job,verify cancellation/no late publication,and separately revoke the provider token. Exercise expired-token/rate-limit behavior without excessive requests.
7. Record actual scan IDs and results. Until then:implementation prepared,real private integration **NOT VERIFIED**.

Official references consulted29October2026:
- https://docs.github.com/en/rest/repos/contents#download-a-repository-archive-zip
- https://docs.github.com/en/rest/branches/branches#list-branches
