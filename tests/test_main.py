from review_classification.main import main


def test_main_import() -> None:
    assert callable(main)
