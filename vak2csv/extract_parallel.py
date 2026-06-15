"""Параллельное извлечение строк из PDF по диапазонам страниц.

Каждый воркер-процесс открывает PDF самостоятельно (объекты pdfplumber не
сериализуются) и обрабатывает свой непрерывный диапазон страниц. Результаты
собираются строго в порядке страниц, поэтому журналы, переходящие со страницы
на страницу, разбираются так же корректно, как при последовательном проходе.
"""

from __future__ import annotations

import math
import os
from multiprocessing import Pool

import pdfplumber
from tqdm import tqdm

from .extract import Row, rows_from_page

# Размер чанка страниц на одну задачу. Мельче чанки → плавнее прогресс-бар,
# но больше повторных открытий PDF. ~16 страниц — разумный компромисс.
DEFAULT_CHUNK_SIZE = 16


def _page_count(pdf_path: str) -> int:
    with pdfplumber.open(pdf_path) as pdf:
        return len(pdf.pages)


def _chunks(start: int, stop: int, n: int) -> list[tuple[int, int]]:
    """Разбить [start, stop) на n примерно равных непрерывных диапазонов."""
    total = stop - start
    if total <= 0:
        return []
    n = max(1, min(n, total))
    size, rem = divmod(total, n)
    ranges: list[tuple[int, int]] = []
    cur = start
    for i in range(n):
        length = size + (1 if i < rem else 0)
        ranges.append((cur, cur + length))
        cur += length
    return ranges


def _worker(task: tuple[str, int, int]) -> tuple[list[Row], int]:
    pdf_path, lo, hi = task
    rows: list[Row] = []
    with pdfplumber.open(pdf_path) as pdf:
        for idx in range(lo, hi):
            rows.extend(rows_from_page(pdf.pages[idx], idx))
    return rows, hi - lo


def extract_rows_parallel(
    pdf_path: str,
    *,
    max_pages: int | None = None,
    workers: int | None = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    progress: bool = False,
) -> list[Row]:
    """Извлечь строки таблицы из PDF параллельно по процессам.

    workers=None → число CPU. progress=True показывает tqdm-бар по страницам.
    Результат отсортирован по (page, top).
    """
    total = _page_count(pdf_path)
    stop = total if max_pages is None else min(total, max_pages)
    workers = workers or os.cpu_count() or 1

    n_chunks = max(1, math.ceil(stop / max(1, chunk_size)))
    ranges = _chunks(0, stop, n_chunks)
    tasks = [(pdf_path, lo, hi) for lo, hi in ranges]

    rows: list[Row] = []
    bar = tqdm(total=stop, unit="стр", disable=not progress, desc="Извлечение")
    with Pool(processes=min(workers, len(tasks))) as pool:
        for part, n_pages in pool.imap_unordered(_worker, tasks):
            rows.extend(part)
            bar.update(n_pages)
    bar.close()

    # Чанки приходят не по порядку (imap_unordered) — сортируем по (page, top).
    rows.sort(key=lambda r: (r.page, r.top))
    return rows
