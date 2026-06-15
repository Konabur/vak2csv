"""Юнит-тесты разбора специальностей и сборки журналов из строк."""

from vak2csv.extract import COL_DATE, COL_ISSN, COL_NAME, COL_NUM, COL_SPEC, Row
from vak2csv.parse import parse, parse_specialty


def _row(top, *, num="", name="", issn="", spec="", date="", page=0):
    cols = {}
    if num:
        cols[COL_NUM] = num
    if name:
        cols[COL_NAME] = name
    if issn:
        cols[COL_ISSN] = issn
    if spec:
        cols[COL_SPEC] = spec
    if date:
        cols[COL_DATE] = date
    return Row(page=page, top=top, cols=cols)


# --- parse_specialty -------------------------------------------------------

def test_branch_from_last_parens_with_nested():
    s = parse_specialty(
        "5.1.2.",
        "Публично-правовые (государственно-правовые) науки (юридические науки),",
        None, None,
    )
    assert s.code == "5.1.2"
    assert s.title == "Публично-правовые (государственно-правовые) науки"
    assert s.branch == "юридические науки"


def test_old_format_dash_stripped():
    s = parse_specialty(
        "17.00.04",
        "– Изобразительное и декоративно-прикладное искусство и архитектура (искусствоведение)",
        "28.12.2018", "16.10.2022",
    )
    assert s.code == "17.00.04"
    assert s.title.startswith("Изобразительное")
    assert s.branch == "искусствоведение"
    assert (s.date_from, s.date_to) == ("28.12.2018", "16.10.2022")


def test_specialty_without_parens_has_no_branch():
    s = parse_specialty("1.2.3.", "Некая специальность без отрасли", None, None)
    assert s.branch is None
    assert s.title == "Некая специальность без отрасли"


# --- parse (сборка журналов) ----------------------------------------------

def test_new_journal_on_num_marker_and_multiline_name():
    rows = [
        # Наименование многострочное; отрасль специальности в скобках — в конце (как в реальном PDF).
        _row(10, num="1.", name="Abyss (Вопросы", issn="2587-7534",
             spec="5.6.4. Этнология, антропология", date="с 28.09.2021"),
        _row(20, name="философии)", spec="и этнография (исторические науки)"),
        _row(30, num="2.", name="Другой журнал", issn="0000-0000",
             spec="1.1.1. Математика (физико-математические науки)", date="с 01.01.2020"),
    ]
    journals = parse(rows)
    assert [j.num for j in journals] == [1, 2]
    assert journals[0].name == "Abyss (Вопросы философии)"
    assert journals[0].issn == "2587-7534"
    assert len(journals[0].specialties) == 1
    assert journals[0].specialties[0].title == "Этнология, антропология и этнография"
    assert journals[0].specialties[0].branch == "исторические науки"


def test_date_to_continuation_on_separate_row():
    rows = [
        _row(10, num="2.", name="Academia", issn="2077-9038",
             spec="17.00.04 – Изобразительное искусство (искусствоведение)",
             date="с 28.12.2018"),
        _row(20, spec="и архитектура", date="по 16.10.2022"),
        _row(30, spec="2.1.1. Строительные конструкции (технические науки),",
             date="с 01.02.2022"),
    ]
    journals = parse(rows)
    specs = journals[0].specialties
    assert specs[0].code == "17.00.04"
    assert (specs[0].date_from, specs[0].date_to) == ("28.12.2018", "16.10.2022")
    # Вторая специальность получает новую активную дату без date_to.
    assert specs[1].code == "2.1.1"
    assert (specs[1].date_from, specs[1].date_to) == ("01.02.2022", None)


def test_date_applies_to_group_until_changed():
    rows = [
        _row(10, num="3.", name="J", issn="1",
             spec="3.1.1. A (медицинские науки),", date="с 01.02.2022"),
        _row(20, spec="3.1.2. B (медицинские науки),"),
        _row(30, spec="3.1.3. C (медицинские науки)"),
    ]
    journals = parse(rows)
    assert [s.date_from for s in journals[0].specialties] == ["01.02.2022"] * 3


def test_journal_without_specialties_is_kept():
    rows = [_row(10, num="5.", name="Журнал без специальностей", issn="9999-9999")]
    journals = parse(rows)
    assert len(journals) == 1
    assert journals[0].specialties == []
