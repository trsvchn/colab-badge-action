import os
import re

from lib import check_cells, get_all_nbs, get_modified_nbs, read_nb, write_nb


def main():
    # Badge setup
    SRC = '"https://colab.research.google.com/assets/colab-badge.svg"'
    ALT = '"Open In Colab"'
    BADGE_VAR = "{{ badge }}"
    BADGE_PATTERN = re.compile(r"<!--<badge>-->(.*?)<!--</badge>-->")
    HREF_PATTERN = re.compile(r"href=[\"\'](.*?)[\"\']")
    # Set repository
    CURRENT_REPOSITORY = os.environ["GITHUB_REPOSITORY"]
    TARGET_REPOSITORY = os.environ["INPUT_TARGET_REPOSITORY"] or CURRENT_REPOSITORY
    # Set branches
    GITHUB_REF = os.environ["GITHUB_REF"]
    GITHUB_HEAD_REF = os.environ["GITHUB_HEAD_REF"]
    CURRENT_BRANCH = GITHUB_HEAD_REF or GITHUB_REF.rsplit("/", 1)[-1]
    TARGET_BRANCH = os.environ["INPUT_TARGET_BRANCH"] or CURRENT_BRANCH
    # Check and/or update
    CHECK = os.environ["INPUT_CHECK"]  # 'all' | 'latest'
    UPDATE = {"true": True, "false": False}.get(os.environ["INPUT_UPDATE"], True)  # True | False

    if CHECK == "all":
        nbs = get_all_nbs()
    elif CHECK == "latest":
        nbs = get_modified_nbs()
    else:
        raise ValueError(f"{CHECK} is a wrong value. Expecting all or latest")

    if nbs:
        for nb in nbs:
            # Import notebook data
            print(f"{nb}: Reading...")
            nb_data = read_nb(nb)
            # Add badge to the right places, add right meta to the corresponding cell
            cells = check_cells(
                cells=nb_data["cells"],
                repo_name=TARGET_REPOSITORY,
                branch=TARGET_BRANCH,
                nb_path=nb,
                update=UPDATE,
                badge_var=BADGE_VAR,
                badge_pattern=BADGE_PATTERN,
                href_pattern=HREF_PATTERN,
                src=SRC,
                alt=ALT,
            )
            # Export if modified
            if cells:
                nb_data["cells"] = cells
                print(f"{nb}: Saving modified...")
                write_nb(nb_data, nb)


if __name__ == "__main__":
    main()
