"""Testes do parser de intervalos de páginas."""

from __future__ import annotations

import pytest

from pdftoolkit.core.errors import PageRangeError
from pdftoolkit.core.ranges import parse_page_ranges


def test_single_pages():
    assert parse_page_ranges("1,3,5", 5) == [0, 2, 4]


def test_inclusive_range():
    assert parse_page_ranges("2-4", 5) == [1, 2, 3]


def test_open_ended_start_and_end():
    assert parse_page_ranges("3-", 5) == [2, 3, 4]
    assert parse_page_ranges("-2", 5) == [0, 1]


def test_reversed_range():
    assert parse_page_ranges("4-2", 5) == [3, 2, 1]


def test_order_preserved():
    assert parse_page_ranges("3,1", 5) == [2, 0]


def test_unique_keeps_first_occurrence():
    assert parse_page_ranges("1,1,2,1", 5, unique=True) == [0, 1]


@pytest.mark.parametrize("spec", ["", "0", "6", "abc", "1,,2", "1-x"])
def test_invalid_specs(spec):
    with pytest.raises(PageRangeError):
        parse_page_ranges(spec, 5)


def test_out_of_bounds():
    with pytest.raises(PageRangeError):
        parse_page_ranges("10", 5)
