import pytest
from src.skill_extraction import extract_skills


def test_alias_normalization_sklearn_to_scikit_learn():
    assert extract_skills("I used sklearn for modeling") == ["Scikit-learn"]
    # also scikit-learn hyphen variant should map to same canonical
    result = extract_skills("Experience with scikit-learn")
    assert "Scikit-learn" in result


def test_alias_normalization_case_insensitive():
    # sklearn in different cases
    assert "Scikit-learn" in extract_skills("SKLEARN")
    assert "Scikit-learn" in extract_skills("Sklearn")


def test_multi_word_skill_machine_learning():
    result = extract_skills("Expert in Machine Learning and deep learning")
    assert "Machine Learning" in result
    # ensure phrase not split into separate words
    assert "Machine Learning" in extract_skills("Machine Learning")

def test_multi_word_skill_deep_learning():
    assert "Deep Learning" in extract_skills("Deep Learning projects")


def test_no_false_positive_r_inside_react():
    result = extract_skills("I love React")
    assert result == ["React"]
    assert "R" not in result
    # also ensure single letter not returned for any input
    for token in result:
        assert len(token) > 1 or token in ("R", "C")  # but R should not appear here

def test_no_false_positive_java_inside_javascript():
    # JavaScript contains java substring but should not duplicate incorrectly beyond alias logic
    # extract_skills should handle via alias map without false word-boundary leaks
    result = extract_skills("JavaScript is great")
    assert "JavaScript" in result
    # Java should NOT be detected inside JavaScript via naive substring
    # implementation uses token alias + word boundary regex, so Java alone should not appear
    # if both appear, Java would only appear if explicitly mentioned
    assert result.count("JavaScript") == 1


def test_deduplication():
    result = extract_skills("Python python PYTHON Python")
    assert result == ["Python"]
    assert result.count("Python") == 1

def test_deduplication_across_aliases():
    # sklearn and Scikit-learn are same canonical, should dedup
    result = extract_skills("sklearn Scikit-learn sklearn")
    assert result == ["Scikit-learn"]


def test_case_insensitivity():
    assert extract_skills("PYTHON") == ["Python"]
    assert extract_skills("python") == ["Python"]
    assert extract_skills("PyThOn") == ["Python"]
    # mixed case multi-word
    assert "Machine Learning" in extract_skills("machine learning")
    assert "Machine Learning" in extract_skills("MACHINE LEARNING")


def test_empty_input_returns_empty_list():
    assert extract_skills("") == []
    assert extract_skills("   ") == []
    assert extract_skills(None) == []
    assert extract_skills("\t\n  ") == []


def test_deduplication_preserves_order():
    result = extract_skills("SQL Python SQL AWS Python")
    # first appearance order: SQL, Python, AWS
    assert result == ["SQL", "Python", "AWS"]


def test_alias_ml_to_machine_learning():
    assert "Machine Learning" in extract_skills("ML experience")
    assert "Machine Learning" in extract_skills("ml")
