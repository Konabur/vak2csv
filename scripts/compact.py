"""Компактные представления output/vak.csv для подачи в LLM.

Запуск:  uv run python scripts/compact.py
         uv run python scripts/compact.py --csv output/vak.csv --out output/

Генерирует три файла из плоского CSV, группируя строки по журналу (одна
специальность на строку CSV → один журнал с вложенным списком специальностей).
Это единственное *лосслесс* сжатие: имя журнала и ISSN перестают повторяться на
каждой специальности. Название и отрасль специальности остаются inline у каждой
специальности намеренно — одна и та же специальность у разных журналов бывает с
разной отраслью (отрасль присваивается журналу, а не выводится из кода), поэтому
вынести их в общий справочник «код → название» нельзя без потери данных.

Форматы:
  vak.compact.json  — сгруппированный JSON (компактнее YAML по пунктуации)
  vak.compact.yaml  — то же, человекочитаемо (генерится без PyYAML)
  vak.compact.tsv   — максимально токено-экономно: заголовок один раз,
                      строка журнала с префиксом '@', специальности с отступом
"""

from __future__ import annotations

import argparse
import csv
import json
import os

FIELDS = ("specialty_code", "specialty_title", "specialty_branch", "date_from", "date_to")


def load_grouped(csv_path: str) -> list[dict]:
    """Читает плоский CSV и группирует строки в журналы, сохраняя порядок."""
    journals: dict[str, dict] = {}
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            num = r["num"]
            j = journals.get(num)
            if j is None:
                j = journals[num] = {
                    "num": int(num),
                    "name": r["name"],
                    "issn": r["issn"],
                    "specialties": [],
                }
            j["specialties"].append(
                {
                    "code": r["specialty_code"],
                    "title": r["specialty_title"],
                    "branch": r["specialty_branch"],
                    "from": r["date_from"],
                    "to": r["date_to"],
                }
            )
    return list(journals.values())


def write_json(journals: list[dict], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(journals, f, ensure_ascii=False, separators=(",", ":"))


def _y(value: str) -> str:
    """Строковый скаляр для YAML. json.dumps даёт валидный YAML double-quoted."""
    return json.dumps(value, ensure_ascii=False)


def write_yaml(journals: list[dict], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for j in journals:
            f.write(f"- num: {j['num']}\n")
            f.write(f"  name: {_y(j['name'])}\n")
            f.write(f"  issn: {_y(j['issn'])}\n")
            f.write("  specialties:\n")
            for s in j["specialties"]:
                f.write(f"    - code: {_y(s['code'])}\n")
                f.write(f"      title: {_y(s['title'])}\n")
                f.write(f"      branch: {_y(s['branch'])}\n")
                f.write(f"      from: {_y(s['from'])}\n")
                f.write(f"      to: {_y(s['to'])}\n")


def write_tsv(journals: list[dict], path: str) -> None:
    """Заголовок один раз; '@'-строка = журнал, отступ = специальность.

    Журнал:      @<num>\\t<name>\\t<issn>
    Специальность:  \\t<code>\\t<title>\\t<branch>\\t<from>\\t<to>
    """
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write("# @num\tname\tissn\n")
        f.write("# \tcode\ttitle\tbranch\tfrom\tto\n")
        for j in journals:
            f.write(f"@{j['num']}\t{j['name']}\t{j['issn']}\n")
            for s in j["specialties"]:
                f.write(f"\t{s['code']}\t{s['title']}\t{s['branch']}\t{s['from']}\t{s['to']}\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="Компактные представления vak.csv для LLM")
    ap.add_argument("--csv", default="output/vak.csv")
    ap.add_argument("--out", default="output/")
    args = ap.parse_args()

    journals = load_grouped(args.csv)
    n_spec = sum(len(j["specialties"]) for j in journals)

    targets = {
        "vak.compact.json": write_json,
        "vak.compact.yaml": write_yaml,
        "vak.compact.tsv": write_tsv,
    }
    src = os.path.getsize(args.csv)
    print(f"журналов: {len(journals)}   специальностей: {n_spec}")
    print(f"исходный CSV: {src/1e6:.2f} МБ")
    for fname, fn in targets.items():
        path = os.path.join(args.out, fname)
        fn(journals, path)
        sz = os.path.getsize(path)
        print(f"  {fname:18} {sz/1e6:5.2f} МБ   ({sz/src*100:4.0f}% от CSV)")


if __name__ == "__main__":
    main()
