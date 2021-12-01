import json
import logging
from string import Template

import pytest

from lib import ALT, SRC, add_badge, write_nb

html_badge_tmpl = Template(
    "<!--<badge>-->"
    '<a href="https://colab.research.google.com/github/usr/repo/blob/main/$nb" target="_parent">'
    '<img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>'
    "<!--</badge>-->"
)
badge_tmpl = Template(
    "[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)]"
    "(https://colab.research.google.com/github/usr/repo/blob/main/$nb)"
)
drive_badge_tmpl = Template(
    "[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)]"
    "(https://colab.research.google.com/drive/$nb)"
)


@pytest.fixture
def min_notebook():
    """Minimal notebook."""
    return {"metadata": {}, "cells": [], "nbformat": 4, "nbformat_minor": 5}


@pytest.fixture
def make_tmp_nb(tmp_path, min_notebook):
    """tmp notebook."""

    def _make_tmp_nb(fname):
        nb = min_notebook
        file_path = (tmp_path / fname).with_suffix(".ipynb")
        write_nb(data=nb, file_path=file_path)
        return file_path

    return _make_tmp_nb


def test_write_nb(tmp_path, min_notebook):
    nb = min_notebook
    fname = "min_nb.ipynb"
    file_path = tmp_path / fname

    write_nb(data=nb, file_path=file_path)

    assert (tmp_path / fname).is_file()
    assert len([*tmp_path.iterdir()]) == 1

    with file_path.open() as f:
        nb2 = json.load(f)

    for k in nb2:
        assert nb2[k] == nb[k]


@pytest.mark.parametrize(
    "line, file_path, expected",
    [
        ("", "nb.ipynb", None),
        ("badge", "nb.ipynb", None),
        ("{badge}", "nb.ipynb", None),
        ("{ badge }", "nb.ipynb", None),
        ("{{badge}}", "nb.ipynb", html_badge_tmpl.substitute(nb="nb.ipynb")),
        ("{{  badge}}", "nb.ipynb", html_badge_tmpl.substitute(nb="nb.ipynb")),
        ("{{badge  }}", "nb.ipynb", html_badge_tmpl.substitute(nb="nb.ipynb")),
        ("{{ badge }}", "nb.ipynb", html_badge_tmpl.substitute(nb="nb.ipynb")),
        (
            "{{ badge }}{{ badge }}",
            "nb.ipynb",
            html_badge_tmpl.substitute(nb="nb.ipynb") + html_badge_tmpl.substitute(nb="nb.ipynb"),
        ),
        (
            "{{ badge }} {{ badge }}",
            "nb2.ipynb",
            html_badge_tmpl.substitute(nb="nb2.ipynb") + " " + html_badge_tmpl.substitute(nb="nb2.ipynb"),
        ),
    ],
)
def test_nb_add_self_html_badge(line, file_path, expected):
    track = True
    badge = add_badge(line, None, "usr/repo", "main", file_path, SRC, ALT, "notebook", track)
    assert badge == expected


@pytest.mark.parametrize(
    "line, file_path, expected",
    [
        ("", "nb.ipynb", None),
        ("badge", "nb.ipynb", None),
        ("{badge}", "nb.ipynb", None),
        ("{{badge}}", "nb.ipynb", badge_tmpl.substitute(nb="nb.ipynb")),
        ("{{ badge }}", "nb.ipynb", badge_tmpl.substitute(nb="nb.ipynb")),
        (
            "{{ badge }}{{ badge }}",
            "nb.ipynb",
            badge_tmpl.substitute(nb="nb.ipynb") + badge_tmpl.substitute(nb="nb.ipynb"),
        ),
        (
            "{{ badge }} {{ badge }}",
            "nb.ipynb",
            badge_tmpl.substitute(nb="nb.ipynb") + " " + badge_tmpl.substitute(nb="nb.ipynb"),
        ),
    ],
)
def test_nb_add_self_md_badge(line, file_path, expected):
    track = False
    badge = add_badge(line, None, "usr/repo", "main", file_path, SRC, ALT, "notebook", track)
    assert badge == expected


@pytest.mark.parametrize(
    "line, line_num, cols",
    [
        ("{{badge}}", 1, [1]),
        ("{{ badge }}", 2, [1]),
        ("{{ badge }}{{ badge }}", 3, [1, 12]),
        ("{{ badge }} {{ badge }}", 4, [1, 13]),
    ],
)
def test_md_add_self_badge(caplog, line, line_num, cols):
    file_path = "file.md"
    levelname = "ERROR"
    message = (
        "You can use {{ badge }} only for notebooks, it is NOT possible to generate a badge for a md file! "
        "Use {{ badge <path> }} instead."
    )
    with caplog.at_level(logging.INFO):
        badge = add_badge(line, line_num, "usr/repo", "main", file_path, SRC, ALT, "md", True)
        assert badge is None
        for record, col in zip(caplog.records, cols):
            line_num = str(line_num)
            col = str(col)
            title = ":".join((file_path, line_num, col, " " + "Incorrect {{ badge }} usage."))

            assert record.file == file_path
            assert record.line == line_num
            assert record.col == col
            assert record.title == title
            assert record.levelname == levelname
            assert record.message == message


def test_add_badge_incorrect_file_type():
    with pytest.raises(ValueError):
        add_badge("{{ badge }}", 1, "usr/repo", "main", "file.py", SRC, ALT, "py", True)


@pytest.mark.parametrize(
    "line, expected",
    [
        ("badge //drive/12345", None),
        ("{badge //drive/12345}", None),
        ("{{badge //drive/12345}}", drive_badge_tmpl.substitute(nb="12345")),
        ("{{ badge //drive/12345}}", drive_badge_tmpl.substitute(nb="12345")),
        ("{{badge //drive/12345 }}", drive_badge_tmpl.substitute(nb="12345")),
        ("{{ badge //drive/12345}}", drive_badge_tmpl.substitute(nb="12345")),
        (
            "{{ badge //drive/12345 }}{{ badge //drive/67890 }}",
            drive_badge_tmpl.substitute(nb="12345") + drive_badge_tmpl.substitute(nb="67890"),
        ),
        (
            "{{ badge //drive/12345 }}abc{{ badge //drive/67890 }}",
            drive_badge_tmpl.substitute(nb="12345") + "abc" + drive_badge_tmpl.substitute(nb="67890"),
        ),
    ],
)
def test_add_badge_drive(line, expected):
    for file_path, file_type in zip(("nb.ipynb", "file.md"), ("notebook", "md")):
        badge = add_badge(line, None, "usr/repo", "main", file_path, SRC, ALT, file_type, True)
        assert badge == expected
