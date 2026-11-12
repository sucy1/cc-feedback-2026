"""Tests for submit-button overrides and image buttons in form submission."""

import sys

import bs4
import pytest
import requests_mock
import setpath  # noqa:F401, must come before 'import mechanicalsoup'

import mechanicalsoup


def make_form(html):
    return bs4.BeautifulSoup(html, "lxml").form


# --- formaction ------------------------------------------------------------

@pytest.mark.parametrize("submit_html", [
    pytest.param(
        '<input type="submit" name="go" value="Send" formaction="/override">',
        id="input-submit"),
    pytest.param(
        '<button name="go" value="Send" formaction="/override">Send</button>',
        id="button"),
])
def test_formaction_overrides_form_action(submit_html):
    """A selected submit element overrides the form action.

    Relative formaction values are resolved against the page URL.
    """
    form = make_form(
        f'<form method="post" action="/submit">{submit_html}</form>')
    submit = form.find(["input", "button"])

    request_kwargs = mechanicalsoup.Browser.get_request_kwargs(
        form, "http://e.com/page", submit)

    assert request_kwargs["url"] == "http://e.com/override"


def test_formaction_without_override_keeps_form_action():
    form = make_form(
        '<form method="post" action="/submit">'
        '<input type="submit" name="go" value="Send"></form>')
    submit = form.input

    request_kwargs = mechanicalsoup.Browser.get_request_kwargs(
        form, "http://e.com/page", submit)

    assert request_kwargs["url"] == "http://e.com/submit"


# --- formmethod ------------------------------------------------------------

@pytest.mark.parametrize("submit_html", [
    pytest.param(
        '<input type="submit" name="go" value="Send" formmethod="get">',
        id="input-submit"),
    pytest.param(
        '<button name="go" value="Send" formmethod="get">Send</button>',
        id="button"),
])
def test_formmethod_override_to_get_uses_params(submit_html):
    """formmethod=get on either submit kind wins over the form method."""
    form = make_form(
        '<form method="post" action="/submit">'
        '<input name="t" value="1">'
        f'{submit_html}</form>')
    submit = form.find(["input", "button"], {"name": "go"})

    request_kwargs = mechanicalsoup.Browser.get_request_kwargs(
        form, "http://e.com/page", submit)

    assert request_kwargs["method"] == "get"
    assert request_kwargs["params"] == [("t", "1"), ("go", "Send")]
    assert "data" not in request_kwargs


@pytest.mark.parametrize("submit_html", [
    pytest.param(
        '<input type="submit" name="go" value="Send" formmethod="post">',
        id="input-submit"),
    pytest.param(
        '<button name="go" value="Send" formmethod="post">Send</button>',
        id="button"),
])
def test_formmethod_override_to_post_uses_data(submit_html):
    """formmethod=post on either submit kind wins over the form method."""
    form = make_form(
        '<form method="get" action="/submit">'
        '<input name="t" value="1">'
        f'{submit_html}</form>')
    submit = form.find(["input", "button"], {"name": "go"})

    request_kwargs = mechanicalsoup.Browser.get_request_kwargs(
        form, "http://e.com/page", submit)

    assert request_kwargs["method"] == "post"
    assert request_kwargs["data"] == [("t", "1"), ("go", "Send")]
    assert "params" not in request_kwargs


# --- image buttons ---------------------------------------------------------

image_button_form = '''
<form method="post" action="/submit">
  <input name="t" value="1">
  <input type="image" name="img" src="i.png">
</form>
'''


def test_choose_image_button_by_name():
    soup = bs4.BeautifulSoup(image_button_form, "lxml")
    form = mechanicalsoup.Form(soup.form)

    chosen = form.choose_submit("img")

    assert chosen is not None
    assert chosen.get("name") == "img"
    assert chosen.get("type") == "image"
    assert form.submit_chosen is chosen


def test_choose_image_button_by_tag():
    soup = bs4.BeautifulSoup(image_button_form, "lxml")
    form = mechanicalsoup.Form(soup.form)
    image = soup.form.find("input", {"name": "img"})

    assert form.choose_submit(image) is image


def test_image_button_submits_coordinates():
    """An selected image button sends <name>.x and <name>.y, not its value."""
    soup = bs4.BeautifulSoup(image_button_form, "lxml")
    form = soup.form
    image = form.find("input", {"name": "img"})

    request_kwargs = mechanicalsoup.Browser.get_request_kwargs(
        form, "http://e.com/page", image)

    assert request_kwargs["data"] == [
        ("t", "1"),
        ("img.x", "0"),
        ("img.y", "0"),
    ]
    assert all(name != "img" for name, value in request_kwargs["data"])


