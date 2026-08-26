from tablevalidate.schema import Row
from utils.convergence import convergent_row_ids


def test_convergent_row_ids_all_unique():
    rows = [Row(species="Ammi majus", row_=1), Row(species="Carum carvi", row_=2)]
    assert convergent_row_ids(rows) == frozenset({1, 2})


def test_convergent_row_ids_duplicate_excluded():
    rows = [Row(species="Ammi majus", row_=1), Row(species="Carum carvi", row_=1)]
    assert convergent_row_ids(rows) == frozenset()


def test_convergent_row_ids_none_row_id_excluded():
    rows = [Row(species="Ammi majus"), Row(species="Carum carvi")]
    assert convergent_row_ids(rows) == frozenset()


def test_convergent_row_ids_mixed():
    rows = [
        Row(species="Ammi majus", row_=1),
        Row(species="Carum carvi", row_=1),
        Row(species="Zea mays", row_=2),
    ]
    assert convergent_row_ids(rows) == frozenset({2})


def test_convergent_row_ids_empty_list():
    assert convergent_row_ids([]) == frozenset()
