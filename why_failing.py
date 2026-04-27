import json
from pathlib import Path

for f in sorted(Path('output_reports').glob('*.json')):
    d = json.load(open(f))
    dec = d['decision']
    cl  = d['claim']
    print(f"=== {cl['package_code']} | {cl['claim_id'][:45]} ===")
    print(f"  Verdict : {dec['verdict']}  score={dec['overall_score']:.1%}")
    print(f"  Passed  : {len(dec['passed_rules'])} rules -> {dec['passed_rules']}")
    print(f"  Critical: {dec['critical_failures']}")
    print(f"  Major   : {dec['major_failures']}")
    print()
