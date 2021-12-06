import sys
import json
import logging
import string
from argparse import Namespace

import pytest

sys.path.append("src")
import lib
from lib import (
    Badge,
    File,
    Patterns,
    add_badge,
    append_ext_to_str,
    append_ext_to_url,
    check_cell,
    check_cells,
    check_md,
    check_md_line,
    check_nb_link,
    get_all_mds,
    get_all_nbs,
    get_modified_mds,
    get_modified_nbs,
    prepare_path_drive,
    prepare_path_local,
    prepare_path_remote,
    prepare_path_remote_full,
    prepare_path_self,
    read_file,
    read_md,
    read_nb,
    update_badge,
    write_file,
    write_md,
    write_nb,
)


@pytest.fixture
def badge():
    return Badge()


@pytest.fixture
def patterns():
    return Patterns()


@pytest.fixture
def min_nb():
    """Minimal notebook."""
    return {"metadata": {}, "cells": [], "nbformat": 4, "nbformat_minor": 5}


@pytest.fixture
def min_md():
    """Minimal md."""
    return [line + "\n" for line in string.ascii_lowercase]


@pytest.fixture
def make_tmp_nb(tmp_path, min_nb):
    """tmp notebook."""

    def _make_tmp_nb(fname):
        file_path = (tmp_path / fname).with_suffix(".ipynb")
        write_nb(min_nb, file_path)
        return file_path

    return _make_tmp_nb


@pytest.fixture
def make_tmp_md(tmp_path, min_md):
    """tmp md."""

    def _make_tmp_md(fname):
        file_path = (tmp_path / fname).with_suffix(".md")
        write_md(min_md, file_path)
        return file_path

    return _make_tmp_md


@pytest.fixture
def line():
    def _line(data="{{ badge }}", num=1):
        return Namespace(**{"data": data, "num": num})

    return _line


@pytest.fixture
def file():
    def _file(path="nb.ipynb", type="notebook", track=True, branch="main", repo="usr/repo"):
        return File(path=path, type=type, track=track, branch=branch, repo=repo)

    return _file


def test_read_nb(tmp_path, min_nb):
    expected = min_nb
    fname = "min_nb.ipynb"
    file_path = tmp_path / fname
    with open(file_path, "w") as f:
        json.dump(expected, f, indent=2)

    nb = read_nb(file_path)

    assert nb == expected


def test_write_nb(tmp_path, min_nb):
    expected = min_nb
    fname = "min_nb.ipynb"
    file_path = tmp_path / fname

    write_nb(expected, file_path)

    assert file_path.is_file()
    assert len([*tmp_path.iterdir()]) == 1

    with file_path.open() as f:
        nb = json.load(f)
    assert nb == expected


def test_read_md(tmp_path, min_md):
    expected = min_md
    fname = "file.md"
    file_path = tmp_path / fname
    file_path.write_text("".join(min_md))

    text = read_md(file_path)

    assert text == expected


def test_write_md(tmp_path):
    data = "abcde"
    data = [line + "\n" for line in data]
    fname = "file.md"
    file_path = tmp_path / fname

    write_md(data, str(file_path))

    assert file_path.is_file()
    assert len([*tmp_path.iterdir()]) == 1

    with open(file_path, "r") as f:
        md = f.readlines()

    assert md == data


def test_read_file(make_tmp_nb, make_tmp_md, min_nb, min_md):
    for file, expected in ((make_tmp_nb("file"), min_nb), (make_tmp_md("file"), min_md)):
        data = read_file(file)
        assert data == expected


def test_write_file(tmp_path, min_nb, min_md):
    for file, expected in ((tmp_path / "file.ipynb", min_nb), (tmp_path / "file.md", min_md)):
        write_file(expected, file)
        assert file.is_file()
        assert read_file(file) == expected


def test_get_all_nbs(make_tmp_nb):
    expected = [make_tmp_nb(name + ".ipynb") for name in string.ascii_lowercase]
    nbs = sorted(get_all_nbs(root_dir=expected[0].parent))
    assert nbs == [file.name for file in expected]


