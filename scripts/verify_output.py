"""Проверка целостности сгенерированных output/vak.csv и output/vak.sqlite.

Запуск:  uv run python scripts/verify_output.py
         uv run python scripts/verify_output.py --db output/vak.sqlite --csv output/vak.csv

Скрипт не извлекает PDF заново — только читает готовые выходные файлы и печатает
сводку + базовые инварианты (непрерывность номеров, отсутствие дублей, примеры
запросов). Возвращает ненулевой код, если найдены явные проблемы.
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys


def verify(db_path: str, csv_path: str) -> int:
    problems: list[str] = []
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    n_j = c.execute("SELECT COUNT(*) FROM journals").fetchone()[0]
    n_s = c.execute("SELECT COUNT(*) FROM specialties").fetchone()[0]
    print(f"journals:    {n_j}")
    print(f"specialties: {n_s}")

    nums = [r[0] for r in c.execute("SELECT num FROM journals ORDER BY num")]
    if nums:
        dups = len(nums) - len(set(nums))
        gaps = sorted(set(range(nums[0], nums[-1] + 1)) - set(nums))
        print(f"num range:   {nums[0]}..{nums[-1]}  дубли={dups}  пропусков={len(gaps)}")
        if dups:
            problems.append(f"дубликаты номеров журналов: {dups}")
        if gaps:
            problems.append(f"пропуски в нумерации: {len(gaps)} (первые {gaps[:10]})")
            print(f"  первые пропуски: {gaps[:10]}")
        # Главный инвариант полноты: сквозная нумерация 1..N без потерь.
        if nums[0] != 1:
            problems.append(f"нумерация начинается не с 1, а с {nums[0]}")
        if nums[-1] != n_j:
            problems.append(f"max(num)={nums[-1]} != числа журналов {n_j} (потеря/задвоение записей)")

    # Целостность связей.
    orphans = c.execute(
        "SELECT COUNT(*) FROM specialties s "
        "LEFT JOIN journals j ON j.num = s.journal_num WHERE j.num IS NULL"
    ).fetchone()[0]
    if orphans:
        problems.append(f"специальности без журнала: {orphans}")

    # Покрытие полей.
    no_branch = c.execute("SELECT COUNT(*) FROM specialties WHERE branch IS NULL").fetchone()[0]
    with_to = c.execute("SELECT COUNT(*) FROM specialties WHERE date_to IS NOT NULL").fetchone()[0]
    no_issn = c.execute("SELECT COUNT(*) FROM journals WHERE issn IS NULL OR issn=''").fetchone()[0]
    print(f"без отрасли:  {no_branch}")
    print(f"с date_to:    {with_to}")
    print(f"без ISSN:     {no_issn}")

    # Аномалии: явные признаки того, что парсер что-то проглотил.
    empty_name = c.execute("SELECT COUNT(*) FROM journals WHERE name IS NULL OR TRIM(name)=''").fetchone()[0]
    no_spec = c.execute(
        "SELECT COUNT(*) FROM journals j "
        "WHERE NOT EXISTS (SELECT 1 FROM specialties s WHERE s.journal_num=j.num)"
    ).fetchone()[0]
    bad_code = c.execute(
        "SELECT COUNT(*) FROM specialties WHERE code IS NULL OR TRIM(code)=''"
    ).fetchone()[0]
    no_date = c.execute("SELECT COUNT(*) FROM specialties WHERE date_from IS NULL").fetchone()[0]
    print(f"пустое имя:   {empty_name}")
    print(f"0 специальн.: {no_spec}")
    print(f"пустой code:  {bad_code}")
    print(f"без date_from:{no_date}")
    if empty_name:
        problems.append(f"журналы с пустым именем: {empty_name}")
    if bad_code:
        problems.append(f"специальности с пустым кодом: {bad_code}")

    # Пример запроса по специальности.
    sample = [r[0] for r in c.execute(
        "SELECT j.name FROM journals j JOIN specialties s ON s.journal_num=j.num "
        "WHERE s.code='5.6.4' ORDER BY j.num LIMIT 3"
    )]
    print(f"журналы по 5.6.4 (первые 3): {sample}")

    conn.close()

    # CSV: число строк данных должно совпадать со sqlite-инвариантом
    # (специальности + журналы без специальностей).
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        csv_rows = sum(1 for _ in reader)
    print(f"\nCSV строк данных: {csv_rows} (заголовок: {header[:3]}...)")

    n_empty_journals = 0
    conn = sqlite3.connect(db_path)
    n_empty_journals = conn.execute(
        "SELECT COUNT(*) FROM journals j "
        "WHERE NOT EXISTS (SELECT 1 FROM specialties s WHERE s.journal_num=j.num)"
    ).fetchone()[0]
    conn.close()
    expected_csv = n_s + n_empty_journals
    if csv_rows != expected_csv:
        problems.append(f"строк в CSV {csv_rows} != ожидаемых {expected_csv}")
    else:
        print(f"CSV строк совпадает с ожидаемым ({expected_csv}). OK")

    if problems:
        print("\nПРОБЛЕМЫ:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("\nВсе проверки пройдены.")
    return 0


def show(db_path: str, num: int) -> int:
    """Вывести полную запись журнала по номеру — для ручной сверки с PDF."""
    conn = sqlite3.connect(db_path)
    j = conn.execute("SELECT num, name, issn FROM journals WHERE num=?", (num,)).fetchone()
    if not j:
        print(f"Журнал №{num} не найден.")
        return 1
    print(f"#{j[0]}  ISSN={j[2]!r}\n  {j[1]}")
    rows = conn.execute(
        "SELECT code, title, branch, date_from, date_to FROM specialties "
        "WHERE journal_num=? ORDER BY id", (num,)
    ).fetchall()
    print(f"  специальностей: {len(rows)}")
    for code, title, branch, df, dt in rows:
        dates = df + (f"..{dt}" if dt else "") if df else ""
        print(f"   {code:<10} {title}  [{branch}]  {dates}")
    conn.close()
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="Проверка выходных файлов vak2csv.")
    ap.add_argument("--db", default="output/vak.sqlite")
    ap.add_argument("--csv", default="output/vak.csv")
    ap.add_argument(
        "--show", type=int, metavar="NUM",
        help="вывести полную запись журнала №NUM для ручной сверки с PDF",
    )
    args = ap.parse_args()
    if args.show is not None:
        sys.exit(show(args.db, args.show))
    sys.exit(verify(args.db, args.csv))


if __name__ == "__main__":
    main()
