import json
import os
import re
import subprocess as sp
from glob import iglob
from typing import List, Optional


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


def is_md(cell: dict) -> bool:
    return cell["cell_type"] == "markdown"


def prepare_badge_code(repo_name: str, branch: str, nb_path: str, src: str, alt: str) -> str:
    """Prepares right html code for the badge."""
    href = f'"https://colab.research.google.com/github/{repo_name}/blob/{branch}/{nb_path}"'
    code = f'<!--<badge>--><a href={href} target="_parent"><img src={src} alt={alt}/></a><!--</badge>-->'
    return code


def add_badge(
    badge_var: str, line: str, repo_name: str, branch: str, nb_path: str, src: str, alt: str
) -> Optional[str]:
    """Inserts "Open in Colab" badge."""
    new_line = None
    if badge_var in line:
        badge = prepare_badge_code(repo_name, branch, nb_path, src, alt)
        print(f"{nb_path}: Inserting badge...")
        new_line = line.replace(badge_var, badge)
    return new_line


def update_badge(
    line: str, repo_name: str, branch: str, nb_path: str, badge_pattern: re.Pattern, href_pattern: re.Pattern
) -> Optional[str]:
    """Updates added badge code."""
    new_line = None
    new_href = f"https://colab.research.google.com/github/{repo_name}/blob/{branch}/{nb_path}"

    badges = badge_pattern.findall(line)

    if badges:
        for badge in badges:
            href = href_pattern.findall(badge)[0]
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
    update: bool,
    badge_var: str,
    badge_pattern: re.Pattern,
    href_pattern: re.Pattern,
    src: str,
    alt: str,
) -> Optional[dict]:
    """Updates/Adds badge for jupyter markdown cell."""
    updated = False
    # Get source
    text = cell["source"]
    # Iterate over source lines
    for i, line in enumerate(text):
        # If a cell already has a badge - check the repo and branch
        if update:
            # Update repo, branch, file path
            new_line = update_badge(line, repo_name, branch, nb_path, badge_pattern, href_pattern)
            if new_line:
                text[i] = new_line
                updated = True if new_line else updated
        # Add badge code
        new_line = add_badge(badge_var, line, repo_name, branch, nb_path, src, alt)
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
    update: bool,
    badge_var: str,
    badge_pattern: re.Pattern,
    href_pattern: re.Pattern,
    src: str,
    alt: str,
) -> Optional[List[dict]]:
    updated = False
    for cell_idx, cell in enumerate(cells):
        # Check only markdown cells
        if is_md(cell):
            cell = check_cell(
                cell, repo_name, branch, nb_path, update, badge_var, badge_pattern, href_pattern, src, alt
            )
            if cell is not None:
                cells[cell_idx] = cell
                updated = True
        else:
            continue

    if updated:
        return cells
