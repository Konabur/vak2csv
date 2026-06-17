# vak2csv

Извлечение таблицы из PDF «Перечня рецензируемых научных изданий ВАК» в **CSV** и
нормализованную **SQLite**-базу.

В PDF есть сетка таблицы (нарисована прямоугольниками/рёбрами; `lines=0`, но
`rects`/`edges` есть, и `pdfplumber.find_tables()` её находит). Тем не менее извлечение
сделано **по x-координатам слов**, а не по сетке: это устойчивее к переносам журналов
между страницами и к многострочным ячейкам, которые сливаются в одну ячейку сетки.
Колонки определяются порогами x0, строки сшиваются в записи журналов по маркеру `№`
в первой колонке.
Каждый журнал содержит список специальностей; отрасль науки берётся из **последних**
скобок специальности (учитывает вложенные скобки, напр.
`5.1.2. Публично-правовые (государственно-правовые) науки (юридические науки)`).

## Установка

С [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

Либо обычный venv + pip (без uv):

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt     # +requirements-dev.txt для запуска тестов
```

## Запуск

```bash
# по умолчанию: input/perechen-vak-29.04.2026.pdf -> output/vak.csv + output/vak.sqlite
uv run python main.py
# без uv (с активированным venv): python main.py

# параметры
uv run python main.py --pdf input/perechen-vak-29.04.2026.pdf \
    --csv output/vak.csv --db output/vak.sqlite \
    --workers 8        # процессов извлечения (по умолчанию — число CPU, 1 — последовательно)
    --max-pages 10     # ограничить страницы (отладка)
```

Все примеры ниже с `uv run python …` равнозначны `python …` в активированном venv.

Извлечение распараллелено по страницам, прогресс показывается через `tqdm`.

## Выходные данные

**CSV** — одна строка = одна специальность (long-формат), UTF-8 с BOM (открывается в Excel):

```
num, name, issn, specialty_code, specialty_title, specialty_branch, date_from, date_to
```

**SQLite** — нормализованная схема:

```sql
journals(num PRIMARY KEY, name, issn)
specialties(id, journal_num -> journals.num, code, title, branch, date_from, date_to)
-- индексы: idx_spec_code, idx_spec_journal
```

Пример запроса — все журналы по специальности `5.6.4`:

```sql
SELECT j.name FROM journals j
JOIN specialties s ON s.journal_num = j.num
WHERE s.code = '5.6.4';
```

## Проверка результата

```bash
uv run python scripts/verify_output.py
```

Печатает сводку и проверяет инварианты (непрерывность номеров, отсутствие дублей и
«сирот», совпадение числа строк CSV).

## Отбор журналов по специальностям

`scripts/match_journals.py` берёт коды специальностей и выводит журналы, у которых
есть хотя бы один из них (номер, название, ISSN, список подходящих кодов; у кода
печатается `date_to`, если задана в источнике):

```bash
uv run python scripts/match_journals.py 5.6.4 5.7.6        # точное совпадение
uv run python scripts/match_journals.py --prefix 5.6       # все 5.6.* (граница по точке)
uv run python scripts/match_journals.py 5.6.4 --out output/picked.csv
```

## Компактные представления для LLM

`scripts/compact.py` группирует плоский CSV по журналу (одна специальность на строку
→ один журнал с вложенным списком специальностей) и пишет три файла, чтобы скармливать
данные модели без повторения имени и ISSN на каждой специальности:

```bash
uv run python scripts/compact.py --csv output/vak.csv --out output/
# output/vak.compact.json  — сгруппированный JSON
# output/vak.compact.yaml  — то же, человекочитаемо
# output/vak.compact.tsv   — максимально токено-экономно
```

## Своя сборка через GitHub Actions

В репозитории есть воркфлоу `.github/workflows/build-release.yml`, который запускается
**вручную** (вкладка *Actions* → *Build VAK dataset and publish release* → *Run workflow*).
Сделайте **форк**, при необходимости задайте параметры и запустите:

- `pdf_url` — ссылка на PDF Перечня (по умолчанию — актуальный с vak.gisnauka.ru);
- `specialties` — коды через пробел для отбора журналов (пусто — без фильтра);
- `prefix_match` — трактовать коды как префиксы (`5.6` → `5.6.*`).

Воркфлоу скачивает PDF, строит CSV/SQLite и компактные представления, при наличии кодов
кладёт `output/picked.csv`, и публикует всё это в **GitHub Release** — **без самого PDF**.

## Тесты

```bash
uv run pytest
```

`tests/` содержит юнит-тесты разбора специальностей и сборки журналов, тесты записи
CSV/SQLite, проверку партиционирования и паритета параллельного извлечения с
последовательным, а также интеграционные проверки на первых страницах реального PDF
(пропускаются, если PDF отсутствует).

## Структура

```
main.py                     CLI
vak2csv/extract.py          извлечение слов одной страницы -> строки по колонкам
vak2csv/extract_parallel.py параллельное извлечение по диапазонам страниц + tqdm
vak2csv/parse.py            сшивка строк в журналы и специальности
vak2csv/write_csv.py        запись CSV (long-формат)
vak2csv/write_sqlite.py     запись нормализованной SQLite
scripts/verify_output.py    проверка целостности выходных файлов
scripts/match_journals.py   отбор журналов по кодам специальностей
scripts/compact.py          компактные представления CSV (json/yaml/tsv) для LLM
.github/workflows/          ручной воркфлоу сборки и публикации релиза
```
