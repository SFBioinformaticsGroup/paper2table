# pyright: reportCallIssue=false
# pyright: reportArgumentType=false

import pytest

from tablemerge.fragment_transformer import (
    FilterTitleRowsTransformer,
    FragmentValuesReverser,
    LeadingRowNumberTransformer,
    NormalizePunctuationTransformer,
    SplitColumnTransformer,
)
from tablevalidate.schema import Row, TableFragment, ValueWithAgreement


class FakeVocab:
    def __init__(self, known: set[str]):
        self._known = known

    def __getitem__(self, word: str):
        return type("Lex", (), {"has_vector": word in self._known})()


class FakeNlp:
    def __init__(self, known: set[str]):
        self.vocab = FakeVocab(known)


@pytest.fixture(scope="session")
def en_spacy_model():
    import spacy

    try:
        spacy.load("en_core_web_md")
    except OSError:
        spacy.cli.download(  # pyright: ignore[reportAttributeAccessIssue]
            "en_core_web_md"
        )


def make_reverser(known: set[str]) -> FragmentValuesReverser:
    reverser = object.__new__(FragmentValuesReverser)
    reverser.language = "en"
    reverser._nlp = FakeNlp(known)  # pyright: ignore[reportAttributeAccessIssue]
    return reverser


def make_fragment(*rows: Row) -> TableFragment:
    return TableFragment(rows=list(rows), page=1)


def test_fragment_values_reverser_reverses_when_score_improves():
    reverser = make_reverser({"john", "smith", "south", "america"})
    fragment = make_fragment(Row(full_name="htims nhoj"), Row(country="acirema htuos"))
    assert reverser.transform_fragment(fragment) == make_fragment(
        Row(full_name="john smith"), Row(country="south america")
    )


def test_fragment_values_reverser_keeps_when_score_does_not_improve():
    reverser = make_reverser({"john", "smith"})
    fragment = make_fragment(Row(full_name="john smith"), Row(country="acirema htuos"))
    assert reverser.transform_fragment(fragment) == fragment


def test_fragment_values_reverser_keeps_when_scores_are_tied():
    reverser = make_reverser(set())
    fragment = make_fragment(
        Row(full_name="eaecaipa"), Row(scientific_name="imma sujam")
    )
    assert reverser.transform_fragment(fragment) == fragment


def test_fragment_values_reverser_all_or_nothing():
    reverser = make_reverser({"john", "smith", "north", "south"})
    fragment = make_fragment(Row(full_name="htims nhoj"), Row(country="north south"))
    assert reverser.transform_fragment(fragment) == fragment


def test_fragment_values_reverser_handles_none_cell_value():
    reverser = make_reverser({"john", "smith"})
    fragment = make_fragment(Row(full_name="htims nhoj", country=None))
    assert reverser.transform_fragment(fragment) == make_fragment(
        Row(full_name="john smith", country=None)
    )


def test_fragment_values_reverser_reverses_list_values():
    reverser = make_reverser({"john", "smith"})
    fragment = make_fragment(
        Row(full_name=[ValueWithAgreement(value="htims nhoj", agreement_level=2)])
    )
    assert reverser.transform_fragment(fragment) == make_fragment(
        Row(full_name=[ValueWithAgreement(value="john smith", agreement_level=2)])
    )


def test_filter_title_rows_transformer_removes_title_in_first_three_rows():
    fragment = make_fragment(
        Row(**{"0": "Figure 1. Species"}),
        Row(**{"0": "species", "1": "family"}),
        Row(**{"0": "Ammi majus", "1": "Apiaceae"}),
    )
    assert FilterTitleRowsTransformer().transform_fragment(fragment) == make_fragment(
        Row(**{"0": "species", "1": "family"}),
        Row(**{"0": "Ammi majus", "1": "Apiaceae"}),
    )


def test_filter_title_rows_transformer_keeps_title_after_first_three_rows():
    fragment = make_fragment(
        Row(**{"0": "species", "1": "family"}),
        Row(**{"0": "Ammi majus", "1": "Apiaceae"}),
        Row(**{"0": "Rosa canina", "1": "Rosaceae"}),
        Row(**{"0": "Figure 2. Continued"}),
    )
    assert FilterTitleRowsTransformer().transform_fragment(fragment) == make_fragment(
        Row(**{"0": "species", "1": "family"}),
        Row(**{"0": "Ammi majus", "1": "Apiaceae"}),
        Row(**{"0": "Rosa canina", "1": "Rosaceae"}),
        Row(**{"0": "Figure 2. Continued"}),
    )



@pytest.mark.integration
def test_fragment_values_reverser_corrects_fully_reversed_fragment(en_spacy_model):
    reverser = FragmentValuesReverser("en")
    fragment = make_fragment(Row(full_name="htimS nhoJ"), Row(country="acirema htuoS"))
    assert reverser.transform_fragment(fragment) == make_fragment(
        Row(full_name="John Smith"), Row(country="South america")
    )


