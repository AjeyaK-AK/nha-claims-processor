import pandas as pd
import json
import numpy as np
from datetime import datetime

# Read the CSV
df = pd.read_csv(r'd:\GIT\Medical\output_reports\batch_summary.csv')
df_valid = df[df['verdict'] != 'UNKNOWN'].drop_duplicates(subset=['claim_id'])

# Overall stats
total = len(df_valid)
pass_count = len(df_valid[df_valid['verdict'] == 'PASS'])
conditional_count = len(df_valid[df_valid['verdict'] == 'CONDITIONAL'])
fail_count = len(df_valid[df_valid['verdict'] == 'FAIL'])

# Average metrics
avg_confidence = df_valid['confidence'].mean()
avg_score = df_valid['score'].mean()
avg_critical = df_valid['critical_failures'].mean()
avg_major = df_valid['major_failures'].mean()
avg_minor = df_valid['minor_failures'].mean()

# Package breakdown
packages = df_valid['package_code'].unique()
package_stats = {}
for pkg in sorted(packages):
    pkg_df = df_valid[df_valid['package_code'] == pkg]
    package_stats[pkg] = {
        'total': len(pkg_df),
        'pass': len(pkg_df[pkg_df['verdict'] == 'PASS']),
        'conditional': len(pkg_df[pkg_df['verdict'] == 'CONDITIONAL']),
        'fail': len(pkg_df[pkg_df['verdict'] == 'FAIL']),
        'avg_score': pkg_df['score'].mean(),
        'avg_confidence': pkg_df['confidence'].mean()
    }

# Generate LaTeX-formatted summary table
print("\\begin{table*}[t]")
print("  \\caption{Summary of the 32-claim evaluation set across five PMJAY packages.}")
print("  \\label{tab:claims-extended}")
print("  \\small")
print("  \\begin{tabular}{@{}l|C{0.9cm}C{0.9cm}C{0.9cm}C{0.9cm}|C{1.2cm}C{1.2cm}@{}}")
print("    \\toprule")
print("    \\textbf{Package} & \\textbf{Pass} & \\textbf{Cond.} & \\textbf{Fail} & \\textbf{Total} &")
print("    \\textbf{Avg Score} & \\textbf{Avg Conf.} \\\\")
print("    \\midrule")

for pkg in sorted(package_stats.keys()):
    stats = package_stats[pkg]
    print(f"    {pkg} & {stats['pass']} & {stats['conditional']} & {stats['fail']} & {stats['total']} & "
          f"{stats['avg_score']:.3f} & {stats['avg_confidence']:.3f} \\\\")

print("    \\midrule")
print(f"    \\textbf{{Total}} & \\textbf{{{pass_count}}} & \\textbf{{{conditional_count}}} & "
      f"\\textbf{{{fail_count}}} & \\textbf{{{total}}} & \\textbf{{{avg_score:.3f}}} & "
      f"\\textbf{{{avg_confidence:.3f}}} \\\\")
print("    \\bottomrule")
print("  \\end{tabular}")
print("\\end{table*}")
print()

# Summary statistics
print("% SUMMARY STATISTICS FOR PAPER")
print(f"% Total claims evaluated: {total}")
print(f"% Pass rate: {100*pass_count/total:.1f}%")
print(f"% Conditional rate: {100*conditional_count/total:.1f}%")
print(f"% Fail rate: {100*fail_count/total:.1f}%")
print(f"% Average compliance score: {avg_score:.4f}")
print(f"% Average confidence: {avg_confidence:.4f}")
print(f"% Average critical failures per claim: {avg_critical:.2f}")
print(f"% Average major failures per claim: {avg_major:.2f}")
print()

# Write to JSON for reference
output = {
    'evaluation_date': datetime.now().isoformat(),
    'total_claims': total,
    'verdict_distribution': {
        'PASS': pass_count,
        'CONDITIONAL': conditional_count,
        'FAIL': fail_count
    },
    'percentages': {
        'pass_pct': round(100*pass_count/total, 1),
        'conditional_pct': round(100*conditional_count/total, 1),
        'fail_pct': round(100*fail_count/total, 1)
    },
    'averages': {
        'score': round(avg_score, 4),
        'confidence': round(avg_confidence, 4),
        'critical_failures': round(avg_critical, 2),
        'major_failures': round(avg_major, 2),
        'minor_failures': round(avg_minor, 2)
    },
    'package_breakdown': package_stats
}

with open(r'd:\GIT\Medical\evaluation_summary.json', 'w') as f:
    json.dump(output, f, indent=2)
    
print(f"\nEvaluation summary saved to evaluation_summary.json")
