# pyright: reportCallIssue=false

from tablevalidate.schema import Row, ValueWithAgreement


def test_normalize_str_value_no_data_lowercase():
    assert Row.normalize_value("no data") == ""


def test_normalize_str_value_no_data_uppercase():
    assert Row.normalize_value("No Data") == ""


def test_normalize_str_value_no_data_extra_whitespace():
    assert Row.normalize_value("  no  data  ") == ""


def test_normalize_str_value_none():
    assert Row.normalize_value("None") == ""


def test_normalize_str_preserves_case():
    assert Row.normalize_value("Perez et al. 2020") == "perez et al. 2020"


def test_normalize_str_collapses_whitespace():
    assert Row.normalize_value("Perez  et   al.") == "perez et al."


def test_normalize_str_strips_edges():
    assert Row.normalize_value("  Perez 2020  ") == "perez 2020"


def test_normalize_str_en_dash():
    assert Row.normalize_value("Perez–Vílchez 2020") == "perez-vílchez 2020"


def test_normalize_str_em_dash():
    assert Row.normalize_value("Perez—Vílchez 2020") == "perez-vílchez 2020"


def test_normalize_str_value_regular_value():
    assert Row.normalize_value("Apiaceae") == "apiaceae"


def test_normalize_str_value_en_dash():
    assert Row.normalize_value("2–5") == "2-5"


def test_normalize_str_value_em_dash():
    assert Row.normalize_value("Jan—Feb") == "jan-feb"


def test_normalize_str_value_figure_dash():
    assert Row.normalize_value("10‒20") == "10-20"


def test_normalize_str_value_horizontal_bar():
    assert Row.normalize_value("A―B") == "a-b"


def test_normalize_str_value_minus_sign():
    assert Row.normalize_value("−5") == "-5"


def test_normalize_str_value_hyphen_variants():
    assert Row.normalize_value("A‐B") == "a-b"
    assert Row.normalize_value("A‑B") == "a-b"


def test_normalize_str_removes_replacement_character():
    assert Row.normalize_value("hello�world") == "helloworld"


def test_normalize_str_removes_control_characters():
    assert Row.normalize_value("hello\x00world\x1fend") == "helloworldend"


def test_normalize_str_value_removes_replacement_character():
    assert Row.normalize_value("Apiaceae�") == "apiaceae"


def test_normalize_str_cid_latin1_accented():
    assert Row.normalize_value("(cid:237)") == "í"


def test_normalize_str_cid_latin1_in_word():
    assert Row.normalize_value("L(cid:243)pez") == "lópez"


def test_normalize_str_cid_outside_latin1_range():
    assert Row.normalize_value("(cid:42)") == ""


def test_normalize_str_cid_outside_latin1_range_with_surrounding_text():
    assert Row.normalize_value("hello (cid:7) world") == "hello world"


def test_is_empty_value_no_data_string():
    assert Row.is_empty_value("no data")


def test_is_empty_value_no_data_uppercase():
    assert Row.is_empty_value("No Data")


def test_is_empty_value_none():
    assert Row.is_empty_value(None)


def test_is_empty_value_empty_string():
    assert Row.is_empty_value("")


def test_is_empty_value_whitespace_string():
    assert Row.is_empty_value("  \t\n")


def test_is_empty_value_non_empty_string():
    assert not Row.is_empty_value("hello")


def test_is_empty_row_all_empty():
    assert Row(family="", scientific_name=None).is_empty()


def test_is_empty_row_whitespace_only():
    assert Row(family="  ", scientific_name="\t").is_empty()


def test_is_empty_row_metadata_keys_ignored():
    assert Row(family="", agreement_level_=2, sources_=["uuid"]).is_empty()


def test_is_empty_row_has_data():
    assert not Row(family="Apiaceae", scientific_name="").is_empty()


def test_is_empty_row_list_value_empty():
    assert Row(family=[ValueWithAgreement(value="", agreement_level=1)]).is_empty()


def test_is_empty_row_list_value_non_empty():
    assert not Row(
        family=[ValueWithAgreement(value="Apiaceae", agreement_level=1)]
    ).is_empty()
