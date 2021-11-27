import os
import re
import json
from glob import iglob
import subprocess as sp

# Badge setup
SRC = '"https://colab.research.google.com/assets/colab-badge.svg"'
ALT = '"Open In Colab"'
BADGE_VAR = "{{ badge }}"
BADGE_PATTERN = re.compile(r"<!--<badge>-->(.*?)<!--</badge>-->")
HREF_PATTERN = re.compile(r"href=[\"\'](.*?)[\"\']")

# Set repository
CURRENT_REPOSITORY = os.environ['GITHUB_REPOSITORY']
TARGET_REPOSITORY = os.environ['INPUT_TARGET_REPOSITORY'] or CURRENT_REPOSITORY

# Set branches
GITHUB_REF = os.environ['GITHUB_REF']
GITHUB_HEAD_REF = os.environ['GITHUB_HEAD_REF']
CURRENT_BRANCH = GITHUB_HEAD_REF or GITHUB_REF.rsplit('/', 1)[-1]
TARGET_BRANCH = os.environ['INPUT_TARGET_BRANCH'] or CURRENT_BRANCH

CHECK = os.environ['INPUT_CHECK']  # 'all' | 'latest'
UPDATE = os.environ['INPUT_UPDATE']  # True | False


def main():
    """Sic Mundus Creatus Est.
    """
    if CHECK == "all":
        nbs = get_all_nbs()
    elif CHECK == "latest":
        nbs = get_modified_nbs()
    else:
        raise ValueError(f"{CHECK} is a wrong value. Expecting all or latest")

    if nbs:
        check_nb(nbs)


def get_all_nbs() -> iter:
    """Get list of all the notebooks a repo.
    """
    nbs = iglob("**/*.ipynb", recursive=True)
    return nbs


def get_modified_nbs() -> list:
    """Get list of all the modified notebooks in a current commit.
    """
    cmd = "git diff-tree --no-commit-id --name-only -r HEAD"
    committed_files = sp.getoutput(cmd).split('\n')
    nbs = [nb for nb in committed_files if (nb.endswith(".ipynb") and os.path.isfile(nb))]
    return nbs


def check_nb(notebooks: list):
    """Iterates over notebooks list.
    """
    for nb in notebooks:
        # Import notebook data
        nb_data = read_nb(nb)
        # Add badge to the right places, add right meta to the corresponding cell
        check_cells(nb_data, TARGET_REPOSITORY, TARGET_BRANCH, nb)


def read_nb(file_path: str) -> dict:
    """Reads jupyter notebook file.
    """
    with open(file_path, "r") as f:
        data = json.load(f)
    return data


def check_cells(data: dict, repo_name: str, branch: str, nb_path: str):
    """Looks for markdown cells. Then adds or updates Colab badge code.
    """
    save = False
    for cell in data["cells"]:
        # Check only markdown cells
        if cell["cell_type"] == "markdown":
            text = cell["source"]
            for i, line in enumerate(text):
                # If a cell already has a badge - check the repo and branch
                if UPDATE:
                    # Update repo, branch, file path
                    new_line = update_badge(line, repo_name, branch, nb_path)
                    if new_line:
                        text[i] = new_line
                        save = True if new_line else save
                # Add badge code
                new_line = add_badge(line, repo_name, branch, nb_path)
                if new_line:
                    text[i] = new_line
                    save = True if new_line else save
        else:
            continue

    # Export if modified
    if save:
        print(f"Saving modified {nb_path}...")
        write_nb(data, nb_path)


def add_badge(line: str, repo_name: str, branch: str, nb_path: str):
    """Inserts "Open in Colab" badge.
    """
    new_line = None
    if BADGE_VAR in line:
        badge = prepare_badge_code(repo_name, branch, nb_path)
        print(f"{nb_path}: Inserting badge...")
        new_line = line.replace(BADGE_VAR, badge)
    return new_line


def prepare_badge_code(repo_name: str, branch: str, nb_path: str) -> str:
    """Prepares right html code for the badge.
    """
    href = f'"https://colab.research.google.com/github/{repo_name}/blob/{branch}/{nb_path}"'
    code = f'<!--<badge>--><a href={href} target="_parent"><img src={SRC} alt={ALT}/></a><!--</badge>-->'
    return code


def update_badge(line: str, repo_name: str, branch: str, nb_path: str):
    """Updates added badge code.
    """
    new_href = f"https://colab.research.google.com/github/{repo_name}/blob/{branch}/{nb_path}"
    new_line = None

    badges = BADGE_PATTERN.findall(line)
    if badges:
        for badge in badges:
            href = HREF_PATTERN.findall(badge)[0]
            repo_branch_nb = href.split("/github/")[-1]
            curr_repo, branch_nb = repo_branch_nb.split("/blob/")
            curr_branch, curr_nb_path = branch_nb.split("/", 1)

            if (curr_repo != repo_name) or (curr_branch != branch) or (curr_nb_path != nb_path):
                print(f"{nb_path}: Updating badge info...")
                new_line = line.replace(href, new_href)

    return new_line


def write_nb(data: dict, file_path: str) -> None:
    """Saves modified jupyter notebook.
    """
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    main()