def test_unselected_image_button_is_not_submitted():
    """No coordinates (and no bare value) when the image button is not used."""
    soup = bs4.BeautifulSoup(image_button_form, "lxml")
    form = soup.form

    request_kwargs = mechanicalsoup.Browser.get_request_kwargs(
        form, "http://e.com/page", False)

    assert request_kwargs["data"] == [("t", "1")]
    assert all(not name.startswith("img") for name, value in
               request_kwargs["data"])


def test_choose_submit_defaults_to_image_button():
    soup = bs4.BeautifulSoup(
        '<form action="/submit"><input type="image" name="img"></form>',
        "lxml")
    form = mechanicalsoup.Form(soup.form)

    assert form.choose_submit(None).get("name") == "img"


# --- formenctype -----------------------------------------------------------

@pytest.mark.parametrize("submit_html", [
    pytest.param(
        '<input type="submit" name="go" value="Send" '
        'formenctype="multipart/form-data">',
        id="input-submit"),
    pytest.param(
        '<button name="go" value="Send" '
        'formenctype="multipart/form-data">Send</button>',
        id="button"),
])
def test_formenctype_multipart_request_kwargs(submit_html):
    """formenctype overrides the form enctype, switching on multipart."""
    form = make_form(
        '<form method="post" action="/submit">'
        '<input name="t" value="1">'
        f'{submit_html}</form>')
    submit = form.find(["input", "button"], {"name": "go"})

    request_kwargs = mechanicalsoup.Browser.get_request_kwargs(
        form, "http://e.com/page", submit)

    assert request_kwargs["data"] == [("t", "1"), ("go", "Send")]
    # A truthy (though empty) files dict makes Requests use multipart.
    assert request_kwargs["files"] == {}
    assert bool(request_kwargs["files"]) is True


def test_formenctype_multipart_is_sent_as_multipart():
    """End-to-end: the request Content-Type becomes multipart/form-data."""
    html = '''
    <form method="post" action="mock://form.com/post">
      <input name="t" value="1">
      <button name="go" value="Send"
              formenctype="multipart/form-data">Send</button>
    </form>
    '''
    mock = requests_mock.Adapter()
    browser = mechanicalsoup.StatefulBrowser(
        requests_adapters={"mock": mock})
    mock.register_uri("GET", "mock://form.com", text=html,
                      headers={"Content-Type": "text/html"})
    mock.register_uri("POST", "mock://form.com/post", text="Success!")

    browser.open("mock://form.com")
    browser.select_form()
    response = browser.submit_selected()

    assert response.text == "Success!"
    content_type = mock.last_request.headers["Content-Type"]
    assert content_type.startswith("multipart/form-data")


# --- behaviour that must not regress --------------------------------------

def test_skipped_controls_stay_skipped():
    """Disabled, unchecked and unnamed controls are still not submitted."""
    form = make_form('''
    <form method="post" action="/submit">
      <input name="ok" value="1">
      <input name="disabled" value="2" disabled>
      <fieldset disabled>
        <legend><input name="in_legend" value="3"></legend>
        <input name="in_fieldset" value="4">
        <fieldset><input name="in_nested_fieldset" value="5"></fieldset>
      </fieldset>
      <input type="checkbox" name="unchecked_checkbox" value="yes">
      <input type="radio" name="unchecked_radio" value="yes">
      <input value="no-name">
    </form>
    ''')

    request_kwargs = mechanicalsoup.Browser.get_request_kwargs(
        form, "http://e.com/page", False)

    assert request_kwargs["data"] == [("ok", "1"), ("in_legend", "3")]


def test_duplicate_names_keep_page_order():
    form = make_form(
        '<form method="post" action="/submit">'
        '<input name="x" value="1">'
        '<input name="x" value="2">'
        '<input name="x" value="3">'
        '</form>')

    request_kwargs = mechanicalsoup.Browser.get_request_kwargs(
        form, "http://e.com/page", False)

    assert request_kwargs["data"] == [
        ("x", "1"), ("x", "2"), ("x", "3"),
    ]


def test_empty_action_falls_back_to_page_url():
    form = make_form(
        '<form method="post">'
        '<input name="x" value="1">'
        '</form>')

    request_kwargs = mechanicalsoup.Browser.get_request_kwargs(
        form, "http://e.com/page", False)

    assert request_kwargs["url"] == "http://e.com/page"


if __name__ == '__main__':
    pytest.main(sys.argv)
