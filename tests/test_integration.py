"""Интеграционный тест: разбор первых страниц реального PDF Перечня."""

import os

import pytest

from vak2csv.parse import parse_pdf

PDF = "input/perechen-vak-29.04.2026.pdf"

pytestmark = pytest.mark.skipif(not os.path.exists(PDF), reason="нет исходного PDF")


@pytest.fixture(scope="module")
def journals():
    return parse_pdf(PDF, max_pages=3)


def test_first_journals_recognized(journals):
    assert journals[0].num == 1
    assert journals[0].name.startswith("Abyss")
    assert journals[0].issn == "2587-7534"


def test_nested_parens_branch_in_real_data(journals):
    # Abyss: специальность 5.6.4 с отраслью "исторические науки".
    abyss = journals[0]
    s = next(sp for sp in abyss.specialties if sp.code == "5.6.4")
    assert s.branch == "исторические науки"
    assert s.title.startswith("Этнология")


def test_date_range_with_to(journals):
    # Academia: 17.00.04 имеет диапазон "с 28.12.2018 по 16.10.2022".
    academia = next(j for j in journals if j.name.startswith("Academia"))
    s = next(sp for sp in academia.specialties if sp.code == "17.00.04")
    assert s.date_from == "28.12.2018"
    assert s.date_to == "16.10.2022"


def test_numbers_are_monotonic(journals):
    nums = [j.num for j in journals]
    assert nums == sorted(nums)
    assert len(set(nums)) == len(nums)  # без дублей
