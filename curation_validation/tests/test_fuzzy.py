import random

import pytest
from thefuzz import fuzz

from curation_validation.core import fuzzy
from curation_validation.core.fuzzy import ratio_matches, ratio_self_matches

WORDS = [
    "university", "institute", "college", "national", "research", "centre",
    "center", "hospital", "foundation", "of", "for", "the", "science",
    "technology", "medical", "berlin", "paris", "tokyo", "sao", "paulo",
    "société", "大学", "研究所",
]


def _random_names(rng, count):
    names = []
    for _ in range(count):
        name = " ".join(rng.choice(WORDS) for _ in range(rng.randint(1, 5)))
        if names and rng.random() < 0.4:
            # Mutate an earlier name to land near the threshold.
            base = list(rng.choice(names))
            for _ in range(rng.randint(0, 3)):
                if base:
                    base[rng.randrange(len(base))] = rng.choice("abcdeé ")
            name = "".join(base)
        names.append(name)
    return names


def _brute_force(queries, choices, threshold):
    return {
        (q, c, fuzz.ratio(queries[q], choices[c]))
        for q in range(len(queries))
        for c in range(len(choices))
        if fuzz.ratio(queries[q], choices[c]) >= threshold
    }


@pytest.mark.parametrize("seed", range(5))
def test_ratio_matches_equals_brute_force(seed):
    rng = random.Random(seed)
    queries = _random_names(rng, 60)
    choices = _random_names(rng, 150)
    assert set(ratio_matches(queries, choices, 85)) == _brute_force(queries, choices, 85)


@pytest.mark.parametrize("seed", range(5))
def test_ratio_self_matches_equals_brute_force(seed):
    rng = random.Random(seed)
    strings = list(dict.fromkeys(_random_names(rng, 200)))
    expected = {
        (i, j, score)
        for i, j, score in _brute_force(strings, strings, 85)
        if i < j
    }
    assert set(ratio_self_matches(strings, 85)) == expected


def test_small_blocks_give_same_results(monkeypatch):
    rng = random.Random(42)
    queries = _random_names(rng, 50)
    choices = _random_names(rng, 80)
    strings = list(dict.fromkeys(queries + choices))
    expected_cross = set(ratio_matches(queries, choices, 85))
    expected_self = set(ratio_self_matches(strings, 85))

    monkeypatch.setattr(fuzzy, "MAX_BLOCK_CELLS", 7)
    assert set(ratio_matches(queries, choices, 85)) == expected_cross
    assert set(ratio_self_matches(strings, 85)) == expected_self


def test_raw_score_of_84_5_rounds_below_threshold():
    # Raw ratio 338/400 = 84.5, which thefuzz rounds (half to even) to 84.
    a, b = "a" * 200, "a" * 169 + "b" * 31
    assert fuzz.ratio(a, b) == 84
    assert list(ratio_matches([a], [b], 85)) == []


def test_raw_score_of_exactly_85_matches():
    a, b = "a" * 200, "a" * 170 + "b" * 30
    assert list(ratio_matches([a], [b], 85)) == [(0, 0, 85)]


def test_empty_inputs():
    assert list(ratio_matches([], ["a"], 85)) == []
    assert list(ratio_matches(["a"], [], 85)) == []
    assert list(ratio_self_matches([], 85)) == []
    assert list(ratio_self_matches(["only"], 85)) == []


def test_identical_strings_score_100():
    assert list(ratio_matches(["same name"], ["same name"], 85)) == [(0, 0, 100)]
