from backend.tools.query_classifier import needs_search


def test_definitional_question_skips_search():
    assert needs_search("What is the capital of France?") is False


def test_how_to_question_skips_search():
    assert needs_search("How to bake a chocolate cake") is False


def test_weather_question_needs_search():
    assert needs_search("What's the weather today in Paris?") is True


def test_news_question_needs_search():
    assert needs_search("Latest news on AI regulation") is True


def test_recent_year_needs_search():
    assert needs_search("Who won the election in 2026") is True


def test_stock_question_needs_search():
    assert needs_search("How is Tesla stock performing right now") is True