def test_get_all_mds(make_tmp_md):
    expected = [make_tmp_md(name + ".md") for name in string.ascii_lowercase]
    mds = sorted(get_all_mds(root_dir=expected[0].parent))
    assert mds == [file.name for file in expected]


def test_get_modified_nbs(monkeypatch, make_tmp_nb):
    expected = [str(make_tmp_nb(file)) for file in string.ascii_lowercase]
    with monkeypatch.context() as m:
        m.setattr(lib, "getoutput", lambda cmd: "\n".join(expected))
        files = get_modified_nbs()
        assert files == expected


def test_get_modified_mds(monkeypatch, make_tmp_md):
    expected = [str(make_tmp_md(file)) for file in string.ascii_lowercase]
    with monkeypatch.context() as m:
        m.setattr(lib, "getoutput", lambda cmd: "\n".join(expected))
        files = get_modified_mds()
        assert files == expected


@pytest.mark.parametrize(
    "path, expected",
    [
        ("file", "file.ipynb"),
        (".file.", ".file..ipynb"),
        ("file.ipynb", "file.ipynb"),
        ("./nbs/file.ipynb", "./nbs/file.ipynb"),
    ],
)
def test_append_ext_to_str(path, expected):
    path = append_ext_to_str(path)
    assert path == expected


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://github.com/usr2/repo/blob/main/nb1.ipynb", "https://github.com/usr2/repo/blob/main/nb1.ipynb"),
        ("https://github.com/usr2/repo/blob/main/nb1", "https://github.com/usr2/repo/blob/main/nb1.ipynb"),
        ("https://github.com/usr2/repo/blob/main/.nb1.", "https://github.com/usr2/repo/blob/main/.nb1..ipynb"),
    ],
)
def test_append_ext_to_url(url, expected):
    url = append_ext_to_url(url)
    assert url == expected


def test_check_nb_link_ok(monkeypatch):
    with monkeypatch.context() as m:
        m.setattr(lib.http.client.HTTPSConnection, "request", lambda *args: None)
        m.setattr(
            lib.http.client.HTTPSConnection, "getresponse", lambda _: Namespace(**{"status": 200, "reason": "OK"})
        )
        res = check_nb_link("/usr/repo/blob/main/nb.ipynb")
        assert res is None


def test_check_nb_link_bad(monkeypatch):
    with monkeypatch.context() as m:
        m.setattr(lib.http.client.HTTPSConnection, "request", lambda *args: None)
        m.setattr(
            lib.http.client.HTTPSConnection, "getresponse", lambda _: Namespace(**{"status": 404, "reason": "Err"})
        )
        res = check_nb_link("/usr/repo/blob/main/nb.ipynb")
        assert res == (404, "Err")


@pytest.mark.parametrize("path, track", [("nb1.md", True), ("nb2.md", False)])
def test_prepare_path_self_none(caplog, line, file, badge, patterns, path, track):
    line, file = line(), file(path=path, type="md", track=track)
    match = patterns.badge.match(line.data)
    line_num = str(line.num)
    col = str(match.start() + 1)
    title = ":".join((file.path, line_num, col, " " + "Incorrect {{ badge }} usage."))
    level = "ERROR"
    message = (
        "You can use {{ badge }} only for notebooks, it is NOT possible to generate a badge for a md file! "
        "Use {{ badge <path> }} instead."
    )
    with caplog.at_level(logging.ERROR):
        nb_path = prepare_path_self(match, line, file, badge)
        assert nb_path is None
        for record in caplog.records:
            assert record.file == file.path
            assert record.line == line_num
            assert record.col == col
            assert record.title == title
            assert record.levelname == level
            assert record.message == message


@pytest.mark.parametrize("path, track", [("nb1.md", True), ("nb2.md", False)])
def test_prepare_path_self_error(line, file, badge, patterns, path, track):
    line, file = line(), file(path=path, type="py", track=track)
    match = patterns.badge.match(line.data)

    with pytest.raises(ValueError):
        nb_path = prepare_path_self(match, line, file, badge)
        assert nb_path is None


