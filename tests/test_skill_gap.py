from skill_gap import compute_gap, coverage_ratio

# Self-check 1: compute_gap
result = compute_gap(['Python', 'SQL'], ['Python', 'SQL', 'AWS'])
print('compute_gap test:', result)
assert result['missing'] == ['AWS'], f"Expected ['AWS'], got {result['missing']}"

# Self-check 2: coverage_ratio empty required
assert coverage_ratio([], []) == 0.0, 'coverage_ratio([], []) should be 0.0'
print('coverage_ratio([], []) : OK')

# Self-check 3: coverage_ratio with empty required but non-empty matched
assert coverage_ratio(['Python'], []) == 0.0, 'coverage_ratio(["Python"], []) should be 0.0'
print('coverage_ratio(["Python"], []) : OK')

# Self-check 4: coverage_ratio normal case
assert coverage_ratio(['Python'], ['Python', 'SQL']) == 0.5, 'should be 0.5'
print('coverage_ratio normal : OK')

# Test dedup
result2 = compute_gap(['Python', 'Python', 'SQL'], ['Python', 'SQL', 'AWS'])
print('compute_gap dedup test:', result2)
assert result2['matched'] == ['Python', 'SQL']

print('All skill_gap self-checks passed!')