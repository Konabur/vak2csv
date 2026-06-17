"""Подбор журналов из output/vak.csv по нужным кодам специальностей.

Запуск:
  uv run python scripts/match_journals.py 5.6.4 5.7.6
  uv run python scripts/match_journals.py --prefix 5.6           # все 5.6.*
  uv run python scripts/match_journals.py 5.6.4 --out output/picked.csv

На вход — один или несколько кодов специальностей. На выход — журналы, у
которых есть хотя бы один из этих кодов: номер, название, ISSN и список
подходящих кодов; у кода печатается date_to, если она задана в источнике.

По умолчанию совпадение точное (код к коду). С флагом --prefix код трактуется
как префикс: '5.6' подходит к 5.6.1, 5.6.4 и т.д. (граница по точке, чтобы
'5.6' не цеплял '5.6.40' лишнего — сверяется посегментно).
"""

from __future__ import annotations

import argparse
import csv
import sys


def _matches(code: str, wanted: list[str], prefix: bool) -> str | None:
    """Возвращает совпавший запрошенный код (для отчёта) или None."""
    code = code.rstrip(".")
    for w in wanted:
        w = w.rstrip(".")
        if code == w:
            return w
        if prefix and (code == w or code.startswith(w + ".")):
            return w
    return None


def pick(csv_path: str, wanted: list[str], prefix: bool) -> list[dict]:
    """Группирует подходящие специальности по журналам, сохраняя порядок CSV."""
    journals: dict[str, dict] = {}
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            hit = _matches(r["specialty_code"], wanted, prefix)
            if hit is None:
                continue
            num = r["num"]
            j = journals.get(num)
            if j is None:
                j = journals[num] = {
                    "num": int(num),
                    "name": r["name"],
                    "issn": r["issn"],
                    "codes": [],
                }
            j["codes"].append(
                {
                    "code": r["specialty_code"].rstrip("."),
                    "matched": hit,
                    "date_to": r["date_to"].strip(),
                }
            )
    return sorted(journals.values(), key=lambda j: j["num"])


def print_report(journals: list[dict], wanted: list[str]) -> None:
    print(f"Запрошенные коды: {', '.join(wanted)}")
    print(f"Подходящих журналов: {len(journals)}\n")
    for j in journals:
        print(f"{j['num']:>4}  {j['name']}  [{j['issn']}]")
        for c in j["codes"]:
            tail = f"  (до {c['date_to']})" if c["date_to"] else ""
            print(f"        {c['code']}{tail}")


def _codes_cell(codes: list[dict]) -> str:
    """Подходящие коды в одну ячейку; у кода с date_to — пометка '(до ...)'."""
    parts = []
    for c in codes:
        parts.append(f"{c['code']} (до {c['date_to']})" if c["date_to"] else c["code"])
    return "; ".join(parts)


def write_csv(journals: list[dict], path: str) -> None:
    """Один журнал — одна строка. С BOM — для Excel."""
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["num", "name", "issn", "specialty_codes"])
        for j in journals:
            w.writerow([j["num"], j["name"], j["issn"], _codes_cell(j["codes"])])


def main() -> None:
    ap = argparse.ArgumentParser(description="Подбор журналов ВАК по кодам специальностей")
    ap.add_argument("codes", nargs="+", help="коды специальностей, напр. 5.6.4 5.7.6")
    ap.add_argument("--csv", default="output/vak.csv", help="исходный CSV")
    ap.add_argument("--prefix", action="store_true", help="код как префикс (5.6 -> 5.6.*)")
    ap.add_argument("--out", help="записать результат в CSV по этому пути")
    args = ap.parse_args()

    journals = pick(args.csv, args.codes, args.prefix)
    if not journals:
        print("Ничего не найдено по этим кодам.", file=sys.stderr)
        sys.exit(1)

    print_report(journals, args.codes)
    if args.out:
        write_csv(journals, args.out)
        print(f"\nЗаписано: {args.out}")


if __name__ == "__main__":
    main()
