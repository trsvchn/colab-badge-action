import functools
import glob
import json
import os
import pathlib
import re
import string
import subprocess
import urllib
from typing import Iterable, List, Optional

__all__ = [
    "ALT",
    "SRC",
    "read_nb",
    "read_md",
    "write_md",
    "write_nb",
    "get_all_mds",
    "get_all_nbs",
    "get_modified_nbs",
    "get_modified_mds",
    "check_cells",
    "check_md",
]

ALT = '"Open In Colab"'
SRC = '"https://colab.research.google.com/assets/colab-badge.svg"'
HREF_TMPL = string.Template('"https://colab.research.google.com/github/$repo_name/blob/$branch/$nb_path"')
URL_TMPL = string.Template("https://colab.research.google.com/github/$repo_name/blob/$branch/$nb_path")
HTML_BADGE_TMPL = string.Template(
    '<!--<badge>--><a href=$href target="_parent"><img src=$src alt=$alt/></a><!--</badge>-->'
)
MD_BADGE_TMPL = string.Template("[![$alt]($src)]($url)")


def read_nb(file_path: str) -> dict:
    """Reads jupyter notebook file."""
    with open(file_path, "r") as f:
        data = json.load(f)
    return data


def read_md(file_path: str) -> Iterable[str]:
    """Reads markdowns file."""
    with open(file_path, "r") as f:
        data = f.readlines()
    return data


def write_nb(data: dict, file_path: str) -> None:
    """Saves modified jupyter notebook."""
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)


def write_md(data: List[str], file_path: str) -> None:
    """Saves modified jupyter notebook."""
    with open(file_path, "w") as f:
        f.writelines(data)


def get_all_nbs() -> List[str]:
    """Get list of all the notebooks."""
    nbs = glob.glob("**/*.ipynb", recursive=True)
    return nbs


def get_all_mds() -> List[str]:
    """Get list of all markdown files."""
    mds = glob.glob("**/*.md", recursive=True)
    return mds


def get_modified_nbs() -> List[str]:
    """Get list of all the modified notebooks in a current commit."""
    cmd = "git diff-tree --no-commit-id --name-only -r HEAD"
    committed_files = subprocess.getoutput(cmd).split("\n")
    nbs = [nb for nb in committed_files if (nb.endswith(".ipynb") and os.path.isfile(nb))]
    return nbs


def get_modified_mds() -> List[str]:
    """Get list of all the modified markdown files in a current commit."""
    cmd = "git diff-tree --no-commit-id --name-only -r HEAD"
    committed_files = subprocess.getoutput(cmd).split("\n")
    mds = [md for md in committed_files if (md.endswith(".md") and os.path.isfile(md))]
    return mds


def is_md_cell(cell: dict) -> bool:
    return cell["cell_type"] == "markdown"


def append_ext_to_str(path: str) -> str:
    """Adds jupyter notebook extension if necessary."""
    p = pathlib.Path(path)
    if not p.suffix:
        path = str(p.with_suffix(".ipynb"))
    return path


def append_ext_to_url(url: str) -> str:
    """Adds jupyter notebook to url extension if necessary."""
    path = urllib.parse.urlsplit(url).path
    new_path = append_ext_to_str(path)
    if new_path != path:
        url = urllib.parse.urljoin(url, pathlib.Path(new_path).name)
    return url


@functools.lru_cache()
def badge_pattern():
    """Badge tag."""
    return re.compile(r"(?P<badge>\{{2}\ *badge\ *(?P<path>.*?)\ *\}{2})")


@functools.lru_cache()
def track_badge_pattern():
    """Badge that is tracked."""
    return re.compile(r"<!--<badge>-->(.*?)<!--</badge>-->")


@functools.lru_cache()
def href_pattern():
    """Href for tracked badge case (using html)."""
    return re.compile(r"href=[\"\'](.*?)[\"\']")


