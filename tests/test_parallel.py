"""Тесты параллельного извлечения."""

import os

import pytest

from vak2csv.extract import extract_rows
from vak2csv.extract_parallel import _chunks, _worker, extract_rows_parallel

PDF = "input/perechen-vak-29.04.2026.pdf"


def test_chunks_partition_is_contiguous_and_complete():
    ranges = _chunks(0, 10, 4)
    assert ranges[0][0] == 0
    assert ranges[-1][1] == 10
    # непрерывность: конец предыдущего = начало следующего
    for (a_lo, a_hi), (b_lo, b_hi) in zip(ranges, ranges[1:]):
        assert a_hi == b_lo
    # покрытие всех страниц без пропусков
    covered = [i for lo, hi in ranges for i in range(lo, hi)]
    assert covered == list(range(10))


def test_chunks_handles_more_workers_than_pages():
    ranges = _chunks(0, 3, 8)
    assert sum(hi - lo for lo, hi in ranges) == 3


@pytest.mark.skipif(not os.path.exists(PDF), reason="нет исходного PDF")
def test_parallel_matches_sequential():
    seq = extract_rows(PDF, max_pages=6)
    par = extract_rows_parallel(PDF, max_pages=6, workers=4, chunk_size=2)
    assert [(r.page, r.top, r.cols) for r in seq] == [(r.page, r.top, r.cols) for r in par]


@pytest.mark.skipif(not os.path.exists(PDF), reason="нет исходного PDF")
def test_worker_reports_page_count():
    rows, n_pages = _worker((PDF, 0, 3))
    assert n_pages == 3
    assert all(0 <= r.page < 3 for r in rows)
