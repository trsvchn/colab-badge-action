import functools
import glob
import http.client
import json
import logging
import os
import pathlib
import re
import string
import subprocess
import urllib
from typing import Iterable, List, Optional, Tuple

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
DRV = "https://colab.research.google.com/drive"
HREF_TMPL = string.Template('"https://colab.research.google.com/github/$repo/blob/$branch/$file_path"')
URL_TMPL = string.Template("https://colab.research.google.com/github/$repo/blob/$branch/$file_path")
URL_TMPL2 = string.Template("https://colab.research.google.com/github/$nb")
HTML_BADGE_TMPL = string.Template(
    '<!--<badge>--><a href=$href target="_parent"><img src=$src alt=$alt/></a><!--</badge>-->'
)
MD_BADGE_TMPL = string.Template("[![$alt]($src)]($url)")
LOGGING_FORMAT = "::%(levelname)s file=%(file)s,line=%(line)s,col=%(col)s,title=%(title)s::%(message)s"

logging.basicConfig(format=LOGGING_FORMAT)


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

    From:
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


def check_nb_link(nb: str) -> Optional[Tuple[int, str]]:
    """Link checker."""
    bad = None
    connection = http.client.HTTPSConnection("github.com")
    connection.request("HEAD", nb)
    response = connection.getresponse()
    connection.close()

    status, reason = response.status, response.reason
    if not (status < 400):
        bad = (status, reason)

    return bad


def prepare_badge_code_html(repo: str, branch: str, file_path: str, src: str, alt: str) -> str:
    """Prepares right html code for the badge."""
    href = HREF_TMPL.safe_substitute(repo=repo, branch=branch, file_path=file_path)
    code = HTML_BADGE_TMPL.safe_substitute(href=href, src=src, alt=alt)
    return code


def prepare_badge_code_md(url: str, src: str, alt: str) -> str:
    """Prepares right html code for the badge."""
    code = MD_BADGE_TMPL.safe_substitute(url=url, src=src, alt=alt)
    return code