@functools.lru_cache()
def url_pattern():
    """Compile a URL pattern.

    Taken from:
    https://github.com/django/django/blob/stable/1.3.x/django/core/validators.py#L45
    """
    return re.compile(
        r"^(?:http|ftp)s?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # Domain...
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ... or ip
        r"(?::\d+)?"  # Optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )


def prepare_badge_code_html(repo_name: str, branch: str, nb_path: str, src: str, alt: str) -> str:
    """Prepares right html code for the badge."""
    href = HREF_TMPL.safe_substitute(repo_name=repo_name, branch=branch, nb_path=nb_path)
    code = HTML_BADGE_TMPL.safe_substitute(href=href, src=src, alt=alt)
    return code


def prepare_badge_code_md(url: str, src: str, alt: str) -> str:
    """Prepares right html code for the badge."""
    code = MD_BADGE_TMPL.safe_substitute(url=url, src=src, alt=alt)
    return code


def add_badge(
    line: str,
    repo_name: str,
    branch: str,
    nb_path: str,
    src: str,
    alt: str,
    file_type: str,
    track: bool,
) -> Optional[str]:
    """Inserts "Open in Colab" badge."""
    updated = False
    badge_matches = badge_pattern().finditer(line)

    if badge_matches:
        for badge_match in badge_matches:
            path = badge_match["path"]
            if (not path) and (file_type == "notebook"):  # Self-Notebook (notebook points to itself).
                # Path is None, use nb_path
                nb_path = append_ext_to_str(nb_path)
                if track:  # If track, add html code allowing tracking
                    badge = prepare_badge_code_html(repo_name, branch, nb_path, src, alt)
                else:  # Otherwise use markdown code. Note: you cannot mix html and md.
                    path = URL_TMPL.safe_substitute(repo_name=repo_name, branch=branch, nb_path=nb_path)
                    badge = prepare_badge_code_md(path, src.strip('"'), alt.strip('"'))
                # TODO: replace it with logging
                print(f"{nb_path}: Inserting badge...")
                # Replace tag with the code
                line = line.replace(badge_match["badge"], badge, 1)
                updated = True
            elif path:  # Notebook from the repo_name, gdrive, or nb from another repo)
                if url_pattern().match(path) is None:  # Notebook from gdrive or from repo_name
                    if path.startswith("/drive/"):  # Notebook from the google drive
                        path = urllib.parse.urljoin("https://colab.research.google.com", path)
                    else:  # Notebook from this repo
                        path = append_ext_to_url(path)
                        path = URL_TMPL.safe_substitute(repo_name=repo_name, branch=branch, nb_path=path)
                else:  # Notebook from internet
                    path = append_ext_to_url(path)
                    path = path.replace("/github.com/", "/colab.research.google.com/github/", 1)
                badge = prepare_badge_code_md(path, src.strip('"'), alt.strip('"'))
                print(f"{nb_path}: Inserting badge...")
                line = line.replace(badge_match["badge"], badge, 1)
                updated = True
            else:
                continue

    return line if updated else None


def update_badge(line: str, repo_name: str, branch: str, nb_path: str) -> Optional[str]:
    """Updates added badge code."""
    updated = False
    nb_path = append_ext_to_str(nb_path)
    new_href = URL_TMPL.safe_substitute(repo_name=repo_name, branch=branch, nb_path=nb_path)

    badges = track_badge_pattern().findall(line)

    if badges:
        for badge in badges:
            href = href_pattern().findall(badge)[0]
            repo_branch_nb = href.split("/github/")[-1]
            curr_repo, branch_nb = repo_branch_nb.split("/blob/")
            curr_branch, curr_nb_path = branch_nb.split("/", 1)

            if (curr_repo != repo_name) or (curr_branch != branch) or (curr_nb_path != nb_path):
                print(f"{nb_path}: Updating badge info...")
                line = line.replace(href, new_href)
                updated = True

    return line if updated else None


def check_md_line(
    line: str,
    repo_name: str,
    branch: str,
    nb_path: str,
    src: str,
    alt: str,
    file_type: str,
    track: bool,
) -> Optional[str]:
    updated = False
    # If a there is a badge - check the repo and the branch
    if track:
        # Update repo, branch, file path
        new_line = update_badge(line, repo_name, branch, nb_path)
        if new_line:
            line = new_line
            updated = True

    # Add badge code
    new_line = add_badge(line, repo_name, branch, nb_path, src, alt, file_type, track)
    if new_line:
        line = new_line
        updated = True

    return line if updated else None


def check_cell(
    cell: dict,
    repo_name: str,
    branch: str,
    nb_path: str,
    src: str,
    alt: str,
    track: bool,
) -> Optional[dict]:
    """Updates/Adds badge for jupyter markdown cell."""
    updated = False
    # Get source
    text = cell["source"]
    # Iterate over source lines
    for i, line in enumerate(text):
        new_line = check_md_line(line, repo_name, branch, nb_path, src, alt, "notebook", track)
        if new_line:
            text[i] = new_line
            updated = True

    return cell if updated else None


def check_md(
    text: List[str],
    repo_name: str,
    branch: str,
    nb_path: str,
    src: str,
    alt: str,
    track: bool,
) -> Optional[List[str]]:
    """Updates/Adds badge for markdown file."""
    updated = False
    # Iterate over source lines
    for i, line in enumerate(text):
        new_line = check_md_line(line, repo_name, branch, nb_path, src, alt, "md", track)
        if new_line:
            text[i] = new_line
            updated = True

    return text if updated else None


def check_cells(
    cells: List[dict],
    repo_name: str,
    branch: str,
    nb_path: str,
    src: str,
    alt: str,
    track: bool,
) -> Optional[List[dict]]:
    updated = False
    for cell_idx, cell in enumerate(cells):
        # Check only markdown cells
        if is_md_cell(cell):
            new_cell = check_cell(cell, repo_name, branch, nb_path, src, alt, track)
            if new_cell is not None:
                cell = new_cell
                cells[cell_idx] = cell
                updated = True
        else:
            continue

    return cells if updated else None
