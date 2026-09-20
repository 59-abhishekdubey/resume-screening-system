from pipeline import build_candidate_result, generate_explanation

# Self-check: generate_explanation contrived cases

# Case (a): perfect match + high similarity
result_a = generate_explanation({
    "matched_skills": ["Python", "SQL"],
    "missing_skills": [],
    "additional_skills": [],
    "similarity": 0.9,
})
print('Case (a) perfect match + high similarity:', repr(result_a))
assert "Strong required-skill coverage" in result_a
assert "High similarity to job description" in result_a

# Case (b): zero match + low similarity
result_b = generate_explanation({
    "matched_skills": [],
    "missing_skills": ["Python", "SQL"],
    "additional_skills": [],
    "similarity": 0.1,
})
print('Case (b) zero match + low similarity:', repr(result_b))
assert "Insufficient signal to explain ranking" in result_b

# Case (c): partial match + moderate similarity
result_c = generate_explanation({
    "matched_skills": ["Python"],
    "missing_skills": ["SQL"],
    "additional_skills": [],
    "similarity": 0.5,
})
print('Case (c) partial match + moderate similarity:', repr(result_c))
assert "Moderate similarity to job description" in result_c
assert "Missing: SQL" in result_c

# Determinism check: running twice gives identical output
result_c1 = generate_explanation({
    "matched_skills": ["Python"],
    "missing_skills": ["SQL"],
    "additional_skills": [],
    "similarity": 0.5,
})
result_c2 = generate_explanation({
    "matched_skills": ["Python"],
    "missing_skills": ["SQL"],
    "additional_skills": [],
    "similarity": 0.5,
})
assert result_c1 == result_c2, f"Expected identical, got {result_c1!r} vs {result_c2!r}"
print('Determinism check : OK')

# No matched, no missing, moderate similarity (should NOT trigger fallback since missing is non-empty)
result_d = generate_explanation({
    "matched_skills": [],
    "missing_skills": [],
    "additional_skills": [],
    "similarity": 0.5,
})
print('Case (d) no matched no missing moderate similarity:', repr(result_d))

# No matched, no missing, low similarity (should trigger fallback)
result_e = generate_explanation({
    "matched_skills": [],
    "missing_skills": [],
    "additional_skills": [],
    "similarity": 0.1,
})
print('Case (e) no matched no missing low similarity:', repr(result_e))
assert "Insufficient signal to explain ranking" in result_e

print('All pipeline self-checks passed!')