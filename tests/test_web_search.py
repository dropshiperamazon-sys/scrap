from scraper.web_search import _looks_blocked


def test_looks_blocked_flags_short_genuine_captcha_page():
    text = "Our systems have detected unusual traffic from your computer network. Please verify you are a human."
    assert _looks_blocked(text) is True


def test_looks_blocked_ignores_long_results_page_that_merely_mentions_the_word():
    # A normal results page can be thousands of characters and still contain
    # one of the phrases once (e.g. quoting a site's own bot-check snippet)
    # without Google having actually blocked the request.
    filler = "Example Furniture Co. Chicago IL. Shop our collection. " * 40
    text = filler + " This site is protected by reCAPTCHA and the Google Privacy Policy apply."
    assert len(text) > 1500
    assert _looks_blocked(text) is False


def test_looks_blocked_false_for_normal_short_text():
    assert _looks_blocked("Example Furniture - Contact us at info@example.com") is False
