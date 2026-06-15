"""Запись журналов в CSV (одна строка = одна специальность)."""

from __future__ import annotations

import csv

from .parse import Journal

_FIELDS = [
    "num",
    "name",
    "issn",
    "specialty_code",
    "specialty_title",
    "specialty_branch",
    "date_from",
    "date_to",
]


def write_csv(journals: list[Journal], path: str) -> int:
    """Записать CSV в long-формате. Возвращает число строк (без заголовка).

    UTF-8 с BOM, чтобы Excel корректно открывал кириллицу.
    """
    n = 0
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(_FIELDS)
        for j in journals:
            if j.specialties:
                for s in j.specialties:
                    writer.writerow(
                        [j.num, j.name, j.issn or "", s.code, s.title, s.branch or "",
                         s.date_from or "", s.date_to or ""]
                    )
                    n += 1
            else:
                # Журнал без распознанных специальностей — не теряем запись.
                writer.writerow([j.num, j.name, j.issn or "", "", "", "", "", ""])
                n += 1
    return n
