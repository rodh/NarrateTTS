from app.extractor import _extract_og_image

def test_extracts_og_image():
    html = '<html><head><meta property="og:image" content="https://x.com/a.jpg"></head></html>'
    assert _extract_og_image(html, "https://x.com/post") == "https://x.com/a.jpg"

def test_falls_back_to_twitter_image():
    html = '<meta name="twitter:image" content="/rel/b.png">'
    assert _extract_og_image(html, "https://x.com/post") == "https://x.com/rel/b.png"

def test_returns_none_when_absent():
    assert _extract_og_image("<html><head></head></html>", "https://x.com/post") is None
