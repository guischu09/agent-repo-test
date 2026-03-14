import os
import re


def read_index_html():
    """Read the index.html file."""
    path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(path, "r") as f:
        return f.read()


def test_index_html_exists():
    path = os.path.join(os.path.dirname(__file__), "index.html")
    assert os.path.exists(path), "index.html should exist"


def test_has_doctype():
    html = read_index_html()
    assert html.strip().startswith("<!DOCTYPE html>"), "Should start with DOCTYPE"


def test_has_title():
    html = read_index_html()
    assert "<title>Click Counter</title>" in html, "Should have a page title"


def test_has_click_button():
    html = read_index_html()
    assert 'id="click-btn"' in html, "Should have a click button with id click-btn"
    assert "Click me!" in html, "Button should have 'Click me!' text"


def test_has_click_count_display():
    html = read_index_html()
    assert 'id="click-count"' in html, "Should have a click count display"
    assert ">0<" in html, "Initial count should be 0"


def test_has_reset_button():
    html = read_index_html()
    assert 'id="reset-btn"' in html, "Should have a reset button"
    assert "Reset" in html, "Reset button should have 'Reset' text"


def test_has_click_event_listener():
    html = read_index_html()
    assert "addEventListener" in html, "Should use addEventListener for click handling"
    assert 'click-btn' in html, "Should reference click-btn in JavaScript"


def test_counter_increment_logic():
    html = read_index_html()
    assert "count++" in html, "Should increment counter on click"
    assert "countDisplay.textContent" in html or "countDisplay.innerText" in html, \
        "Should update display text"


def test_reset_logic():
    html = read_index_html()
    assert "count = 0" in html, "Reset should set count back to 0"


def test_has_viewport_meta():
    html = read_index_html()
    assert "viewport" in html, "Should have a viewport meta tag for responsiveness"


def test_has_styles():
    html = read_index_html()
    assert "<style>" in html, "Should have embedded styles"


def test_valid_html_structure():
    html = read_index_html()
    assert "<html" in html, "Should have html tag"
    assert "<head>" in html, "Should have head tag"
    assert "<body>" in html, "Should have body tag"
    assert "</html>" in html, "Should have closing html tag"
    assert "</head>" in html, "Should have closing head tag"
    assert "</body>" in html, "Should have closing body tag"


def test_script_tag_present():
    html = read_index_html()
    assert "<script>" in html, "Should have a script tag"
    assert "</script>" in html, "Should have closing script tag"


def test_let_count_variable():
    html = read_index_html()
    assert re.search(r'let\s+count\s*=\s*0', html), \
        "Should declare count variable initialized to 0"