@pytest.mark.parametrize("path, track", [("nb.ipynb", True), ("nb.ipynb", False)])
def test_prepare_path_self(caplog, line, file, badge, patterns, path, track):
    line, file = line(), file(path=path, type="notebook", track=track)
    match = patterns.badge.match(line.data)

    expected = badge.url.safe_substitute(repo=file.repo, branch=file.branch, file=file.path)
    nb_path = prepare_path_self(match, line, file, badge)
    assert nb_path == expected


@pytest.mark.parametrize(
    "path, nb_path, type",
    [
        ("nb.ipynb", "nb2.ipynb", "notebook"),
        ("nb.ipynb", "nb2", "notebook"),
        ("file.md", "nb2.ipynb", "md"),
        ("file.md", "nb2", "md"),
    ],
)
def test_prepare_path_local_none(caplog, line, file, badge, patterns, path, nb_path, type):
    line, file = line(data="{{ " + f"badge {nb_path}" + " }}"), file(path=path, type=type)
    match = patterns.badge.match(line.data)
    line_num = str(line.num)
    col = str(match.start() + 1)
    title = ":".join((file.path, line_num, col, " " + "File doesn't exist."))
    level = "ERROR"
    message = f"Specified file {nb_path} doesn't exist in current repository."
    with caplog.at_level(logging.ERROR):
        path = prepare_path_local(match, nb_path, line, file, badge)
        assert path is None
        for record in caplog.records:
            assert record.file == file.path
            assert record.line == line_num
            assert record.col == col
            assert record.title == title
            assert record.levelname == level
            assert record.message == message


@pytest.mark.parametrize(
    "path, nb_path, type",
    [
        ("nb.ipynb", "nb2.ipynb", "notebook"),
        ("nb.ipynb", "nb2", "notebook"),
        ("file.md", "nb2.ipynb", "md"),
        ("file.md", "nb2", "md"),
    ],
)
def test_prepare_path_local(make_tmp_nb, line, file, badge, patterns, path, nb_path, type):
    tmp_nb = make_tmp_nb(nb_path)
    line, file = line(data="{{ " + f"badge {tmp_nb}" + " }}"), file(path=path, type=type)
    match = patterns.badge.match(line.data)
    expected = badge.url.safe_substitute(repo=file.repo, branch=file.branch, file=tmp_nb)

    path = prepare_path_local(match, tmp_nb, line, file, badge)
    assert path == expected


@pytest.mark.parametrize(
    "path, nb_path",
    [
        ("nb.ipynb", "/usr2/repo/blob/main/nb1.ipynb"),
        ("nb.ipynb", "/usr2/repo/blob/main/nb2"),
        ("file.md", "/usr2/repo/blob/main/nb3.ipynb"),
        ("file.md", "/usr2/repo/blob/main/nb4"),
    ],
)
def test_prepare_path_remote_none(caplog, monkeypatch, line, file, badge, patterns, path, nb_path):
    _line, _file = line(data="{{ " + f"badge {nb_path}" + " }}"), file(path=path)
    match = patterns.badge.match(_line.data)

    with monkeypatch.context() as m:
        status, reason = (404, "Not Found")
        m.setattr(lib, "check_nb_link", lambda nb: (status, reason))

        line_num = str(_line.num)
        col = str(match.start() + 1)
        title = ":".join((_file.path, line_num, col, " " + f"{status} {reason}"))
        level = "ERROR"
        message = f"Specified file {nb_path} {reason}."
        with caplog.at_level(logging.ERROR):
            path = prepare_path_remote(match, nb_path, _line, _file, badge)
            assert path is None
            for record in caplog.records:
                assert record.file == _file.path
                assert record.line == line_num
                assert record.col == col
                assert record.title == title
                assert record.levelname == level
                assert record.message == message


