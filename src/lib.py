import http.client
import json
import os
import re
import urllib.parse
from argparse import Namespace
from glob import glob
from logging import Logger
from pathlib import Path
from string import Template
from subprocess import getoutput
from typing import Iterable, List, NamedTuple, Optional, Tuple, Union

# logging.basicConfig(format="::%(levelname)s file=%(file)s,line=%(line)s,title=%(title)s::%(message)s")


class File(NamedTuple):
    path: str
    type: str
    track: bool
    branch: str
    repo: str


class Badge(NamedTuple):
    drive: Template = Template("https://colab.research.google.com/drive/$file")
    url: Template = Template("https://colab.research.google.com/github/$repo/blob/$branch/$file")
    url2: Template = Template("https://colab.research.google.com/github/$file")
    html: Template = Template(
        '<!--<badge>--><a href="$url" target="_parent">'
        '<img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>'
        "<!--</badge>-->"
    )
    md: Template = Template("[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)]($url)")


class Patterns(NamedTuple):
    # Badge tag.
    badge: re.Pattern = re.compile(r"(?P<badge>\{{2}\ *badge\ *(?P<path>.*?)\ *\}{2})")
    # Badge that is tracked.
    tracked: re.Pattern = re.compile(r"<!--<badge>-->(.*?)<!--</badge>-->")
    # Href for tracked badge case (using html).
    href: re.Pattern = re.compile(r"href=[\"\'](.*?)[\"\']")
    # Compile a URL pattern, from https://github.com/django/django/blob/stable/1.3.x/django/core/validators.py#L45
    url: re.Pattern = re.compile(
        r"^(?:http|ftp)s?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # Domain...
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ... or ip
        r"(?::\d+)?"  # Optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )


def read_file(path: str) -> Union[dict, Iterable[str]]:
    """File reader."""
    return {".ipynb": read_nb, ".md": read_md}[Path(path).suffix](path)


def read_nb(path: str) -> dict:
    """Reads jupyter notebook file."""
    with open(path, "r") as f:
        data = json.load(f)
    return data


def read_md(path: str) -> Iterable[str]:
    """Reads markdowns file."""
    with open(path, "r") as f:
        data = f.readlines()
    return data


def write_file(data: Union[dict, List[str]], path: str) -> None:
    """File writer."""
    write_nb(data, path) if isinstance(data, dict) else write_md(data, path)


def write_nb(data: dict, path: str) -> None:
    """Saves modified jupyter notebook."""
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def write_md(data: List[str], path: str) -> None:
    """Saves modified jupyter notebook."""
    with open(path, "w") as f:
        f.writelines(data)


def get_all_nbs(root_dir: Optional[str] = None) -> List[str]:
    """Get list of all the notebooks."""
    return glob("**/*.ipynb", root_dir=root_dir, recursive=True)


def get_all_mds(root_dir: Optional[str] = None) -> List[str]:
    """Get list of all markdown files."""
    return glob("**/*.md", root_dir=root_dir, recursive=True)


def get_modified_nbs() -> List[str]:
    """Get list of all the modified notebooks in a current commit."""
    cmd = "git diff-tree --no-commit-id --name-only -r HEAD"
    committed_files = getoutput(cmd).split("\n")
    nbs = [nb for nb in committed_files if (nb.endswith(".ipynb") and os.path.isfile(nb))]
    return nbs


def get_modified_mds() -> List[str]:
    """Get list of all the modified markdown files in a current commit."""
    cmd = "git diff-tree --no-commit-id --name-only -r HEAD"
    committed_files = getoutput(cmd).split("\n")
    mds = [md for md in committed_files if (md.endswith(".md") and os.path.isfile(md))]
    return mds


def append_ext_to_str(path: str) -> str:
    """Adds jupyter notebook extension if necessary."""
    p = Path(path)
    if not p.suffix:
        path = str(p.with_suffix(".ipynb"))
    return path


def append_ext_to_url(url: str) -> str:
    """Adds jupyter notebook to url extension if necessary."""
    path = urllib.parse.urlsplit(url).path
    new_path = append_ext_to_str(path)
    if new_path != path:
        url = urllib.parse.urljoin(url, Path(new_path).name)
    return url


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


def prepare_path_drive(nb_path: str, badge: Badge) -> Optional[str]:
    success = None
    nb_path_url = badge.drive.safe_substitute(file=nb_path.lstrip("//drive/"))
    if nb_path_url:
        success = nb_path_url
    return success


def prepare_path_remote(
    match: re.Match, nb_path: str, line: Namespace, file: File, badge: Badge, logger: Logger
) -> Optional[str]:
    success = None
    nb_path_ext = append_ext_to_url(nb_path)
    res = check_nb_link(nb_path_ext)
    # Notebook exists (link is OK).
    if res is None:
        nb_path_url = badge.url2.safe_substitute(file=nb_path_ext)
        success = nb_path_url
    # Notebook: bad link (on github).
    else:
        line_num_str, status, reason = map(str, (line.num or "", res[0], res[1]))
        title = ":".join((file.path, line_num_str, " " + f"{status} {reason}"))
        logger.error(
            f"Specified file {nb_path} {reason}.",
            extra={"file": file.path, "line": line_num_str, "title": title},
        )
    return success


def prepare_path_remote_full(
    match: re.Match, nb_path: str, line: Namespace, file: File, badge: Badge, logger: Logger
) -> Optional[str]:
    success = None
    nb_path_ext = append_ext_to_url(nb_path)
    # Check hostname.
    # TODO: gists?
    nb_path_parse_res = urllib.parse.urlparse(nb_path_ext)
    # Only github is allowed.
    if nb_path_parse_res.hostname == "github.com":
        # Get notebook path.
        nb_path_url = prepare_path_remote(match, nb_path_parse_res.path, line, file, badge, logger)
        if nb_path_url is not None:
            success = nb_path_url
    # Host is not supported.
    else:
        line_num_str = str(line.num or "")
        title = ":".join((file.path, line_num_str, " " + "Wrong hostname."))
        logger.error(
            "Currently only notebooks hosted on GitHub are supported.",
            extra={"file": file.path, "line": line_num_str, "title": title},
        )
    return success


def prepare_path_local(
    match: re.Match, nb_path: str, line: Namespace, file: File, badge: Badge, logger: Logger
) -> Optional[str]:
    success = None
    nb_path_ext = append_ext_to_str(nb_path)
    # Check file existence.
    _path = Path(nb_path_ext)
    # File is OK.
    if _path.exists() and _path.is_file():
        nb_path_url = badge.url.safe_substitute(repo=file.repo, branch=file.branch, file=nb_path_ext)
        success = nb_path_url
    # No such file.
    else:
        line_num_str = str(line.num or "")
        title = ":".join((file.path, line_num_str, " " + "File doesn't exist."))
        logger.error(
            f"Specified file {nb_path} doesn't exist in current repository.",
            extra={"file": file.path, "line": line_num_str, "title": title},
        )
    return success


def prepare_path_self(match: re.Match, line: Namespace, file: File, badge: Badge, logger: Logger) -> Optional[str]:
    success = None
    # Check file type.
    if file.type == "notebook":
        # Path is None, use file_path.
        nb_path_ext = append_ext_to_str(file.path)
        # Otherwise use markdown code. Note: you cannot mix html and md.
        nb_path_url = badge.url.substitute(repo=file.repo, branch=file.branch, file=nb_path_ext)
        success = nb_path_url
    # Markdown points to itself -> incorrect.
    elif file.type == "md":
        line_num_str = str(line.num or "")
        title = ":".join((file.path, line_num_str, " " + "Incorrect {{ badge }} usage."))
        logger.error(
            "You can use {{ badge }} only for notebooks, "
            "it is NOT possible to generate a badge for a md file! "
            "Use {{ badge <path> }} instead.",
            extra={"file": file.path, "line": line_num_str, "title": title},
        )
    # Anything else is invalid.
    else:
        raise ValueError(f"Inappropriate file_type=({file.type}) value!")

    return success


def add_badge(line: Namespace, file: File, badge: Badge, patterns: Patterns, logger: Logger) -> Optional[Namespace]:
    """Inserts "Open in Colab" badge."""
    updated = False
    badge_matches = patterns.badge.finditer(line.data)
    for badge_match in badge_matches:
        nb_path = badge_match["path"]
        # Notebook from the repo, gdrive, or nb from another repo).
        if nb_path:
            # Notebook from gdrive or from repo.
            if patterns.url.match(nb_path) is None:
                # Notebook from gdrive or from remote repo.
                if nb_path.startswith("/"):
                    # Notebook from the google drive.
                    if nb_path.startswith("//drive/"):
                        nb_path_url = prepare_path_drive(nb_path, badge)
                    # Notebook from remote repo.
                    else:
                        nb_path_url = prepare_path_remote(badge_match, nb_path, line, file, badge, logger)
                # Notebook from local (repo) repo.
                else:
                    nb_path_url = prepare_path_local(badge_match, nb_path, line, file, badge, logger)
            # Full url -> notebook from remote repo.
            else:
                nb_path_url = prepare_path_remote_full(badge_match, nb_path, line, file, badge, logger)
            if nb_path_url is None:
                continue
            # Prepare code badge
            badge_code = badge.md.safe_substitute(url=nb_path_url)
        # Self-Notebook (notebook points to itself).
        else:
            nb_path_url = prepare_path_self(badge_match, line, file, badge, logger)
            if nb_path_url is None:
                continue
            # If track, add html code allowing tracking.
            if file.track:
                badge_code = badge.html.safe_substitute(url=nb_path_url)
            # Otherwise use markdown code. Note: you cannot mix html and md.
            else:
                badge_code = badge.md.safe_substitute(url=nb_path_url)
        # Update line
        line.data = line.data.replace(badge_match["badge"], badge_code, 1)
        updated = True

    return line if updated else None


def update_badge(line: Namespace, file: File, badge: Badge, patterns: Patterns) -> Optional[Namespace]:
    """Updates added badge code."""
    updated = False
    file_path = append_ext_to_str(file.path)
    new_href = badge.url.safe_substitute(repo=file.repo, branch=file.branch, file=file_path)

    badges = patterns.tracked.findall(line.data)
    if badges:
        for b in badges:
            href = patterns.href.findall(b)[0]
            repo_branch_nb = href.split("/github/")[-1]
            curr_repo, branch_nb = repo_branch_nb.split("/blob/")
            curr_branch, curr_file_path = branch_nb.split("/", 1)

            if (curr_repo != file.repo) or (curr_branch != file.branch) or (curr_file_path != file_path):
                line.data = line.data.replace(href, new_href)
                updated = True

    return line if updated else None


def check_md_line(line: Namespace, file: File, badge: Badge, patterns: Patterns, logger: Logger) -> Optional[Namespace]:
    updated = False
    # If a there is a badge - check the repo and the branch.
    if file.track:
        # Update repo, branch, file path.
        new_line = update_badge(line, file, badge, patterns)
        if new_line:
            line = new_line
            updated = True
    # Add badge code.
    new_line = add_badge(line, file, badge, patterns, logger)
    if new_line:
        line = new_line
        updated = True

    return line if updated else None


def check_cell(cell: dict, file: File, badge: Badge, patterns: Patterns, logger: Logger) -> Optional[dict]:
    """Updates/Adds badge for jupyter markdown cell."""
    updated = False
    # Get source.
    text = cell["source"]
    # Iterate over source lines.
    for i, l in enumerate(text):
        line = Namespace(**{"data": l, "num": 1})
        new_line = check_md_line(line, file, badge, patterns, logger)
        if new_line:
            text[i] = new_line.data
            updated = True

    return cell if updated else None


def check_md(text: List[str], file: File, badge: Badge, patterns: Patterns, logger: Logger) -> Optional[List[str]]:
    """Updates/Adds badge for markdown file."""
    updated = False
    # Iterate over source lines.
    for i, l in enumerate(text):
        line = Namespace(**{"data": l, "num": i + 1})
        new_line = check_md_line(line, file, badge, patterns, logger)
        if new_line:
            text[i] = new_line.data
            updated = True

    return text if updated else None


def check_cells(
    cells: List[dict], file: File, badge: Badge, patterns: Patterns, logger: Logger
) -> Optional[List[dict]]:
    updated = False
    for cell_idx, cell in enumerate(cells):
        # Check only markdown cells.
        if cell["cell_type"] == "markdown":
            new_cell = check_cell(cell, file, badge, patterns, logger)
            if new_cell is not None:
                cell = new_cell
                cells[cell_idx] = cell
                updated = True
        else:
            continue

    return cells if updated else None