@pytest.mark.integration
def test_fragment_values_reverser_keeps_natural_fragment(en_spacy_model):
    reverser = FragmentValuesReverser("en")
    fragment = make_fragment(Row(full_name="John Smith"), Row(country="South America"))
    assert reverser.transform_fragment(fragment) == fragment


@pytest.mark.integration
def test_fragment_values_reverser_keeps_fragment_with_unknown_terms(en_spacy_model):
    reverser = FragmentValuesReverser("en")
    fragment = make_fragment(Row(col_a="xkzqpwb vnrmt"), Row(col_b="qptnmrv bwpqzkx"))
    assert reverser.transform_fragment(fragment) == fragment


def test_split_column_transformer_finds_and_conjunction():
    transformer = SplitColumnTransformer("en")
    assert transformer.find_conjunction_split("city_and_country") == ("city", "country")


def test_split_column_transformer_finds_or_conjunction():
    transformer = SplitColumnTransformer("en")
    assert transformer.find_conjunction_split("city_or_country") == ("city", "country")


def test_split_column_transformer_finds_multi_token_headers():
    transformer = SplitColumnTransformer("en")
    assert transformer.find_conjunction_split("first_name_and_last_name") == ("first_name", "last_name")


def test_split_column_transformer_returns_none_when_no_conjunction():
    transformer = SplitColumnTransformer("en")
    assert transformer.find_conjunction_split("city_country") is None


def test_split_column_transformer_returns_none_conjunction_at_start():
    transformer = SplitColumnTransformer("en")
    assert transformer.find_conjunction_split("and_city_country") is None


def test_split_column_transformer_returns_none_conjunction_at_end():
    transformer = SplitColumnTransformer("en")
    assert transformer.find_conjunction_split("city_country_and") is None


def test_split_column_transformer_finds_spanish_y_conjunction():
    transformer = SplitColumnTransformer("es")
    assert transformer.find_conjunction_split("ciudad_y_pais") == ("ciudad", "pais")


def test_split_column_transformer_returns_none_unknown_language():
    transformer = SplitColumnTransformer("de")
    assert transformer.find_conjunction_split("stadt_und_land") is None



@pytest.mark.integration
def test_split_column_transformer_splits_city_and_country_values(en_spacy_model):
    transformer = SplitColumnTransformer("en")
    fragment = make_fragment(
        Row(city_and_country="Lima Peru"),
        Row(city_and_country="Santiago Chile"),
        Row(city_and_country="Caracas Venezuela"),
    )
    assert transformer.transform_fragment(fragment) == make_fragment(
        Row(city="Lima", country="Peru"),
        Row(city="Santiago", country="Chile"),
        Row(city="Caracas", country="Venezuela"),
    )


@pytest.mark.integration
def test_split_column_transformer_handles_multi_token_city(en_spacy_model):
    transformer = SplitColumnTransformer("en")
    fragment = make_fragment(Row(city_and_country="Buenos Aires Argentina"))
    assert transformer.transform_fragment(fragment) == make_fragment(
        Row(city="Buenos Aires", country="Argentina")
    )


@pytest.mark.integration
def test_split_column_transformer_handles_empty_cell(en_spacy_model):
    transformer = SplitColumnTransformer("en")
    fragment = make_fragment(Row(city_and_country=""))
    assert transformer.transform_fragment(fragment) == make_fragment(
        Row(city="", country="")
    )


@pytest.mark.integration
def test_split_column_transformer_handles_none_cell(en_spacy_model):
    transformer = SplitColumnTransformer("en")
    fragment = make_fragment(Row(city_and_country=None))
    assert transformer.transform_fragment(fragment) == make_fragment(
        Row(city=None, country=None)
    )


@pytest.mark.integration
def test_split_column_transformer_handles_list_value_cell(en_spacy_model):
    transformer = SplitColumnTransformer("en")
    fragment = make_fragment(
        Row(city_and_country=[ValueWithAgreement(value="Lima Peru", agreement_level=2)])
    )
    assert transformer.transform_fragment(fragment) == make_fragment(
        Row(
            city=[ValueWithAgreement(value="Lima", agreement_level=2)],
            country=[ValueWithAgreement(value="Peru", agreement_level=2)],
        )
    )


@pytest.mark.integration
def test_split_column_transformer_leaves_non_conjunction_columns_unchanged(en_spacy_model):
    transformer = SplitColumnTransformer("en")
    fragment = make_fragment(Row(city_and_country="Lima Peru", population="11000000"))
    assert transformer.transform_fragment(fragment) == make_fragment(
        Row(city="Lima", country="Peru", population="11000000")
    )


@pytest.mark.integration
def test_split_column_transformer_preserves_row_special_fields(en_spacy_model):
    transformer = SplitColumnTransformer("en")
    fragment = make_fragment(
        Row(city_and_country="Bogota Colombia", agreement_level_=3, sources_=["s1"], row_=5)
    )
    assert transformer.transform_fragment(fragment) == make_fragment(
        Row(city="Bogota", country="Colombia", agreement_level_=3, sources_=["s1"], row_=5)
    )


@pytest.mark.integration
def test_split_column_transformer_returns_unchanged_when_no_conjunction_columns(en_spacy_model):
    transformer = SplitColumnTransformer("en")
    fragment = make_fragment(Row(city="Lima", country="Peru"))
    assert transformer.transform_fragment(fragment) == fragment