@pytest.mark.parametrize(
    "path, nb_path, exp_nb_path",
    [
        ("nb.ipynb", "/usr2/repo/blob/main/nb1.ipynb", "/usr2/repo/blob/main/nb1.ipynb"),
        ("nb.ipynb", "/usr2/repo/blob/main/nb2", "/usr2/repo/blob/main/nb2.ipynb"),
        ("file.md", "/usr2/repo/blob/main/nb3.ipynb", "/usr2/repo/blob/main/nb3.ipynb"),
        ("file.md", "/usr2/repo/blob/main/nb4", "/usr2/repo/blob/main/nb4.ipynb"),
    ],
)
def test_prepare_path_remote(monkeypatch, line, file, badge, patterns, path, nb_path, exp_nb_path):
    _line, _file = line(data="{{ " + f"badge {nb_path}" + " }}"), file(path=path)
    match = patterns.badge.match(_line.data)

    with monkeypatch.context() as m:
        m.setattr(lib, "check_nb_link", lambda nb: None)

        expected = badge.url2.safe_substitute(file=exp_nb_path)
        path = prepare_path_remote(match, nb_path, _line, _file, badge)
        assert path == expected


@pytest.mark.parametrize(
    "path, nb_path",
    [
        ("nb.ipynb", "https://github.com/usr2/repo/blob/main/nb1.ipynb"),
        ("nb.ipynb", "https://github.com/usr2/repo/blob/main/nb1"),
        ("file.md", "https://github.com/usr2/repo/blob/main/nb2.ipynb"),
        ("file.md", "https://github.com/usr2/repo/blob/main/nb2"),
    ],
)
def test_prepare_path_remote_full_none(caplog, line, file, badge, patterns, path, nb_path):
    _line, _file = line(data="{{ " + f"badge {nb_path}" + " }}"), file(path=path)
    match = patterns.badge.match(_line.data)

    line_num = str(_line.num)
    col = str(match.start() + 1)
    title = ":".join((_file.path, line_num, col, " " + "Wrong hostname."))
    level = "ERROR"
    message = "Currently only notebooks hosted on GitHub are supported."
    nb_path = nb_path.replace("github.com", "example.com")
    with caplog.at_level(logging.ERROR):
        path = prepare_path_remote_full(match, nb_path, _line, _file, badge)
        assert path is None
        for record in caplog.records:
            assert record.file == _file.path
            assert record.line == line_num
            assert record.col == col
            assert record.title == title
            assert record.levelname == level
            assert record.message == message


@pytest.mark.parametrize(
    "path, nb_path",
    [
        ("nb.ipynb", "https://github.com/usr2/repo/blob/main/nb1.ipynb"),
        ("nb.ipynb", "https://github.com/usr2/repo/blob/main/nb1"),
        ("file.md", "https://github.com/usr2/repo/blob/main/nb2.ipynb"),
        ("file.md", "https://github.com/usr2/repo/blob/main/nb2"),
    ],
)
def test_prepare_path_remote_full_none_none(monkeypatch, line, file, badge, patterns, path, nb_path):
    _line, _file = line(data="{{ " + f"badge {nb_path}" + " }}"), file(path=path)
    match = patterns.badge.match(_line.data)
    with monkeypatch.context() as m:
        m.setattr(lib, "prepare_path_remote", lambda match, nb_path, line, file, badge: None)
        path = prepare_path_remote_full(match, nb_path, _line, _file, badge)
        assert path is None


@pytest.mark.parametrize(
    "path, nb_path, exp_nb_path",
    [
        (
            "nb.ipynb",
            "https://github.com/usr2/repo/blob/main/nb1.ipynb",
            "https://github.com/usr2/repo/blob/main/nb1.ipynb",
        ),
        ("nb.ipynb", "https://github.com/usr2/repo/blob/main/nb1", "https://github.com/usr2/repo/blob/main/nb1.ipynb"),
        (
            "file.md",
            "https://github.com/usr2/repo/blob/main/nb2.ipynb",
            "https://github.com/usr2/repo/blob/main/nb2.ipynb",
        ),
        ("file.md", "https://github.com/usr2/repo/blob/main/nb2", "https://github.com/usr2/repo/blob/main/nb2.ipynb"),
    ],
)
def test_prepare_path_remote_full(monkeypatch, line, file, badge, patterns, path, nb_path, exp_nb_path):
    _line, _file = line(data="{{ " + f"badge {nb_path}" + " }}"), file(path=path)
    match = patterns.badge.match(_line.data)
    with monkeypatch.context() as m:
        m.setattr(
            lib,
            "prepare_path_remote",
            lambda match, nb_path, line, file, badge: badge.url2.safe_substitute(
                file=nb_path.lstrip("https://github.com")
            ),
        )
        expected = badge.url2.safe_substitute(file=exp_nb_path.lstrip("https://github.com"))
        path = prepare_path_remote_full(match, nb_path, _line, _file, badge)
        assert path == expected


