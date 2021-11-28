import json
import os
import re
import subprocess as sp
from functools import lru_cache
from glob import iglob
from typing import List, Optional

ALT = '"Open In Colab"'
SRC = '"https://colab.research.google.com/assets/colab-badge.svg"'


def read_nb(file_path: str) -> dict:
    """Reads jupyter notebook file."""
    with open(file_path, "r") as f:
        data = json.load(f)
    return data


def write_nb(data: dict, file_path: str) -> None:
    """Saves modified jupyter notebook."""
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)


def get_all_nbs() -> iter:
    """Get list of all the notebooks a repo."""
    nbs = iglob("**/*.ipynb", recursive=True)
    return nbs


def get_modified_nbs() -> list:
    """Get list of all the modified notebooks in a current commit."""
    cmd = "git diff-tree --no-commit-id --name-only -r HEAD"
    committed_files = sp.getoutput(cmd).split("\n")
    nbs = [nb for nb in committed_files if (nb.endswith(".ipynb") and os.path.isfile(nb))]
    return nbs


def is_md_cell(cell: dict) -> bool:
    return cell["cell_type"] == "markdown"


@lru_cache()
def badge_pattern():
    """Badge tag."""
    return re.compile(r"(?P<badge>\{{2}\ *badge\ *(?P<path>.*?)\ *\}{2})")


@lru_cache()
def track_badge_pattern():
    """Badge that is tracked."""
    return re.compile(r"<!--<badge>-->(.*?)<!--</badge>-->")


@lru_cache()
def href_pattern():
    """Href for tracked badge case (using html)."""
    return re.compile(r"href=[\"\'](.*?)[\"\']")


@lru_cache()
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
    href = f'"https://colab.research.google.com/github/{repo_name}/blob/{branch}/{nb_path}"'
    code = f'<!--<badge>--><a href={href} target="_parent"><img src={src} alt={alt}/></a><!--</badge>-->'
    return code


def prepare_badge_code_md(url: str, src: str, alt: str) -> str:
    """Prepares right html code for the badge."""
    code = f"[![{alt}]({src})]({url})"
    return code


def add_badge(
    line: str,
    repo_name: str,
    branch: str,
    nb_path: str,
    src: str,
    alt: str,
    file_type: str,
    track: bool = True,
) -> Optional[str]:
    """Inserts "Open in Colab" badge."""
    updated = False
    badge_matches = badge_pattern().finditer(line)

    for badge_match in badge_matches:
        if not badge_match["path"] and file_type == "notebook":
            if track:
                badge = prepare_badge_code_html(repo_name, branch, nb_path, src, alt)
            else:
                path = f"https://colab.research.google.com/github/{repo_name}/blob/{branch}/{nb_path}"
                badge = prepare_badge_code_md(path, src.strip('"'), alt.strip('"'))
            print(f"{nb_path}: Inserting badge...")
            line = line.replace(badge_match["badge"], badge, 1)
            updated = True
        else:
            path = badge_match["path"]

            if url_pattern().match(path) is None:
                path = f"https://colab.research.google.com/github/{repo_name}/blob/{branch}/{path}"
            else:
                path = path.replace("/github.com/", "/colab.research.google.com/github/", 1)

            badge = prepare_badge_code_md(path, src.strip('"'), alt.strip('"'))
            print(f"{nb_path}: Inserting badge...")
            line = line.replace(badge_match["badge"], badge, 1)
            updated = True

    if updated:
        return line


def update_badge(line: str, repo_name: str, branch: str, nb_path: str) -> Optional[str]:
    """Updates added badge code."""
    new_line = None
    new_href = f"https://colab.research.google.com/github/{repo_name}/blob/{branch}/{nb_path}"

    badges = track_badge_pattern().findall(line)

    if badges:
        for badge in badges:
            href = href_pattern().findall(badge)[0]
            repo_branch_nb = href.split("/github/")[-1]
            curr_repo, branch_nb = repo_branch_nb.split("/blob/")
            curr_branch, curr_nb_path = branch_nb.split("/", 1)

            if (curr_repo != repo_name) or (curr_branch != branch) or (curr_nb_path != nb_path):
                print(f"{nb_path}: Updating badge info...")
                new_line = line.replace(href, new_href)

    return new_line


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
        # If a cell already has a badge - check the repo and branch
        if track:
            # Update repo, branch, file path
            new_line = update_badge(line, repo_name, branch, nb_path)
            if new_line:
                text[i] = new_line
                updated = True if new_line else updated
        # Add badge code
        new_line = add_badge(line, repo_name, branch, nb_path, src, alt, "notebook", track)
        if new_line:
            text[i] = new_line
            updated = True if new_line else updated

    if updated:
        return cell


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
            cell = check_cell(cell, repo_name, branch, nb_path, src, alt, track)
            if cell is not None:
                cells[cell_idx] = cell
                updated = True
        else:
            continue

    if updated:
        return cells
