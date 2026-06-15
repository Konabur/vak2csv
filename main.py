"""CLI: извлечение таблицы Перечня ВАК из PDF в CSV и SQLite."""

from __future__ import annotations

import argparse

from vak2csv.parse import parse_pdf
from vak2csv.write_csv import write_csv
from vak2csv.write_sqlite import write_sqlite

DEFAULT_PDF = "input/perechen-vak-29.04.2026.pdf"
DEFAULT_CSV = "output/vak.csv"
DEFAULT_DB = "output/vak.sqlite"


def main() -> None:
    ap = argparse.ArgumentParser(description="Извлечь таблицу Перечня ВАК в CSV и SQLite.")
    ap.add_argument("--pdf", default=DEFAULT_PDF, help="путь к PDF Перечня")
    ap.add_argument("--csv", default=DEFAULT_CSV, help="путь к выходному CSV")
    ap.add_argument("--db", default=DEFAULT_DB, help="путь к выходной SQLite-базе")
    ap.add_argument("--max-pages", type=int, default=None, help="ограничить число страниц (отладка)")
    ap.add_argument(
        "--workers", type=int, default=None,
        help="число процессов для извлечения (по умолчанию — число CPU; 1 — последовательно)",
    )
    args = ap.parse_args()

    print(f"Читаю {args.pdf} ...")
    journals = parse_pdf(
        args.pdf, max_pages=args.max_pages, workers=args.workers, progress=True
    )
    n_spec_total = sum(len(j.specialties) for j in journals)
    print(f"Распознано журналов: {len(journals)}, специальностей: {n_spec_total}")

    rows = write_csv(journals, args.csv)
    print(f"CSV записан: {args.csv} ({rows} строк)")

    n_j, n_s = write_sqlite(journals, args.db)
    print(f"SQLite записан: {args.db} (journals={n_j}, specialties={n_s})")


if __name__ == "__main__":
    main()
