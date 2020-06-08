import os
import re
import json
from glob import iglob
import subprocess as sp

# Badge setup
SRC = '"https://colab.research.google.com/assets/colab-badge.svg"'
ALT = '"Open In Colab"'

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
    if CHECK:
        if CHECK == 'all':
            nbs = get_all_nbs()
        elif CHECK == 'latest':
            nbs = get_modified_nbs()
        else:
            raise ValueError(f'{CHECK} is a wrong value. Expecting all or latest')
    else:
        nbs = []

    if nbs:
        modified_nbs = check_nb(nbs)
        if modified_nbs:
            set_output(modified_nbs)
        else:
            set_output()
            print('Nothing to add. Nothing to update!')
    else:
        set_output()
        print('There is no modified notebooks in a current commit.')


def get_modified_nbs() -> list:
    """Get list of all the modified notebooks in a current commit.
    """
    cmd = 'git diff-tree --no-commit-id --name-only -r HEAD'
    committed_files = sp.getoutput(cmd).split('\n')
    nbs = [nb for nb in committed_files if (nb.endswith('.ipynb') and os.path.isfile(nb))]
    return nbs


def get_all_nbs() -> iter:
    """Get list of all the notebooks a repo.
    """
    nbs = iglob('**/*.ipynb', recursive=True)
    return nbs


def check_nb(notebooks: list) -> list:
    """Iterates over notebooks list.
    """
    updated_nbs = []  # To track updated notebooks

    for nb in notebooks:
        # Import notebook data
        nb_data = read_nb(nb)
        # Add badge to right places, add right meta to the corresponding cell
        check_cells(nb_data, TARGET_REPOSITORY, TARGET_BRANCH, nb, updated_nbs)

    return updated_nbs


def read_nb(file_path: str) -> dict:
    """Reads jupyter notebook file.
    """
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data


def prepare_badge_code(repo_name: str, branch: str, nb_path: str) -> str:
    """Prepares right html code for the badge.
    """
    href = f'"https://colab.research.google.com/github/{repo_name}/blob/{branch}/{nb_path}"'
    code = f'<a href={href} target="_parent"><img src={SRC} alt={ALT}/></a>'
    return code


def check_cells(data: dict, repo_name: str, branch: str, nb_path: str, modified: list):
    """Looks for markdown cells. Then adds or updates Colab badge code.
    """
    save = False
    for cell in data['cells']:
        # Check only markdown cells
        if cell['cell_type'] == 'markdown':
            if cell['metadata']:
                # If a cell already has a badge - check the repo and branch
                if UPDATE and cell['metadata'].get('badge'):
                    # Update repo, branch, file path, cell badge meta
                    save = True if update_badge(cell, repo_name, branch, nb_path) else save
            # Add badge code, add metadata
            save = True if add_badge(cell, repo_name, branch, nb_path) else save
        else:
            continue

    # Export if modified
    if save:
        print(f'Saving modified {nb_path}...')
        write_nb(data, nb_path)
        modified.append(nb_path)


def add_badge(cell: dict, repo_name: str, branch: str, nb_path: str):
    """Inserts "Open in Colab" badge.
    """
    modified = False
    pattern = '{{ badge }}'  # badge variable
    meta = {
        'badge': True,
        'repo_name': repo_name,
        'branch': branch,
        'nb_path': nb_path,
        'comment': 'This badge cell was added by colab-badge-action',
    }

    text = cell['source']
    for i, line in enumerate(text):
        if pattern in line:
            badge = prepare_badge_code(repo_name, branch, nb_path)
            print(f'{nb_path}: Inserting badge...')
            new_line = line.replace(pattern, badge)
            # Add metadata about cell
            text[i] = new_line
            cell['metadata'].update(meta)
            modified = True
        else:
            continue
    return modified


def update_badge(cell: dict, repo_name: str, branch: str, nb_path: str):
    """Updates added badge code.
    """
    modified = False
    a_pattern = re.compile(r'<a (.*?)</a>')

    meta = cell['metadata']
    curr_repo, curr_branch, curr_nb_path = meta['repo_name'], meta['branch'], meta['nb_path']

    new_href = f'"https://colab.research.google.com/github/{repo_name}/blob/{branch}/{nb_path}"'
    code = f'href={new_href} target="_parent"><img src={SRC} alt={ALT}/>'

    text = cell['source']

    for i, line in enumerate(text):
        links = a_pattern.findall(line)
        if links:
            for link in links:
                if SRC and ALT in link:
                    if (curr_repo != repo_name) or (curr_branch != branch) or (curr_nb_path != nb_path):
                        print(f'{nb_path}: Updating badge info...')
                        new_line = line.replace(link, code)
                        text[i] = new_line

                        # Updates cell badge metadata
                        if curr_repo != repo_name: meta.update({'repo_name': repo_name})
                        if curr_branch != branch: meta.update({'branch': branch})
                        if curr_nb_path != nb_path: meta.update({'nb_path': nb_path})
                        modified = True
                else:
                    continue
        else:
            continue
    return modified


def write_nb(data: dict, file_path: str) -> None:
    """Saves modified jupyter notebook.
    """
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)


def set_output(modified_nbs=None) -> None:
    """Sets the modified notebooks as a environmental variable (set-env) and step output (set-output).
    """
    modified_nbs = modified_nbs or []
    # os.environ['MODIFIED_NOTEBOOKS'] = ' '.join(set(modified_nbs))
    run = lambda cmd, name: sp.run(f"echo ::{cmd} name={name}::{' '.join(set(modified_nbs))}", shell=True, check=True)
    run('set-env', 'MODIFIED_NOTEBOOKS')
    run('set-output ', 'modified_notebooks')


if __name__ == '__main__':
    main()