def add_badge(
    line: str,
    line_num: Optional[int],
    repo: str,
    branch: str,
    file_path: str,
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
            nb_path = badge_match["path"]
            # Notebook from the repo, gdrive, or nb from another repo).
            if nb_path:
                # Notebook from gdrive or from repo.
                if url_pattern().match(nb_path) is None:
                    # Notebook from gdrive or from remote repo.
                    if nb_path.startswith("/"):
                        # Notebook from the google drive.
                        if nb_path.startswith("//drive/"):
                            nb_path = urllib.parse.urljoin(DRV, nb_path.lstrip("/"))
                        # Notebook from remote repo.
                        else:
                            res = check_nb_link(nb_path)
                            # Notebook exists (link is OK).
                            if res is None:
                                nb_path = URL_TMPL2.safe_substitute(nb=nb_path)
                            # Notebook: bad link (on github).
                            else:
                                line_num_str, col, status, reason = map(
                                    str, (line_num or "", badge_match.start() + 1, res[0], res[1])
                                )
                                title = ":".join((file_path, line_num_str, col, " " + f"{status} {reason}"))
                                logging.error(
                                    f"Specified file {nb_path} {reason}.",
                                    extra={"file": file_path, "line": line_num_str, "col": col, "title": title},
                                )
                                continue
                    # Notebook from local (repo) repo.
                    else:
                        nb_path = append_ext_to_url(nb_path)
                        # Check file existence.
                        _path = pathlib.Path(nb_path)
                        # File is OK.
                        if _path.exists() and _path.is_file():
                            nb_path = URL_TMPL.safe_substitute(repo=repo, branch=branch, file_path=nb_path)
                        # No such file.
                        else:
                            line_num_str, col = map(str, (line_num or "", badge_match.start() + 1))
                            title = ":".join((file_path, line_num_str, col, " " + "File doesn't exist."))
                            logging.error(
                                f"Specified file {nb_path} doesn't exist in current repository.",
                                extra={"file": file_path, "line": line_num_str, "col": col, "title": title},
                            )
                            continue
                # Full url -> notebook from remote repo.
                else:
                    nb_path = append_ext_to_url(nb_path)
                    # Check hostname.
                    # TODO: gists?
                    nb_path_url = urllib.parse.urlparse(nb_path)
                    # Only github is allowed.
                    if nb_path_url.hostname == "github.com":
                        # Get notebook path.
                        nb_path = nb_path_url.path
                        # Check existence.
                        res = check_nb_link(nb_path)
                        # Link is OK.
                        if res is None:
                            nb_path = URL_TMPL2.safe_substitute(nb=nb_path)
                        # Bad response.
                        else:
                            line_num_str, col, status, reason = map(
                                str, (line_num or "", badge_match.start() + 1, res[0], res[1])
                            )
                            title = ":".join((file_path, line_num_str, col, " " + f"{status} {reason}"))
                            logging.error(
                                f"Specified file {nb_path} {reason}.",
                                extra={"file": file_path, "line": line_num_str, "col": col, "title": title},
                            )
                            continue
                    # Host is not supported.
                    else:
                        line_num_str, col = map(str, (line_num or "", badge_match.start() + 1))
                        title = ":".join((file_path, line_num_str, col, " " + "Wrong hostname."))
                        logging.error(
                            "Currently only notebooks hosted on GitHub are supported.",
                            extra={"file": file_path, "line": line_num_str, "col": col, "title": title},
                        )
                        continue
                # Prepare code badge
                badge = prepare_badge_code_md(nb_path, src.strip('"'), alt.strip('"'))
                line = line.replace(badge_match["badge"], badge, 1)
                updated = True
            # Self-Notebook (notebook points to itself).
            else:
                # Check filer type.
                if file_type == "notebook":
                    # Path is None, use file_path.
                    file_path = append_ext_to_str(file_path)
                    # If track, add html code allowing tracking.
                    if track:
                        badge = prepare_badge_code_html(repo, branch, file_path, src, alt)
                    # Otherwise use markdown code. Note: you cannot mix html and md.
                    else:
                        nb_path = URL_TMPL.safe_substitute(repo=repo, branch=branch, file_path=file_path)
                        badge = prepare_badge_code_md(nb_path, src.strip('"'), alt.strip('"'))
                    # Replace tag with the code.
                    line = line.replace(badge_match["badge"], badge, 1)
                    updated = True
                # Markdown points to itself -> incorrect.
                elif file_type == "md":
                    line_num_str, col = map(str, (line_num or "", badge_match.start() + 1))
                    title = ":".join((file_path, line_num_str, col, " " + "Incorrect {{ badge }} usage."))
                    logging.error(
                        "You can use {{ badge }} only for notebooks, "
                        "it is NOT possible to generate a badge for a md file! "
                        "Use {{ badge <path> }} instead.",
                        extra={"file": file_path, "line": line_num_str, "col": col, "title": title},
                    )
                    continue
                # Anything else is invalid.
                else:
                    raise ValueError(f"Inappropriate file_type=({file_type}) value!")

    return line if updated else None


def update_badge(line: str, repo: str, branch: str, file_path: str) -> Optional[str]:
    """Updates added badge code."""
    updated = False
    file_path = append_ext_to_str(file_path)
    new_href = URL_TMPL.safe_substitute(repo=repo, branch=branch, file_path=file_path)

    badges = track_badge_pattern().findall(line)

    if badges:
        for badge in badges:
            href = href_pattern().findall(badge)[0]
            repo_branch_nb = href.split("/github/")[-1]
            curr_repo, branch_nb = repo_branch_nb.split("/blob/")
            curr_branch, curr_file_path = branch_nb.split("/", 1)

            if (curr_repo != repo) or (curr_branch != branch) or (curr_file_path != file_path):
                line = line.replace(href, new_href)
                updated = True

    return line if updated else None


def check_md_line(
    line: str,
    line_num: Optional[int],
    repo: str,
    branch: str,
    file_path: str,
    src: str,
    alt: str,
    file_type: str,
    track: bool,
) -> Optional[str]:
    updated = False
    # If a there is a badge - check the repo and the branch.
    if track:
        # Update repo, branch, file path.
        new_line = update_badge(line, repo, branch, file_path)
        if new_line:
            line = new_line
            updated = True

    # Add badge code.
    new_line = add_badge(line, line_num, repo, branch, file_path, src, alt, file_type, track)
    if new_line:
        line = new_line
        updated = True

    return line if updated else None


def check_cell(
    cell: dict,
    repo: str,
    branch: str,
    file_path: str,
    src: str,
    alt: str,
    track: bool,
) -> Optional[dict]:
    """Updates/Adds badge for jupyter markdown cell."""
    updated = False
    # Get source.
    text = cell["source"]
    # Iterate over source lines.
    for i, line in enumerate(text):
        new_line = check_md_line(line, None, repo, branch, file_path, src, alt, "notebook", track)
        if new_line:
            text[i] = new_line
            updated = True

    return cell if updated else None


def check_md(
    text: List[str],
    repo: str,
    branch: str,
    file_path: str,
    src: str,
    alt: str,
    track: bool,
) -> Optional[List[str]]:
    """Updates/Adds badge for markdown file."""
    updated = False
    # Iterate over source lines.
    for i, line in enumerate(text):
        new_line = check_md_line(line, i + 1, repo, branch, file_path, src, alt, "md", track)
        if new_line:
            text[i] = new_line
            updated = True

    return text if updated else None


def check_cells(
    cells: List[dict],
    repo: str,
    branch: str,
    file_path: str,
    src: str,
    alt: str,
    track: bool,
) -> Optional[List[dict]]:
    updated = False
    for cell_idx, cell in enumerate(cells):
        # Check only markdown cells.
        if is_md_cell(cell):
            new_cell = check_cell(cell, repo, branch, file_path, src, alt, track)
            if new_cell is not None:
                cell = new_cell
                cells[cell_idx] = cell
                updated = True
        else:
            continue

    return cells if updated else None
