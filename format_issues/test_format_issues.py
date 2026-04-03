import pytest
from format_issues import remove_hallucinated_ror_ids


class TestRemoveHallucinatedRorIds:
    def test_removes_hallucinated_ror_id_with_relationship_type(self):
        original = "Related organizations: University of Oxford (parent)"
        formatted = "Related organizations: https://ror.org/052gg0110 (parent)"
        result = remove_hallucinated_ror_ids(original, formatted)
        assert "https://ror.org/052gg0110" not in result

    def test_preserves_original_ror_id_unchanged(self):
        original = "Related organizations: https://ror.org/02mhbdp94 (parent)"
        formatted = "Related organizations: https://ror.org/02mhbdp94 (parent)"
        result = remove_hallucinated_ror_ids(original, formatted)
        assert result == formatted

    def test_preserves_multiple_original_ror_ids(self):
        original = "Related organizations: https://ror.org/02mhbdp94 (parent) https://ror.org/05gq02987 (child)"
        formatted = "Related organizations: https://ror.org/02mhbdp94 (parent) https://ror.org/05gq02987 (child)"
        result = remove_hallucinated_ror_ids(original, formatted)
        assert result == formatted

    def test_no_ror_ids_returns_unchanged(self):
        original = "Name of organization: Foo University"
        formatted = "Name of organization: Foo University*en"
        result = remove_hallucinated_ror_ids(original, formatted)
        assert result == formatted

    def test_removes_hallucinated_but_keeps_original_with_formatting(self):
        original = "Related organizations: https://ror.org/02mhbdp94 (parent)\nSome University (child)"
        formatted = "Related organizations: https://ror.org/02mhbdp94 (parent) https://ror.org/0fake1d99 (child)"
        result = remove_hallucinated_ror_ids(original, formatted)
        assert "https://ror.org/02mhbdp94 (parent)" in result
        assert "https://ror.org/0fake1d99" not in result

    def test_removes_multiple_hallucinated_ids(self):
        original = "Related organizations: Org A (parent) Org B (child)"
        formatted = "Related organizations: https://ror.org/0aaaaaa00 (parent) https://ror.org/0bbbbbb11 (child)"
        result = remove_hallucinated_ror_ids(original, formatted)
        assert "https://ror.org/0aaaaaa00" not in result
        assert "https://ror.org/0bbbbbb11" not in result

    def test_removes_bare_hallucinated_id_without_relationship_type(self):
        original = "Some field: no ror ids here"
        formatted = "Some field: https://ror.org/0aaaaaa00"
        result = remove_hallucinated_ror_ids(original, formatted)
        assert "https://ror.org/0aaaaaa00" not in result
