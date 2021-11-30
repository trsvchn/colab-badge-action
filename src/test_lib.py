import json

import pytest

from lib import ALT, SRC, add_badge, write_nb

alt = ALT.strip('"')
src = SRC.strip('"')


@pytest.fixture
def min_notebook():
    """Minimal notebook."""
    return {"metadata": {}, "cells": [], "nbformat": 4, "nbformat_minor": 2}


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
    "test_line, repo_name, branch, nb_path, file_type, track, expected_line",
    [
        ("", "repo", "main", "nb.ipynb", "notebook", True, None),
        ("badge", "repo", "main", "nb.ipynb", "notebook", True, None),
        ("{badge}", "repo", "main", "nb.ipynb", "notebook", True, None),
        (
            "{{ badge }}",
            "user/repo",
            "main",
            "nb.ipynb",
            "notebook",
            True,
            f'<!--<badge>--><a href="https://colab.research.google.com/github/user/repo/blob/main/nb.ipynb"'
            f' target="_parent"><img src={SRC} alt={ALT}/></a><!--</badge>-->',
        ),
        (
            "{{ badge }}",
            "user/repo",
            "main",
            "nb.ipynb",
            "notebook",
            False,
            f"[![{alt}]({src})](https://colab.research.google.com/github/user/repo/blob/main/nb.ipynb)",
        ),
        (
            "{{ badge }}{{ badge }}",
            "user/repo",
            "main",
            "nb.ipynb",
            "notebook",
            True,
            f'<!--<badge>--><a href="https://colab.research.google.com/github/user/repo/blob/main/nb.ipynb"'
            f' target="_parent"><img src={SRC} alt={ALT}/></a><!--</badge>-->'
            f'<!--<badge>--><a href="https://colab.research.google.com/github/user/repo/blob/main/nb.ipynb"'
            f' target="_parent"><img src={SRC} alt={ALT}/></a><!--</badge>-->',
        ),
        (
            "{{ badge }} {{ badge }}",
            "user/repo",
            "main",
            "nb.ipynb",
            "notebook",
            True,
            f'<!--<badge>--><a href="https://colab.research.google.com/github/user/repo/blob/main/nb.ipynb"'
            f' target="_parent"><img src={SRC} alt={ALT}/></a><!--</badge>--> '
            f'<!--<badge>--><a href="https://colab.research.google.com/github/user/repo/blob/main/nb.ipynb"'
            f' target="_parent"><img src={SRC} alt={ALT}/></a><!--</badge>-->',
        ),
        (
            "{{ badge nbs/nb1.ipynb }}",
            "user/repo",
            "main",
            "nb.ipynb",
            "notebook",
            True,
            f"[![{alt}]({src})](https://colab.research.google.com/github/user/repo/blob/main/nbs/nb1.ipynb)",
        ),
        (
            "{{ badge nbs/nb1.ipynb }} {{ badge nbs/nb2.ipynb }}",
            "user/repo",
            "main",
            "nb.ipynb",
            "notebook",
            True,
            f"[![{alt}]({src})](https://colab.research.google.com/github/user/repo/blob/main/nbs/nb1.ipynb) "
            f"[![{alt}]({src})](https://colab.research.google.com/github/user/repo/blob/main/nbs/nb2.ipynb)",
        ),
        (
            "{{ badge https://github.com/user2/repo2/blob/main/nb2.ipynb }}",
            "user/repo",
            "main",
            "nb.ipynb",
            "notebook",
            True,
            f"[![{alt}]({src})](https://colab.research.google.com/github/user2/repo2/blob/main/nb2.ipynb)",
        ),
        (
            "{{ badge /drive/1234567890 }}",
            "user/repo",
            "main",
            "nb.ipynb",
            "notebook",
            True,
            f"[![{alt}]({src})](https://colab.research.google.com/drive/1234567890)",
        ),
        (
            "{{ badge nbs/nb1 }}",
            "user/repo",
            "main",
            "nb.ipynb",
            "notebook",
            True,
            f"[![{alt}]({src})](https://colab.research.google.com/github/user/repo/blob/main/nbs/nb1.ipynb)",
        ),
        (
            "{{ badge drive/n b s/nb1_ _. }}",
            "user/repo",
            "main",
            "nb.ipynb",
            "notebook",
            True,
            f"[![{alt}]({src})](https://colab.research.google.com/github/user/repo/blob/main/drive/n b s/nb1_ _..ipynb)",
        ),
        (
            "{{ badge .drive/nbs/nb1.... }}",
            "user/repo",
            "main",
            "nb.ipynb",
            "notebook",
            True,
            f"[![{alt}]({src})](https://colab.research.google.com/github/user/repo/blob/main/.drive/nbs/nb1.....ipynb)",
        ),
        (
            "{{ badge ...drive/nbs/nb1.... }}",
            "user/repo",
            "main",
            "nb.ipynb",
            "notebook",
            True,
            f"[![{alt}]({src})](https://colab.research.google.com/github/user/repo/blob/main/...drive/nbs/nb1.....ipynb)",
        ),
        (
            "{{ badge https://github.com/user2/repo2/blob/main/nb2 }}",
            "user/repo",
            "main",
            "nb.ipynb",
            "notebook",
            True,
            f"[![{alt}]({src})](https://colab.research.google.com/github/user2/repo2/blob/main/nb2.ipynb)",
        ),
        (
            "{{ badge https://github.com/user2/repo2/blob/main/.nb2. }}",
            "user/repo",
            "main",
            "nb.ipynb",
            "notebook",
            True,
            f"[![{alt}]({src})](https://colab.research.google.com/github/user2/repo2/blob/main/.nb2..ipynb)",
        ),
        (
            "{{ badge https://github.com/user2/repo2/blob/main/.nbs/nb2.  }}",
            "user/repo",
            "main",
            "nb.ipynb",
            "notebook",
            True,
            f"[![{alt}]({src})](https://colab.research.google.com/github/user2/repo2/blob/main/.nbs/nb2..ipynb)",
        ),
    ],
)
def test_add_badge(test_line, repo_name, branch, nb_path, file_type, track, expected_line):
    assert add_badge(test_line, repo_name, branch, nb_path, SRC, ALT, file_type, track) == expected_line
