"""Запись журналов в нормализованную SQLite-базу."""

from __future__ import annotations

import sqlite3

from .parse import Journal

_SCHEMA = """
DROP TABLE IF EXISTS specialties;
DROP TABLE IF EXISTS journals;

CREATE TABLE journals (
    num  INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    issn TEXT
);

CREATE TABLE specialties (
    id          INTEGER PRIMARY KEY,
    journal_num INTEGER NOT NULL REFERENCES journals(num),
    code        TEXT NOT NULL,
    title       TEXT,
    branch      TEXT,
    date_from   TEXT,
    date_to     TEXT
);

CREATE INDEX idx_spec_code ON specialties(code);
CREATE INDEX idx_spec_journal ON specialties(journal_num);
"""


def write_sqlite(journals: list[Journal], path: str) -> tuple[int, int]:
    """Создать базу и записать журналы и специальности.

    Возвращает (число журналов, число специальностей).
    """
    conn = sqlite3.connect(path)
    try:
        conn.executescript(_SCHEMA)
        n_spec = 0
        with conn:
            conn.executemany(
                "INSERT INTO journals (num, name, issn) VALUES (?, ?, ?)",
                [(j.num, j.name, j.issn) for j in journals],
            )
            spec_rows = []
            for j in journals:
                for s in j.specialties:
                    spec_rows.append(
                        (j.num, s.code, s.title, s.branch, s.date_from, s.date_to)
                    )
            conn.executemany(
                "INSERT INTO specialties (journal_num, code, title, branch, date_from, date_to) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                spec_rows,
            )
            n_spec = len(spec_rows)
        return len(journals), n_spec
    finally:
        conn.close()