@pytest.mark.integration
def test_split_column_transformer_strips_parentheses_around_full_part(en_spacy_model):
    transformer = SplitColumnTransformer("en")
    fragment = make_fragment(Row(city_and_country="Buenos Aires (Argentina)"))
    assert transformer.transform_fragment(fragment) == make_fragment(
        Row(city="Buenos Aires", country="Argentina")
    )


@pytest.mark.integration
def test_split_column_transformer_strips_dash_separator(en_spacy_model):
    transformer = SplitColumnTransformer("en")
    fragment = make_fragment(Row(city_and_country="Buenos Aires - Argentina"))
    assert transformer.transform_fragment(fragment) == make_fragment(
        Row(city="Buenos Aires", country="Argentina")
    )


@pytest.mark.integration
def test_split_column_transformer_preserves_parentheses_within_part(en_spacy_model):
    transformer = SplitColumnTransformer("en")
    fragment = make_fragment(Row(city_and_country="(Ciudad de) La Paz - Bolivia"))
    assert transformer.transform_fragment(fragment) == make_fragment(
        Row(city="(Ciudad de) La Paz", country="Bolivia")
    )


def test_normalize_punctuation_converts_dash_variants():
    transformer = NormalizePunctuationTransformer()
    fragment = make_fragment(Row(period="2010–2020", range="5—7"))
    assert transformer.transform_fragment(fragment) == make_fragment(
        Row(period="2010-2020", range="5-7")
    )


def test_normalize_punctuation_removes_guillemets():
    transformer = NormalizePunctuationTransformer()
    fragment = make_fragment(Row(species="«Homo sapiens»", note="‹present›"))
    assert transformer.transform_fragment(fragment) == make_fragment(
        Row(species="Homo sapiens", note="present")
    )


def test_normalize_punctuation_converts_typographic_double_quotes_to_single():
    transformer = NormalizePunctuationTransformer()
    fragment = make_fragment(Row(value="“positive”"))
    assert transformer.transform_fragment(fragment) == make_fragment(
        Row(value="'positive'")
    )


def test_normalize_punctuation_converts_straight_double_quotes_to_single():
    transformer = NormalizePunctuationTransformer()
    fragment = make_fragment(Row(value='"yes"'))
    assert transformer.transform_fragment(fragment) == make_fragment(
        Row(value="'yes'")
    )


def test_normalize_punctuation_normalizes_typographic_apostrophe():
    transformer = NormalizePunctuationTransformer()
    fragment = make_fragment(Row(note="don’t", opening="L‘Hopital"))
    assert transformer.transform_fragment(fragment) == make_fragment(
        Row(note="don't", opening="L'Hopital")
    )


def test_normalize_punctuation_converts_ellipsis():
    transformer = NormalizePunctuationTransformer()
    fragment = make_fragment(Row(note="see below…"))
    assert transformer.transform_fragment(fragment) == make_fragment(
        Row(note="see below...")
    )


def test_normalize_punctuation_removes_trailing_dot_after_long_word():
    transformer = NormalizePunctuationTransformer()
    fragment = make_fragment(
        Row(species="Homo sapiens.", location="North America.")
    )
    assert transformer.transform_fragment(fragment) == make_fragment(
        Row(species="Homo sapiens", location="North America")
    )


def test_normalize_punctuation_keeps_trailing_dot_after_short_word():
    transformer = NormalizePunctuationTransformer()
    fragment = make_fragment(
        Row(citation="et al.", figure="Fig.", taxon="spp.", rank="sp.")
    )
    assert transformer.transform_fragment(fragment) == make_fragment(
        Row(citation="et al.", figure="Fig.", taxon="spp.", rank="sp.")
    )


def test_normalize_punctuation_handles_none_value():
    transformer = NormalizePunctuationTransformer()
    fragment = make_fragment(Row(species="Homo sapiens.", note=None))
    assert transformer.transform_fragment(fragment) == make_fragment(
        Row(species="Homo sapiens", note=None)
    )


def test_normalize_punctuation_transforms_list_values():
    transformer = NormalizePunctuationTransformer()
    fragment = make_fragment(
        Row(species=[
            ValueWithAgreement(value="Homo sapiens.", agreement_level=2),
            ValueWithAgreement(value="“positive”", agreement_level=1),
        ])
    )
    assert transformer.transform_fragment(fragment) == make_fragment(
        Row(species=[
            ValueWithAgreement(value="Homo sapiens", agreement_level=2),
            ValueWithAgreement(value="'positive'", agreement_level=1),
        ])
    )


def test_normalize_punctuation_preserves_row_special_fields():
    transformer = NormalizePunctuationTransformer()
    fragment = make_fragment(
        Row(species="Homo sapiens.", agreement_level_=3, sources_=["s1"], row_=5)
    )
    assert transformer.transform_fragment(fragment) == make_fragment(
        Row(species="Homo sapiens", agreement_level_=3, sources_=["s1"], row_=5)
    )


