"""Testes das operações estruturais: merge, split, pages, rotate, crop."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pdftoolkit.core.errors import InvalidInputError
from pdftoolkit.core.io import PdfInput
from pdftoolkit.core.registry import get_operation
from pdftoolkit.engines import pypdf_engine as pe


def _run(name, datas, **params):
    op = get_operation(name)
    inputs = [PdfInput(data) for data in datas]
    return op.execute(inputs, op.params_model(**params))


def test_merge_concatenates(pdf5, pdf3):
    result = _run("merge", [pdf5, pdf3])
    assert pe.count_pages(result.single.data) == 8
    assert result.meta["pages"] == 8


def test_merge_requires_two(pdf5):
    with pytest.raises(InvalidInputError):
        _run("merge", [pdf5])


def test_split_every_two(pdf5):
    result = _run("split", [pdf5], every=2)
    assert len(result.artifacts) == 3
    counts = [pe.count_pages(a.data) for a in result.artifacts]
    assert counts == [2, 2, 1]


def test_split_by_ranges(pdf5):
    result = _run("split", [pdf5], ranges=["1-2", "3-5"])
    counts = [pe.count_pages(a.data) for a in result.artifacts]
    assert counts == [2, 3]


def test_remove_pages(pdf5):
    result = _run("remove-pages", [pdf5], pages="2,4")
    assert pe.count_pages(result.single.data) == 3


def test_remove_all_fails(pdf5):
    with pytest.raises(InvalidInputError):
        _run("remove-pages", [pdf5], pages="1-5")


def test_extract_pages_order(pdf5):
    result = _run("extract-pages", [pdf5], pages="5,1")
    assert pe.count_pages(result.single.data) == 2


def test_reorder_requires_permutation(pdf5):
    assert pe.count_pages(_run("reorder-pages", [pdf5], order="5,4,3,2,1").single.data) == 5
    with pytest.raises(InvalidInputError):
        _run("reorder-pages", [pdf5], order="1,2,3")


def test_rotate_subset(pdf5):
    result = _run("rotate", [pdf5], degrees=90, pages="1-2")
    assert pe.count_pages(result.single.data) == 5


def test_rotate_invalid_degrees(pdf5):
    with pytest.raises(ValidationError):
        _run("rotate", [pdf5], degrees=45)


def test_crop(pdf5):
    result = _run("crop", [pdf5], left=50, bottom=50, right=400, top=700)
    assert pe.count_pages(result.single.data) == 5


def test_crop_invalid_box(pdf5):
    with pytest.raises(ValidationError):
        _run("crop", [pdf5], left=400, bottom=50, right=100, top=700)
