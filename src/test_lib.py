import json
import logging
from argparse import Namespace

import pytest

import lib
from lib import (
    Badge,
    File,
    Patterns,
    prepare_path_drive,
    prepare_path_local,
    prepare_path_remote,
    prepare_path_remote_full,
    prepare_path_self,
    write_nb,
)


@pytest.fixture
def badge():
    return Badge()


@pytest.fixture
def patterns():
    return Patterns()


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
        write_nb(nb, file_path)
        return file_path

    return _make_tmp_nb


def test_write_nb(tmp_path, min_notebook):
    nb = min_notebook
    fname = "min_nb.ipynb"
    file_path = tmp_path / fname

    write_nb(nb, file_path)

    assert (tmp_path / fname).is_file()
    assert len([*tmp_path.iterdir()]) == 1

    with file_path.open() as f:
        nb2 = json.load(f)

    for k in nb2:
        assert nb2[k] == nb[k]


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


@pytest.mark.parametrize(
    "path, type, track",
    [
        ("nb.ipynb", "notebook", True),
        ("nb.ipynb", "notebook", False),
        ("nb.md", "md", True),
        ("nb.md", "md", False),
        ("nb.py", "py", True),
        ("nb.py", "py", False),
    ],
)
def test_prepare_path_self(caplog, line, file, badge, patterns, path, type, track):
    line, file = line(), file(path=path, type=type, track=track)
    match = patterns.badge.match(line.data)

    if file.type == "notebook":
        expected = badge.url.safe_substitute(repo=file.repo, branch=file.branch, file=file.path)
        nb_path = prepare_path_self(match, line, file, badge)
        assert nb_path == expected
    elif file.type == "md":
        line_num = str(line.num)
        col = str(match.start() + 1)
        title = ":".join((file.path, line_num, col, " " + "Incorrect {{ badge }} usage."))
        level = "ERROR"
        message = (
            "You can use {{ badge }} only for notebooks, it is NOT possible to generate a badge for a md file! "
            "Use {{ badge <path> }} instead."
        )
        with caplog.at_level(logging.INFO):
            nb_path = prepare_path_self(match, line, file, badge)
            assert nb_path is None
            for record in caplog.records:
                assert record.file == file.path
                assert record.line == line_num
                assert record.col == col
                assert record.title == title
                assert record.levelname == level
                assert record.message == message
    else:
        with pytest.raises(ValueError):
            nb_path = prepare_path_self(match, line, file, badge)
            assert nb_path is None


@pytest.mark.parametrize(
    "path, nb_path, type",
    [
        ("nb.ipynb", "nb2.ipynb", "notebook"),
        ("nb.ipynb", "nb2", "notebook"),
        ("file.md", "nb2.ipynb", "md"),
        ("file.md", "nb2", "md"),
    ],
)
def test_prepare_path_local(caplog, make_tmp_nb, line, file, badge, patterns, path, nb_path, type):
    tmp_nb = make_tmp_nb(nb_path)
    line, file = line(data="{{ " + f"badge {tmp_nb}" + " }}"), file(path=path, type=type)
    match = patterns.badge.match(line.data)
    expected = badge.url.safe_substitute(repo=file.repo, branch=file.branch, file=tmp_nb)

    path = prepare_path_local(match, tmp_nb, line, file, badge)
    assert path == expected

    line_num = str(line.num)
    col = str(match.start() + 1)
    title = ":".join((file.path, line_num, col, " " + "File doesn't exist."))
    level = "ERROR"
    message = f"Specified file {nb_path} doesn't exist in current repository."
    with caplog.at_level(logging.INFO):
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
    "path, nb_path, exp_nb_path",
    [
        ("nb.ipynb", "/usr2/repo/blob/main/nb1.ipynb", "/usr2/repo/blob/main/nb1.ipynb"),
        ("nb.ipynb", "/usr2/repo/blob/main/nb2", "/usr2/repo/blob/main/nb2.ipynb"),
        ("file.md", "/usr2/repo/blob/main/nb3.ipynb", "/usr2/repo/blob/main/nb3.ipynb"),
        ("file.md", "/usr2/repo/blob/main/nb4", "/usr2/repo/blob/main/nb4.ipynb"),
    ],
)
def test_prepare_path_remote(caplog, monkeypatch, line, file, badge, patterns, path, nb_path, exp_nb_path):
    with monkeypatch.context() as m:
        m.setattr(lib, "check_nb_link", lambda nb: None)
        _line, _file = line(data="{{ " + f"badge {nb_path}" + " }}"), file(path=path)
        match = patterns.badge.match(_line.data)
        expected = badge.url2.safe_substitute(file=exp_nb_path)

        path = prepare_path_remote(match, nb_path, _line, _file, badge)
        assert path == expected

    with monkeypatch.context() as m:
        status, reason = (404, "Not Found")
        m.setattr(lib, "check_nb_link", lambda nb: (status, reason))
        _line, _file = line(data="{{ " + f"badge {nb_path}" + " }}"), file(path=path, type=type)
        match = patterns.badge.match(_line.data)
        line_num = str(_line.num)
        col = str(match.start() + 1)
        title = ":".join((_file.path, line_num, col, " " + f"{status} {reason}"))
        level = "ERROR"
        message = f"Specified file {nb_path} {reason}."
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
def test_prepare_path_remote_full(caplog, monkeypatch, line, file, badge, patterns, path, nb_path, exp_nb_path):
    with monkeypatch.context() as m:
        m.setattr(
            lib,
            "prepare_path_remote",
            lambda match, nb_path, line, file, badge: badge.url2.safe_substitute(
                file=nb_path.lstrip("https://github.com")
            ),
        )
        _line, _file = line(data="{{ " + f"badge {nb_path}" + " }}"), file(path=path, type=type)
        match = patterns.badge.match(_line.data)
        expected = badge.url2.safe_substitute(file=exp_nb_path.lstrip("https://github.com"))
        path = prepare_path_remote_full(match, nb_path, _line, _file, badge)
        assert path == expected

    with monkeypatch.context() as m:
        m.setattr(lib, "prepare_path_remote", lambda match, nb_path, line, file, badge: None)
        _line, _file = line(data="{{ " + f"badge {nb_path}" + " }}"), file(path=path, type=type)
        match = patterns.badge.match(_line.data)
        path = prepare_path_remote_full(match, nb_path, _line, _file, badge)
        assert path is None


@pytest.mark.parametrize("nb_path", ["0000", "1111", "2222", "3333"])
def test_prepare_path_drive(badge, nb_path):
    assert prepare_path_drive("//drive/" + nb_path, badge) == badge.drive.safe_substitute(file=nb_path)
