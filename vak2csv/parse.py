"""Сборка строк таблицы в записи журналов со списком специальностей."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .extract import COL_DATE, COL_ISSN, COL_NAME, COL_NUM, COL_SPEC, Row, extract_rows

# Маркер начала новой записи в колонке № (например "1." или "275.").
_NUM_RE = re.compile(r"^(\d+)\.$")

# Код специальности: новый формат "5.6.4." либо старый "17.00.04" (часто с " – ").
_CODE_RE = re.compile(r"^(\d+\.\d+\.\d+\.|\d{2}\.\d{2}\.\d{2})")

# Дата: "с DD.MM.YYYY" и опционально "по DD.MM.YYYY".
_DATE_RE = re.compile(
    r"с\s+(\d{2}\.\d{2}\.\d{4})(?:\s+по\s+(\d{2}\.\d{2}\.\d{4}))?"
)
# Хвост "по DD.MM.YYYY" может переноситься на отдельную строку.
_DATE_TO_RE = re.compile(r"по\s+(\d{2}\.\d{2}\.\d{4})")

# Последняя скобочная группа в тексте специальности — отрасль науки.
_LAST_PAREN_RE = re.compile(r"\(([^()]*)\)\s*$")


@dataclass
class Specialty:
    code: str
    title: str
    branch: str | None
    date_from: str | None
    date_to: str | None


@dataclass
class Journal:
    num: int
    name: str
    issn: str | None
    specialties: list[Specialty] = field(default_factory=list)


def parse_specialty(code: str, body: str, date_from: str | None, date_to: str | None) -> Specialty:
    """Разобрать одну специальность: наименование + отрасль из последних скобок."""
    text = body.strip()
    # Старый формат: после кода идёт тире.
    text = re.sub(r"^[–—-]\s*", "", text)
    text = text.rstrip().rstrip(",;").strip()

    branch: str | None = None
    m = _LAST_PAREN_RE.search(text)
    if m:
        branch = m.group(1).strip()
        title = text[: m.start()].strip()
    else:
        title = text
    title = title.rstrip(",;.").strip()
    return Specialty(
        code=code.rstrip("."),
        title=title,
        branch=branch,
        date_from=date_from,
        date_to=date_to,
    )


def _flush_specialty(buf: list[str], code: str, date: tuple[str | None, str | None]) -> Specialty:
    return parse_specialty(code, " ".join(buf), date[0], date[1])


def parse(rows: list[Row]) -> list[Journal]:
    """Сшить строки в записи журналов."""
    journals: list[Journal] = []

    cur: Journal | None = None
    name_parts: list[str] = []
    issn_parts: list[str] = []
    # текущая специальность
    spec_code: str | None = None
    spec_buf: list[str] = []
    spec_date: tuple[str | None, str | None] = (None, None)
    # дата, активная для следующих специальностей (применяется до смены)
    active_date: tuple[str | None, str | None] = (None, None)

    def finish_spec() -> None:
        nonlocal spec_code, spec_buf
        if cur is not None and spec_code is not None:
            cur.specialties.append(_flush_specialty(spec_buf, spec_code, spec_date))
        spec_code, spec_buf = None, []

    def finish_journal() -> None:
        nonlocal cur, name_parts, issn_parts, active_date
        finish_spec()
        if cur is not None:
            cur.name = " ".join(name_parts).strip()
            cur.issn = " ".join(issn_parts).strip() or None
            journals.append(cur)
        cur = None
        name_parts, issn_parts = [], []
        active_date = (None, None)

    for row in rows:
        num_text = row.col(COL_NUM).strip()
        m_num = _NUM_RE.match(num_text)
        if m_num:
            finish_journal()
            cur = Journal(num=int(m_num.group(1)), name="", issn=None)

        if cur is None:
            # Строки до первой записи (не должно случаться после отсечки шапки).
            continue

        # Дата на этом уровне обновляет активную дату (до обработки кода специальности).
        date_text = row.col(COL_DATE).strip()
        if date_text:
            md = _DATE_RE.search(date_text)
            if md:
                active_date = (md.group(1), md.group(2))
            else:
                # Перенос хвоста "по DD.MM.YYYY" на отдельную строку.
                mto = _DATE_TO_RE.search(date_text)
                if mto:
                    active_date = (active_date[0], mto.group(1))
                    # Дополнить уже открытую специальность того же блока.
                    if spec_code is not None and spec_date[1] is None:
                        spec_date = (spec_date[0], mto.group(1))

        name_text = row.col(COL_NAME).strip()
        if name_text:
            name_parts.append(name_text)

        issn_text = row.col(COL_ISSN).strip()
        if issn_text:
            issn_parts.append(issn_text)

        spec_text = row.col(COL_SPEC).strip()
        if spec_text:
            m_code = _CODE_RE.match(spec_text)
            if m_code:
                finish_spec()
                spec_code = m_code.group(1)
                spec_date = active_date
                rest = spec_text[m_code.end():]
                spec_buf = [rest] if rest.strip() else []
            elif spec_code is not None:
                spec_buf.append(spec_text)

    finish_journal()
    return journals


def parse_pdf(
    pdf_path: str,
    *,
    max_pages: int | None = None,
    workers: int | None = 1,
    progress: bool = False,
) -> list[Journal]:
    """Разобрать PDF в список журналов.

    workers=1 → последовательно; иначе параллельное извлечение по процессам
    (workers=None → число CPU). progress=True показывает прогресс-бар.
    """
    if workers == 1:
        rows = extract_rows(pdf_path, max_pages=max_pages)
    else:
        from .extract_parallel import extract_rows_parallel

        rows = extract_rows_parallel(
            pdf_path, max_pages=max_pages, workers=workers, progress=progress
        )
    return parse(rows)
