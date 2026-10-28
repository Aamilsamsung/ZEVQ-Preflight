# Compare stored scan findings

Open Reports → Compare scan findings. Select two completed reports with the same source label, then select Compare findings. The picker lists the latest100 scans. Viewers and other organization members can compare reports they are authorized to read. Cross-organization references return404. In-progress and failed scans cannot be compared.

The comparison groups exact stable finding IDs into newly observed, no longer observed, changed evidence and unchanged. A changed group shows earlier/later evidence and the differing fields. Missing/duplicate identifiers appear separately and are never guessed to match. The scanner's identifiers include rule, file, location and evidence: moving code or changing evidence may produce a new identifier. This is not semantic equivalence matching.

“No longer observed” does not establish that a vulnerability or compatibility risk was fixed. Different inputs, baselines, rules, locations and coverage can explain a difference. The page warns about engine versions, incomplete coverage, different requested revision pairs and upload source identity. Uploaded reports with matching labels do not establish that the files are from the same project. Chronological order is chosen by the reviewer and not enforced.

Original reports and review decisions are not modified. Suppressions and false-positive judgments do not carry forward to another scan. Scores are prioritization indices, not failure probabilities. Download comparison JSON includes the stored evidence and source metadata; treat it as confidential project data. Downloads require the same account and organization access as the reports. Public report sharing is not enabled.

API: GET `/api/orgs/{org_id}/comparisons?baseline_id={scan_id}&proposed_id={scan_id}`. Both reports are checked server-side for membership, completion, distinct identifiers and the same source label. No additional database tables or migrations are required.

Rollback: restore application commit576fd92012851bf32b8613d2b73c81848e43125e, keeping schema0002. No customer scan or review data is altered by this feature.
