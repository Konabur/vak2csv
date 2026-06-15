"""Тесты раскладки по колонкам и отсечки шапки."""

from vak2csv.extract import _column_of, _is_header, COL_DATE, COL_NAME, COL_NUM, COL_SPEC


def test_column_boundaries():
    assert _column_of(48) == COL_NUM
    assert _column_of(77) == COL_NAME
    assert _column_of(244) != COL_NAME  # ISSN
    assert _column_of(306) == COL_SPEC
    assert _column_of(516) == COL_DATE


def test_header_only_on_first_page_top_block():
    # Титульный блок первой страницы — шапка.
    assert _is_header(0, 100.0) is True
    assert _is_header(0, 136.0) is True
    # Данные первой страницы (ниже шапки) — не шапка.
    assert _is_header(0, 155.0) is False
    # Регрессия: журнал «Научные …» в верху любой НЕ первой страницы не должен
    # отсекаться (раньше терялся из-за совпадения со словом «Научные» в шапке).
    assert _is_header(1, 50.0) is False
    assert _is_header(500, 80.0) is False
