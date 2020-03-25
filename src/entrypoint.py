import os
import subprocess as sp


SRC = '"https://colab.research.google.com/assets/colab-badge.svg"'
ALT = '"Open In Colab"'


def main():
    GITHUB_REPOSITORY = os.environ['GITHUB_REPOSITORY']
    GITHUB_REF = os.environ['GITHUB_REF']
    _, BRANCH = GITHUB_REF.rsplit('/', 1)

    notebooks = get_nb_list()
    updated_nbs = []

    for nb in notebooks:
        # Import notebook data
        nb_data = read_nb(nb)
        # Generate badge code
        badge = prepare_badge_code(GITHUB_REPOSITORY, BRANCH, nb)
        # Insert badge
        nb_data = insert_badge(nb_data, badge)
        # Export notebook
        write_nb(nb_data, nb, updated_nbs)

    commit_changes(updated_nbs)
    push_changes()


def get_nb_list() -> list:
    """Get list of all the changed notebooks in a current commit.
    """
    cmd = 'git diff-tree --no-commit-id --name-only -r HEAD'
    committed_files = sp.getoutput(cmd).split('\n')
    nbs = [nb for nb in committed_files if nb.endswith('.ipynb')]
    return nbs


def read_nb(file_path) -> str:
    """Reads jupyter notebook file.
    """
    with open(file_path, 'r') as f:
        data = f.read()
    return data


def prepare_badge_code(repo_name: str, branch: str, nb_path: str):
    """Prepares right html code for the badge.
    """
    href = f'"https://colab.research.google.com/github/{repo_name}/blob/{branch}/{nb_path}"'
    code = f'<a href={href} target="_parent"><img src={SRC} alt={ALT}/></a>'
    return code


def insert_badge(data: str, badge_code: str) -> str:
    """Inserts colab badge.
    """
    return '\n'.join([data, badge_code])


def write_nb(data: str, file_path: str, nbs: list):
    """Saves changed jupyter notebook.
    """
    with open(file_path, 'w') as f:
        f.write(data)
    nbs.append(file_path)


def commit_changes(nbs: list):
    """Commits changes.
    """
    set_email = 'git config --local user.email "colab-badge-action@master"'
    set_user = 'git config --local user.name "Colab Badge Action"'

    sp.call(set_email, shell=True)
    sp.call(set_user, shell=True)

    nbs = ' '.join(nbs)
    git_add = f'git add {nbs}'
    git_commit = 'git commit -m "Add Colab badge"'

    sp.call(git_add, shell=True)
    sp.call(git_commit, shell=True)


def push_changes():
    """Pushes commit.
    """
    GITHUB_ACTOR = os.environ['GITHUB_ACTOR']
    GITHUB_TOKEN = os.environ['INPUT_GITHUB_TOKEN']
    GITHUB_REPOSITORY = os.environ['GITHUB_REPOSITORY']
    GITHUB_REF = os.environ['GITHUB_REF']

    remote_repo = f'"https://{GITHUB_ACTOR}:{GITHUB_TOKEN}@github.com/{GITHUB_REPOSITORY}.git"'
    git_push = f'git push {remote_repo} HEAD:{GITHUB_REF}'

    sp.call(git_push, shell=True)


if __name__ == '__main__':
    main()
