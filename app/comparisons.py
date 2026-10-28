"""Deterministic comparison of stored findings, not a prediction of deployment safety."""


def compare_results(baseline, proposed):
    warnings=[]
    if baseline.get('engine_version') != proposed.get('engine_version'):
        warnings.append('Analysis engine versions differ; detection changes may explain differences.')
    for name,result in [('Baseline',baseline),('Proposed',proposed)]:
        coverage=result.get('coverage') or {}
        if any(coverage.get(k) for k in ('skipped','baseline_skipped','comparison_unknown_files','files_without_language_analysis')):
            warnings.append(name+' coverage is incomplete or includes unsupported files. Inspect its original report.')
        if coverage.get('route_removal_checks_complete') is False:
            warnings.append(name+' route removal checks were incomplete.')
    def index(result):
        groups={};unmatched=[]
        for f in result.get('findings',[]):
            fid=f.get('id')
            if not isinstance(fid,str) or not fid:unmatched.append(f);continue
            groups.setdefault(fid,[]).append(f)
        indexed={}
        for fid,values in groups.items():
            if len(values)==1:indexed[fid]=values[0]
            else:unmatched.extend(values)
        return indexed,unmatched
    before,old_unknown=index(baseline);after,new_unknown=index(proposed)
    ambiguous={f['id'] for f in old_unknown+new_unknown if isinstance(f.get('id'),str) and f['id']}
    # Never pair an ambiguous identifier with a unique finding from the other report.
    for fid in ambiguous:
        if fid in before:old_unknown.append(before.pop(fid))
        if fid in after:new_unknown.append(after.pop(fid))
    added=[after[k] for k in sorted(after.keys()-before.keys())]
    absent=[before[k] for k in sorted(before.keys()-after.keys())]
    changed=[];unchanged=[]
    for fid in sorted(before.keys() & after.keys()):
        old,new=before[fid],after[fid]
        if old==new:unchanged.append(new)
        else:
            fields=sorted(k for k in old.keys()|new.keys() if old.get(k)!=new.get(k) or (k in old)!=(k in new))
            changed.append({'id':fid,'baseline':old,'proposed':new,'changed_fields':fields})
    if old_unknown or new_unknown:warnings.append('Missing or duplicate finding identifiers cannot be matched reliably; they are listed separately.')
    return {'counts':{'added':len(added),'not_observed':len(absent),'changed':len(changed),'unchanged':len(unchanged),'unmatched_baseline':len(old_unknown),'unmatched_proposed':len(new_unknown)},
            'added':added,'not_observed':absent,'changed':changed,'unchanged':unchanged,
            'unmatched_baseline':old_unknown,'unmatched_proposed':new_unknown,'warnings':warnings,
            'limitations':'Matches exact stable finding IDs only. Not observed does not mean fixed. Different inputs, rules, coverage or baselines can change results. Review decisions are per-scan and are not carried forward. Scores are prioritization indices, not failure probabilities.'}
