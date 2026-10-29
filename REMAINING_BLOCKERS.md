# Remaining blockers — 29 October 2026

| Priority | Owner | Evidence | Resolution criteria |
|---|---|---|---|
| P1 Candidate deployment | Hosting owner / reviewer | Candidate f8619a5 passed CI40804324589;live remains5e0e211;connector cannot select a commit | Review PR3;Render Manual Deploy → Deploy a specific commit → f8619a5e6fb83ab8fcc4b4b094c8a3d2501bb7c7;verify schema0004 and hosted workflows;do not merge unreviewed branches |
| P1 HTTP health configuration | Hosting owner | Actual healthCheckPath empty; connector lacks update operation | Render Settings → Health Checks → `/health` → Save; provider read-back, deployment persistence and safe failure test |
| P1 Hosted recovery | Release operator | Isolated snapshot branch br-orange-water-b36lbess and queryable child br-mute-bread-b3znuqmn at parentLSN0/1DC1868 created; aggregate rows verified; runner DNS blocked | Use a securely connected runner to verify restored application/session/worker/tenant data; do not redirect staging or overwrite parent |
| P1 External alert receipt | Owner + release engineer | Opt-in workflow and aggregate endpoint implemented; no schedule or delivery activated | Secure token configuration, reviewed workflow placement, controlled incident, actual received notification and recovery |
| P1 Email recovery delivery | Owner + release engineer | TLS-only SMTP integration and tests implemented; provider unavailable | Connect approved free SMTP provider via host secrets; verify inbox receipt, ownership verification and reset end-to-end |
| P1 Private GitHub | Integration owner + engineer | App authorization/credential model not implemented | Create/install least-privilege GitHub App using secure settings; implement and test authorized private fixture workflow; never reuse ChatGPT connector credentials as customer integration |
| P2 Accessibility | QA | Automated checks passed previously; manual assistive technology/contrast assessment incomplete | Manual keyboard, contrast, screen-reader/device matrix |
| P2 Performance | SRE | Prior warm samples available; first public health request this session timed out at30seconds | Controlled idle cold-start and bounded load/resource evidence; distinguish proxy wait and service latency |

Full planned beta is not ready. Restricted evaluation has NOT been approved and cannot waive monitoring or recovery. Email delivery, external monitoring and public registration remain disabled. Do not switch launch scope silently.
