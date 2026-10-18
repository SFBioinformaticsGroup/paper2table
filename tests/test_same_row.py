# pyright: reportCallIssue=false
from tablemerge.tablesfile_merger import same_row
from tablevalidate.schema import Row, ValueWithAgreement


def test_same_row_scalar_rows():
    assert same_row(
        Row(family="rosaceae", scientific_name="rosa canina l."),
        Row(family="rosaceae", scientific_name="rosa canina l."),
    )


def test_not_same_row_scalar_rows():
    assert not same_row(
        Row(family="rosaceae", scientific_name="rosa canina l."),
        Row(family="rosaceae", scientific_name="rosa"),
        similarity_threshold=1.0,
    )


def test_same_row_multivalued_rows():
    assert same_row(
        Row(
            family=[ValueWithAgreement(value="rosaceae", agreement_level=2)],
            scientific_name=[
                ValueWithAgreement(value="rosa canina l.", agreement_level=2)
            ],
        ),
        Row(
            family=[ValueWithAgreement(value="rosaceae", agreement_level=2)],
            scientific_name=[
                ValueWithAgreement(value="rosa canina l.", agreement_level=2)
            ],
        ),
    )

def test_not_same_row_multivalued_rows():
    assert not same_row(
        Row(
            family=[ValueWithAgreement(value="rosaceae", agreement_level=2)],
            scientific_name=[
                ValueWithAgreement(value="rosa canina l.", agreement_level=2)
            ],
        ),
        Row(
            family=[ValueWithAgreement(value="rosaceae", agreement_level=2)],
            scientific_name=[
                ValueWithAgreement(value="rosa canina", agreement_level=2)
            ],
        ),
        similarity_threshold=1
    )



def test_same_row_left_multivalued_right_scalar():
    assert same_row(
        Row(
            family=[ValueWithAgreement(value="rosaceae", agreement_level=2)],
            scientific_name=[
                ValueWithAgreement(value="rosa canina l.", agreement_level=2)
            ],
        ),
        Row(family="rosaceae", scientific_name="rosa canina l."),
    )


def test_same_row_left_scalar_right_multivalued():
    assert same_row(
        Row(family="rosaceae", scientific_name="rosa canina l."),
        Row(
            family=[ValueWithAgreement(value="rosaceae", agreement_level=2)],
            scientific_name=[
                ValueWithAgreement(value="rosa canina l.", agreement_level=2)
            ],
        ),
    )

def test_same_row_left_scalar_right_multivalued_more_than_one_choice():
    assert same_row(
        Row(family="rosaceae", scientific_name="rosa canina l."),
        Row(
            family=[ValueWithAgreement(value="rosaceae", agreement_level=2)],
            scientific_name=[
                ValueWithAgreement(value="rosa canina l.", agreement_level=2),
            ],
        ),
        similarity_threshold=1
    )

