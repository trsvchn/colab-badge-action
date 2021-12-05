import os

from lib import (
    Badge,
    File,
    Patterns,
    check_cells,
    check_md,
    get_all_mds,
    get_all_nbs,
    get_modified_mds,
    get_modified_nbs,
    read_file,
    write_file,
)


def main():
    # Set repository
    CURRENT_REPOSITORY = os.environ["GITHUB_REPOSITORY"]
    TARGET_REPOSITORY = os.environ["INPUT_TARGET_REPOSITORY"] or CURRENT_REPOSITORY
    # Set branches
    GITHUB_REF = os.environ["GITHUB_REF"]
    GITHUB_HEAD_REF = os.environ["GITHUB_HEAD_REF"]
    CURRENT_BRANCH = GITHUB_HEAD_REF or GITHUB_REF.rsplit("/", 1)[-1]
    TARGET_BRANCH = os.environ["INPUT_TARGET_BRANCH"] or CURRENT_BRANCH
    # Check all or latest
    CHECK = os.environ["INPUT_CHECK"]  # 'all' | 'latest'
    # Track badges info (works only for notebooks with "self-badges").
    TRACK = {"true": True, "false": False}.get(os.environ["INPUT_TRACK"], True)  # True | False

    if CHECK == "all":
        nbs = get_all_nbs()
        mds = get_all_mds()
    elif CHECK == "latest":
        nbs = get_modified_nbs()
        mds = get_modified_mds()
    else:
        raise ValueError(f"{CHECK} is a wrong value. Expecting all or latest")

    badge = Badge()
    patterns = Patterns()

    if nbs:
        for nb in nbs:
            # Import notebook data.
            print(f"{nb}: Checking...")
            nb_data = read_file(nb)
            file = File(path=nb, type="notebook", track=TRACK, branch=TARGET_BRANCH, repo=TARGET_REPOSITORY)
            # Add badge to the right places, add right meta to the corresponding cell.
            cells = check_cells(cells=nb_data["cells"], file=file, badge=badge, patterns=patterns)
            # Export if modified.
            if cells:
                nb_data["cells"] = cells
                print(f"{nb}: Saving modified...")
                write_file(nb_data, nb)
            else:
                print(f"{nb}: Nothing to add!")
    if mds:
        for md in mds:
            print(f"{md}: Checking...")
            md_data = read_file(md)
            file = File(path=md, type="md", track=TRACK, branch=TARGET_BRANCH, repo=TARGET_REPOSITORY)
            text = check_md(text=[*md_data], file=file, badge=badge, patterns=patterns)
            if text:
                md_data = text
                print(f"{md}: Saving...")
                write_file(md_data, md)
            else:
                print(f"{md}: Nothing to add!")


if __name__ == "__main__":
    main()
