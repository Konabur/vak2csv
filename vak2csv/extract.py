"""Извлечение слов из PDF Перечня ВАК и раскладка по колонкам.

PDF не содержит линий таблицы, поэтому колонки определяются по x-координате
левого края слова (x0). Границы проверены на странице 1 формата A4 и стабильны
на всём документе.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pdfplumber

# Границы колонок по x0 (left edge слова). См. design-документ.
COL_NUM = 0  # № п/п
COL_NAME = 1  # Наименование издания
COL_ISSN = 2  # ISSN
COL_SPEC = 3  # Научные специальности и отрасли науки
COL_DATE = 4  # Дата включения в Перечень

# Пороги x0: слово попадает в колонку, если x0 < соответствующего верхнего порога.
_X_BOUNDS = [70, 240, 305, 508]  # < 70 -> 0, < 240 -> 1, < 305 -> 2, < 508 -> 3, иначе 4

# Титульный блок с шапкой таблицы есть ТОЛЬКО на первой странице (проверено: слова
# «ПЕРЕЧЕНЬ»/«Наименование»/«присуждаются» встречаются на весь документ по 1 разу).
# На остальных страницах таблица продолжается без шапки. Поэтому отсекаем шапку строго
# по позиции на странице 0, а не по ключевым словам (иначе журналы с названием
# «Научные …» терялись бы, т.к. в шапке есть слово «Научные специальности»).
_HEADER_PAGE = 0
_HEADER_BOTTOM = 150.0  # последняя строка шапки top≈136, первая запись «Abyss» top≈155


@dataclass
class Row:
    """Одна визуальная строка таблицы: тексты по колонкам на одном уровне top."""

    page: int
    top: float
    cols: dict[int, str] = field(default_factory=dict)

    def col(self, idx: int) -> str:
        return self.cols.get(idx, "")


def _column_of(x0: float) -> int:
    for col, bound in enumerate(_X_BOUNDS):
        if x0 < bound:
            return col
    return COL_DATE


def _is_header(page_idx: int, top: float) -> bool:
    """Шапка таблицы — только титульный блок на первой странице."""
    return page_idx == _HEADER_PAGE and top < _HEADER_BOTTOM


def rows_from_page(page, page_idx: int) -> list[Row]:
    """Извлечь строки таблицы из одной страницы pdfplumber.

    Слова группируются в строки по округлённому top; внутри строки — по колонкам.
    Заголовочная зона первой страницы отбрасывается по позиции.
    """
    words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
    by_top: dict[int, list[dict]] = {}
    for w in words:
        by_top.setdefault(round(w["top"]), []).append(w)

    rows: list[Row] = []
    for top in sorted(by_top):
        if _is_header(page_idx, float(top)):
            continue
        line_words = sorted(by_top[top], key=lambda w: w["x0"])
        cols: dict[int, list[str]] = {}
        for w in line_words:
            cols.setdefault(_column_of(w["x0"]), []).append(w["text"])
        joined = {c: " ".join(parts) for c, parts in cols.items()}
        if not joined:
            continue
        rows.append(Row(page=page_idx, top=float(top), cols=joined))
    return rows


def extract_rows(pdf_path: str, *, max_pages: int | None = None) -> list[Row]:
    """Прочитать PDF последовательно и вернуть строки таблицы в порядке чтения.

    Для параллельного извлечения см. vak2csv.extract_parallel.
    """
    rows: list[Row] = []
    with pdfplumber.open(pdf_path) as pdf:
        pages = pdf.pages if max_pages is None else pdf.pages[:max_pages]
        for page_idx, page in enumerate(pages):
            rows.extend(rows_from_page(page, page_idx))
    return rows
