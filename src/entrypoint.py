import os
import re
import json
import subprocess as sp


SRC = '"https://colab.research.google.com/assets/colab-badge.svg"'
ALT = '"Open In Colab"'
GITHUB_REPOSITORY = os.environ['GITHUB_REPOSITORY']
GITHUB_REF = os.environ['GITHUB_REF']
_, BRANCH = GITHUB_REF.rsplit('/', 1)
GITHUB_ACTOR = os.environ['GITHUB_ACTOR']
GITHUB_TOKEN = os.environ['INPUT_GITHUB_TOKEN']


def main():
    """Sic Mundus Creatus Est.
    """
    nbs = get_nb_list()
    if nbs:
        modified_nbs = update(nbs)
        if modified_nbs:
            for nb in modified_nbs.items():
                nb_path, data = nb
                # Export notebook
                print(f'Saving modified {nb_path}...')
                write_nb(data, nb_path)
            # Commit changes
            commit_changes(list(modified_nbs.keys()))
            # Push
            push_changes()
        else:
            print('Nothing to add. Nothing to update!')
    else:
        print('There is no modified notebooks in a current commit.')


def get_nb_list() -> list:
    """Get list of all the modified notebooks in a current commit.
    """
    cmd = 'git diff-tree --no-commit-id --name-only -r HEAD'
    committed_files = sp.getoutput(cmd).split('\n')
    nbs = [nb for nb in committed_files if (nb.endswith('.ipynb') and os.path.isfile(nb))]
    return nbs


def update(notebooks: list) -> dict:
    """Iterates over changed notebooks list.
    """
    updated_nbs = {}  # To track updated notebooks

    for nb in notebooks:
        # Import notebook data
        nb_data = read_nb(nb)
        # Add badge to right places, add right meta to the corresponding cell
        check_cells(nb_data, GITHUB_REPOSITORY, BRANCH, nb, updated_nbs)

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


def check_cells(data: dict, repo_name: str, branch: str, nb_path: str, modified: dict):
    """Looks for markdown cells. Then adds or updates Colab badge code.
    """
    cells = data['cells']  # get cells
    for cell in cells:
        # Check only markdown cells
        if cell['cell_type'] == 'markdown':
            if cell['metadata']:
                # If a cell already has a badge - check the repo and branch
                if cell['metadata'].get('badge'):
                    # Update repo, branch, file path
                    print(f'Updating {nb_path} badge info...')
                    update_badge(cell, repo_name, branch, nb_path)
                    # Update cell badge meta
                    update_meta(cell, repo_name, branch, nb_path)
                    modified.update({nb_path: data})
                    continue
            # Add badge code, add metadata
            add_badge(cell, repo_name, branch, nb_path)
            modified.update({nb_path: data})
        else:
            continue


def add_badge(cell: dict, repo_name: str, branch: str, nb_path: str):
    """Inserts "Open in Colab" badge.
    """
    pattern = '{{ badge }}'  # badge variable
    text = cell['source']
    for i, line in enumerate(text):
        if pattern in line:
            badge = prepare_badge_code(repo_name, branch, nb_path)
            print(f'Inserting badge for {nb_path}...')
            new_line = line.replace(pattern, badge)
            # Add metadata about cell
            text[i] = new_line
            add_meta(cell, repo_name, branch, nb_path)
        else:
            continue


def add_meta(cell: dict, repo_name: str, branch: str, nb_path: str) -> None:
    """Adds meta to cell with a badge.
    """
    meta = {
        'badge': True,
        'repo_name': repo_name,
        'branch': branch,
        'nb_path': nb_path,
        'comment': 'This badge cell was added by colab-badge-action',
    }
    cell['metadata'].update(meta)


def update_badge(cell: dict, repo_name: str, branch: str, nb_path: str):
    """Updates already added by action badge code.
    """
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
                        new_line = line.replace(link, code)
                        text[i] = new_line
                else:
                    continue
        else:
            continue


def update_meta(cell: dict, repo_name: str, branch: str, nb_path: str):
    """Updates cell badge metadata
    """
    current_repo = cell['metadata']['repo_name']
    current_branch = cell['metadata']['branch']
    current_nb_path = cell['metadata']['nb_path']

    # Update cell metadata
    for new, curr in zip([repo_name, branch, nb_path], [current_repo, current_branch, current_nb_path]):
        if new != curr:
            cell['metadata'].update({new: new})


def write_nb(data: dict, file_path: str) -> None:
    """Saves modified jupyter notebook.
    """
    with open(file_path, 'w') as f:
        json.dump(data, f)


def commit_changes(nbs: list):
    """Commits changes.
    """
    set_email = 'git config --local user.email "colab-badge-action@master"'
    set_user = 'git config --local user.name "Colab Badge Action"'

    sp.call(set_email, shell=True)
    sp.call(set_user, shell=True)

    nbs = ' '.join(set(nbs))
    git_add = f'git add {nbs}'
    git_commit = 'git commit -m "Add/Update Colab badges"'

    print(f'Committing {nbs}...')

    sp.call(git_add, shell=True)
    sp.call(git_commit, shell=True)


def push_changes():
    """Pushes commit.
    """
    remote_repo = f'"https://{GITHUB_ACTOR}:{GITHUB_TOKEN}@github.com/{GITHUB_REPOSITORY}.git"'
    git_push = f'git push {remote_repo} HEAD:{GITHUB_REF}'

    sp.call(git_push, shell=True)


if __name__ == '__main__':
    main()