@pytest.mark.parametrize("nb_path", ["//drive/0000", "//drive/1111", "//drive/2222", "//drive/3333"])
def test_prepare_path_drive(badge, nb_path):
    assert prepare_path_drive(nb_path, badge) == badge.drive.safe_substitute(file=nb_path.lstrip("//drive/"))


@pytest.mark.parametrize("data", ["foo bar", "badge", "{{ bdg }}", "{{ badg }}"])
def test_add_badge_none(line, file, badge, patterns, data):
    line = add_badge(line=line(data=data), file=file(), badge=badge, patterns=patterns)
    assert line is None


@pytest.mark.parametrize(
    "data, path, type, track, expected",
    [
        (
            "{{ badge }}",
            "nb.ipynb",
            "notebook",
            True,
            "<!--<badge>-->"
            '<a href="https://colab.research.google.com/github/usr/repo/blob/main/nb.ipynb" target="_parent">'
            '<img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>'
            "<!--</badge>-->",
        ),
        (
            "{{ badge }}",
            "nb.ipynb",
            "notebook",
            False,
            "[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)]"
            "(https://colab.research.google.com/github/usr/repo/blob/main/nb.ipynb)",
        ),
        ("{{ badge }}", "nb.md", "md", False, None),
        ("{{ badge }}", "nb.md", "md", True, None),
    ],
)
def test_add_badge_self(line, file, badge, patterns, data, path, type, track, expected):
    _line = line(data=data)
    _file = file(path=path, type=type, track=track)
    expected = line(data=expected) if expected else None

    new_line = add_badge(line=_line, file=_file, badge=badge, patterns=patterns)
    assert new_line == expected


@pytest.mark.parametrize(
    "data, nb_path",
    [
        ("{{ badge nb2 }}", "nb2"),
        ("{{  badge   nb2 }}", "nb2"),
        ("{{   badge     nbs/nb.ipynb }}", " nbs/nb.ipynb"),
    ],
)
def test_add_badge_local(monkeypatch, line, file, badge, patterns, data, nb_path):
    nb_path = append_ext_to_str(nb_path)
    url = f"https://colab.research.google.com/github/usr/repo/blob/main/{nb_path}"
    _line = line(data=data)
    _file = file()
    expected = line(data=f"[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)]({url})")

    with monkeypatch.context() as m:
        m.setattr(lib, "prepare_path_local", lambda match, nb_path, line, file, badge: url)
        new_line = add_badge(line=_line, file=_file, badge=badge, patterns=patterns)
        assert new_line == expected


@pytest.mark.parametrize(
    "data, nb_path",
    [("{{ badge //drive/0000 }}", "//drive/0000"), ("{{ badge                 //drive/1111   }}", "//drive/1111")],
)
def test_add_badge_drive(monkeypatch, line, file, badge, patterns, data, nb_path):
    url = f"https://colab.research.google.com/drive/{nb_path.lstrip('//drive/')}"
    _line = line(data=data)
    _file = file()
    expected = line(data=f"[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)]({url})")
    new_line = add_badge(line=_line, file=_file, badge=badge, patterns=patterns)
    assert new_line == expected


