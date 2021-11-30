import os

from lib import (
    ALT,
    SRC,
    check_cells,
    check_md,
    get_all_mds,
    get_all_nbs,
    get_modified_mds,
    get_modified_nbs,
    read_md,
    read_nb,
    write_md,
    write_nb,
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
    # Check and/or update
    CHECK = os.environ["INPUT_CHECK"]  # 'all' | 'latest'
    TRACK = {"true": True, "false": False}.get(os.environ["INPUT_TRACK"], True)  # True | False

    if CHECK == "all":
        nbs = get_all_nbs()
        mds = get_all_mds()
    elif CHECK == "latest":
        nbs = get_modified_nbs()
        mds = get_modified_mds()
    else:
        raise ValueError(f"{CHECK} is a wrong value. Expecting all or latest")

    if nbs:
        for nb in nbs:
            # Import notebook data
            print(f"{nb}: Checking...")
            nb_data = read_nb(nb)
            # Add badge to the right places, add right meta to the corresponding cell
            cells = check_cells(
                cells=nb_data["cells"],
                repo_name=TARGET_REPOSITORY,
                branch=TARGET_BRANCH,
                nb_path=nb,
                src=SRC,
                alt=ALT,
                track=TRACK,
            )
            # Export if modified
            if cells:
                nb_data["cells"] = cells
                print(f"{nb}: Saving modified...")
                write_nb(nb_data, nb)
            else:
                print(f"{nb}: Nothing to add!")

    if mds:
        for md in mds:
            print(f"{md}: Checking...")
            md_data = read_md(md)
            text = check_md(
                text=[*md_data],
                repo_name=TARGET_REPOSITORY,
                branch=TARGET_BRANCH,
                nb_path=md,
                src=SRC,
                alt=ALT,
                track=TRACK,
            )
            if text:
                md_data = text
                print(f"{md}: Saving...")
                write_md(md_data, md)
            else:
                print(f"{md}: Nothing to add!")


if __name__ == "__main__":
    main()
