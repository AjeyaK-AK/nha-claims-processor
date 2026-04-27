import pandas as pd
import json
import numpy as np
from pathlib import Path

df = pd.read_csv(r'd:\GIT\Medical\output_reports\batch_summary.csv')
df_valid = df[df['verdict'] != 'UNKNOWN'].drop_duplicates(subset=['claim_id'])

print('='*60)
print('RESULTS SUMMARY FOR Q1 JOURNAL PAPER')
print('='*60)
print(f'Total valid results: {len(df_valid)}')
print(f'  - PASS:        {len(df_valid[df_valid["verdict"] == "PASS"])}')
print(f'  - CONDITIONAL: {len(df_valid[df_valid["verdict"] == "CONDITIONAL"])}')
print(f'  - FAIL:        {len(df_valid[df_valid["verdict"] == "FAIL"])}')
print()
print(f'Average confidence: {df_valid["confidence"].mean():.4f}')
print(f'Average score:      {df_valid["score"].mean():.4f}')
print()

# Package breakdown
print('Package breakdown:')
for pkg in df_valid['package_code'].unique():
    pkg_df = df_valid[df_valid['package_code'] == pkg]
    print(f'  {pkg}: {len(pkg_df)} claims')
    print(f'    - PASS: {len(pkg_df[pkg_df["verdict"] == "PASS"])}')
    print(f'    - FAIL: {len(pkg_df[pkg_df["verdict"] == "FAIL"])}')

print()
print('Failure analysis:')
print(f'Avg critical failures: {df_valid["critical_failures"].mean():.2f}')
print(f'Avg major failures:    {df_valid["major_failures"].mean():.2f}')
print(f'Avg minor failures:    {df_valid["minor_failures"].mean():.2f}')