@pytest.mark.parametrize(
    "data",
    [
        "{{ badge /usr2/repo2/blob/dev/nb2.ipynb }}",
        "{{  badge   /usr2/repo2/blob/dev/nb2 }}",
        "{{   badge   /usr2/repo2/blob/dev/nbs/nb.ipynb }}",
    ],
)
def test_add_badge_remote_none(monkeypatch, line, file, badge, patterns, data):
    _line = line(data=data)
    _file = file()

    with monkeypatch.context() as m:
        m.setattr(lib, "prepare_path_remote", lambda match, nb_path, line, file, badge: None)
        new_line = add_badge(line=_line, file=_file, badge=badge, patterns=patterns)
        assert new_line is None


@pytest.mark.parametrize(
    "data, nb_path",
    [
        ("{{ badge /usr2/repo2/blob/dev/nb2.ipynb }}", "/usr2/repo2/blob/dev/nb2.ipynb"),
        ("{{  badge   /usr2/repo2/blob/dev/nb2 }}", "/usr2/repo2/blob/dev/nb2"),
        ("{{   badge     /usr2/repo2/blob/dev/nbs/nb.ipynb }}", "/usr2/repo2/blob/dev/nbs/nb.ipynb"),
    ],
)
def test_add_badge_remote(monkeypatch, line, file, badge, patterns, data, nb_path):
    nb_path = append_ext_to_str(nb_path)
    url = f"https://colab.research.google.com/github/{nb_path}"
    _line = line(data=data)
    _file = file()
    expected = line(data=f"[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)]({url})")

    with monkeypatch.context() as m:
        m.setattr(lib, "prepare_path_remote", lambda match, nb_path, line, file, badge: url)
        new_line = add_badge(line=_line, file=_file, badge=badge, patterns=patterns)
        assert new_line == expected


@pytest.mark.parametrize(
    "data",
    [
        "{{ badge https://github.com/usr2/repo/blob/main/nb1.ipynb }}",
        "{{  badge   https://github.com/usr2/repo2/blob/dev/nb2 }}",
        "{{   badge   https://github.com/usr2/repo2/blob/dev/nbs/nb.ipynb }}",
    ],
)
def test_add_badge_remote_full_none(monkeypatch, line, file, badge, patterns, data):
    _line = line(data=data)
    _file = file()

    with monkeypatch.context() as m:
        m.setattr(lib, "prepare_path_remote_full", lambda match, nb_path, line, file, badge: None)
        new_line = add_badge(line=_line, file=_file, badge=badge, patterns=patterns)
        assert new_line is None


@pytest.mark.parametrize(
    "data, nb_path",
    [
        (
            "{{ badge https://github.com/usr2/repo/blob/main/nb1.ipynb }}",
            "https://github.com/usr2/repo/blob/main/nb1.ipynb",
        ),
        ("{{  badge   https://github.com/usr2/repo2/blob/dev/nb2 }}", "https://github.com/usr2/repo2/blob/dev/nb2"),
        (
            "{{   badge   https://github.com/usr2/repo2/blob/dev/nbs/nb.ipynb }}",
            "https://github.com/usr2/repo2/blob/dev/nbs/nb.ipynb",
        ),
    ],
)
def test_add_badge_remote_full(monkeypatch, line, file, badge, patterns, data, nb_path):
    nb_path = append_ext_to_url(nb_path)
    url = f"https://colab.research.google.com/github/{nb_path.replace('https://github.com/', '')}"
    _line = line(data=data)
    _file = file()
    expected = line(data=f"[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)]({url})")

    with monkeypatch.context() as m:
        m.setattr(lib, "prepare_path_remote_full", lambda match, nb_path, line, file, badge: url)
        new_line = add_badge(line=_line, file=_file, badge=badge, patterns=patterns)
        assert new_line == expected


def test_update_badge_none(line, file, badge, patterns):
    line = update_badge(line=line(data="foo bar"), file=file(), badge=badge, patterns=patterns)
    assert line is None


