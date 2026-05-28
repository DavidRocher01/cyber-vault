import json

with open('coverage/coverage-final.json') as f:
    cov = json.load(f)

rows = []
for path, data in cov.items():
    rel = path.replace('\\', '/').split('src/app/')[-1]
    stmts = data['s']
    total = len(stmts)
    covered = sum(1 for v in stmts.values() if v > 0)
    pct = (covered / total * 100) if total else 100
    uncovered = total - covered
    rows.append((pct, uncovered, rel))

rows.sort()
print(f"{'File':<65} {'%':>5} {'uncov':>6}")
print('-' * 80)
for pct, uncov, rel in rows[:50]:
    print(f"{rel:<65} {pct:>5.0f} {uncov:>6}")

total_stmts = sum(len(d['s']) for d in cov.values())
total_cov = sum(sum(1 for v in d['s'].values() if v > 0) for d in cov.values())
print(f"\nOverall: {total_cov}/{total_stmts} = {total_cov/total_stmts*100:.1f}%")
