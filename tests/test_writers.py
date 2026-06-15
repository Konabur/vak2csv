"""Юнит-тесты записи CSV и SQLite."""

import csv
import sqlite3

from vak2csv.parse import Journal, Specialty
from vak2csv.write_csv import write_csv
from vak2csv.write_sqlite import write_sqlite


def _sample():
    return [
        Journal(
            num=1, name="Abyss", issn="2587-7534",
            specialties=[
                Specialty("5.6.4", "Этнология", "исторические науки", "28.09.2021", None),
                Specialty("5.7.6", "Философия науки", "философские науки", "28.09.2021", None),
            ],
        ),
        Journal(num=2, name="Пустой журнал", issn=None, specialties=[]),
    ]


def test_csv_long_format_and_bom(tmp_path):
    path = tmp_path / "vak.csv"
    n = write_csv(_sample(), str(path))
    assert n == 3  # 2 специальности + 1 журнал без специальностей

    raw = path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM для Excel

    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["num"] == "1"
    assert rows[0]["specialty_code"] == "5.6.4"
    assert rows[0]["specialty_branch"] == "исторические науки"
    # Журнал без специальностей — одна строка с пустыми полями специальности.
    assert rows[2]["num"] == "2"
    assert rows[2]["specialty_code"] == ""


def test_sqlite_normalized_and_queryable(tmp_path):
    path = tmp_path / "vak.sqlite"
    n_j, n_s = write_sqlite(_sample(), str(path))
    assert (n_j, n_s) == (2, 2)

    conn = sqlite3.connect(path)
    try:
        names = conn.execute(
            "SELECT j.name FROM journals j JOIN specialties s ON s.journal_num = j.num "
            "WHERE s.code = '5.6.4'"
        ).fetchall()
        assert names == [("Abyss",)]
        assert conn.execute("SELECT COUNT(*) FROM journals").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM specialties").fetchone()[0] == 2
    finally:
        conn.close()


def test_sqlite_rewrite_is_idempotent(tmp_path):
    path = tmp_path / "vak.sqlite"
    write_sqlite(_sample(), str(path))
    write_sqlite(_sample(), str(path))  # повторный прогон не должен падать/дублировать
    conn = sqlite3.connect(path)
    try:
        assert conn.execute("SELECT COUNT(*) FROM journals").fetchone()[0] == 2
    finally:
        conn.close()
