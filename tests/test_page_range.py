from paper2table.page_range import parse_page_range


def test_plain_path_returns_no_range():
    path, rng = parse_page_range("some/file.pdf")
    assert path == "some/file.pdf"
    assert rng is None


def test_range_is_parsed():
    path, rng = parse_page_range("some/file.pdf:2:5")
    assert path == "some/file.pdf"
    assert rng == (2, 5)


def test_single_page_range():
    path, rng = parse_page_range("paper.pdf:3:3")
    assert path == "paper.pdf"
    assert rng == (3, 3)


def test_one_colon_suffix_is_not_a_range():
    path, rng = parse_page_range("file.pdf:5")
    assert path == "file.pdf:5"
    assert rng is None


def test_non_integer_suffix_is_not_a_range():
    path, rng = parse_page_range("file.pdf:foo:bar")
    assert path == "file.pdf:foo:bar"
    assert rng is None


def test_path_with_directory_and_range():
    path, rng = parse_page_range("/data/papers/study.pdf:10:20")
    assert path == "/data/papers/study.pdf"
    assert rng == (10, 20)


def test_path_without_extension_and_range():
    path, rng = parse_page_range("myfile:1:4")
    assert path == "myfile"
    assert rng == (1, 4)
