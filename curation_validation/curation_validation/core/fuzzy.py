"""Bulk fuzzy matching that reports exactly the scores of thefuzz.fuzz.ratio.

rapidfuzz's cdist compares every query against every choice in native code across
all cores. Its float32 scores serve only as a prefilter, one point below the
threshold, and each surviving pair is rescored with thefuzz, so reported scores
and threshold decisions are identical to calling fuzz.ratio pair by pair.
"""
from collections.abc import Iterator, Sequence

import numpy as np
from rapidfuzz import fuzz as rapid_fuzz
from rapidfuzz import process
from thefuzz import fuzz

# Upper bound on cells per cdist block (float32), about 64 MB.
MAX_BLOCK_CELLS = 1 << 24


def _scan(
    queries: Sequence[str],
    choices: Sequence[str],
    threshold: int,
    upper_triangle: bool,
) -> Iterator[tuple[int, int, int]]:
    if not queries or not choices:
        return
    rows_per_block = max(1, MAX_BLOCK_CELLS // len(choices))
    for start in range(0, len(queries), rows_per_block):
        stop = min(start + rows_per_block, len(queries))
        col_offset = start if upper_triangle else 0
        scores = process.cdist(
            queries[start:stop],
            choices[col_offset:],
            scorer=rapid_fuzz.ratio,
            processor=None,
            score_cutoff=threshold - 1,
            workers=-1,
        )
        for row, col in zip(*np.nonzero(scores)):
            query_index = start + int(row)
            choice_index = col_offset + int(col)
            if upper_triangle and choice_index <= query_index:
                continue
            score = fuzz.ratio(queries[query_index], choices[choice_index])
            if score >= threshold:
                yield query_index, choice_index, score


def ratio_matches(
    queries: Sequence[str],
    choices: Sequence[str],
    threshold: int,
) -> Iterator[tuple[int, int, int]]:
    """Yield (query_index, choice_index, score) for each pair scoring >= threshold."""
    return _scan(queries, choices, threshold, upper_triangle=False)


def ratio_self_matches(
    strings: Sequence[str],
    threshold: int,
) -> Iterator[tuple[int, int, int]]:
    """Yield (i, j, score) with i < j for each pair of strings scoring >= threshold."""
    return _scan(strings, strings, threshold, upper_triangle=True)