@pytest.mark.parametrize("path, new_path", [("nb.ipynb", "nb2.ipynb"), ("nb.ipynb", "dir/nb.ipynb")])
def test_update_badge(line, file, badge, patterns, path, new_path):
    _line = line(
        data="<!--<badge>-->"
        f'<a href="https://colab.research.google.com/github/usr/repo/blob/main/{path}" target="_parent">'
        '<img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>'
        "<!--</badge>-->"
    )
    expected = line(
        data="<!--<badge>-->"
        f'<a href="https://colab.research.google.com/github/usr/repo/blob/main/{new_path}" target="_parent">'
        '<img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>'
        "<!--</badge>-->"
    )
    line2 = update_badge(
        line=_line,
        file=file(path=new_path),
        badge=badge,
        patterns=patterns,
    )
    assert line2 == expected


@pytest.mark.parametrize("data", ["", "{badge}", "{ badge }", "{{ badge }", "{{  }}", "badge"])
def test_check_md_line_none(line, file, badge, patterns, data):
    _line = line(data=data)
    for track in (True, False):
        line2 = check_md_line(line=_line, file=file(track=track), badge=badge, patterns=patterns)
        assert line2 is None


def test_check_md_line(monkeypatch, line, file, badge, patterns):
    _line = line(data="foo.bar")
    for track in (True, False):
        with monkeypatch.context() as m:
            m.setattr(lib, "update_badge", lambda line, file, badge, patterns: _line)
            m.setattr(lib, "add_badge", lambda line, file, badge, patterns: _line)
            line2 = check_md_line(line=_line, file=file(track=track), badge=badge, patterns=patterns)
            assert line2 == _line


def test_check_cell_none(file, badge, patterns):
    cell = {"source": ["\n", "{{ badg }}"]}
    cell = check_cell(cell=cell, file=file(), badge=badge, patterns=patterns)
    assert cell is None


def test_check_cell(monkeypatch, line, file, badge, patterns):
    _line = line
    _text = ["foo", "bar", "foo", "bar"]
    text = ["foo", "bar", "foo", "bar"]
    cell = {"source": text}
    with monkeypatch.context() as m:
        m.setattr(lib, "check_md_line", lambda line, file, badge, patterns: _line(data=_text.pop(0)))
        cell2 = check_cell(cell=cell, file=file(), badge=badge, patterns=patterns)
        assert cell2 == cell


def test_check_md_none(file, badge, patterns):
    text = ["\n", "{{ badg }}"]
    text = check_md(text=text, file=file(), badge=badge, patterns=patterns)
    assert text is None


def test_check_md(monkeypatch, line, file, badge, patterns):
    _line = line
    _text = ["foo", "bar", "foo", "bar"]
    text = ["foo", "bar", "foo", "bar"]
    with monkeypatch.context() as m:
        m.setattr(lib, "check_md_line", lambda line, file, badge, patterns: _line(data=_text.pop(0)))
        text2 = check_md(text=text, file=file(), badge=badge, patterns=patterns)
        assert text2 == text


def test_check_cells_none(file, badge, patterns):
    cells = [
        {"source": ["foo\n", "{{ foo }}"], "cell_type": "markdown"},
        {"source": ["bar\n", "foo{{{}}} }}"], "cell_type": "code"},
        {"source": ["bar\n", "foo{{{}}} }}"], "cell_type": "markdown"},
    ]
    cells = check_cells(cells=cells, file=file(), badge=badge, patterns=patterns)
    assert cells is None


def test_check_cells(monkeypatch, file, badge, patterns):
    cells = [
        {"source": ["foo", "bar"], "cell_type": "markdown"},
        {"source": ["bar", "foo"], "cell_type": "code"},
        {"source": ["bar", "foo"], "cell_type": "markdown"},
    ]
    _cells = [
        {"source": ["foo", "bar"], "cell_type": "markdown"},
        {"source": ["bar", "foo"], "cell_type": "code"},
        {"source": ["bar", "foo"], "cell_type": "markdown"},
    ]
    with monkeypatch.context() as m:
        m.setattr(lib, "check_cell", lambda cell, file, badge, patterns: _cells.pop(0))
        cells2 = check_cells(cells=cells, file=file(), badge=badge, patterns=patterns)
        assert cells2 == cells
