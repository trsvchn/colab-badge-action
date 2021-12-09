import logging
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


def setup_logger(name, formatter):
    logger = logging.getLogger(name)
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


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
    CHECK = os.environ["INPUT_CHECK"]  # "all" | "latest"
    # Track badges info (works only for notebooks with "self-badges").
    TRACK = {"true": True, "false": False}.get(os.environ["INPUT_UPDATE"], True)  # True | False
    VERBOSE = {"true": True, "false": False}.get(os.environ["INPUT_VERBOSE"], False)  # True | False

    logger_action = setup_logger(
        "action",
        logging.Formatter(fmt="%(asctime)s %(levelname)s %(message)s", datefmt="%d-%b-%y %H:%M:%S"),
    )

    logger_badge = setup_logger(
        "badge",
        logging.Formatter(fmt="::%(levelname)s file=%(file)s,line=%(line)s,title=%(title)s::%(message)s"),
    )

    if VERBOSE:
        logger_action.setLevel(logging.INFO)

    if CHECK == "all":
        logger_action.info("Getting list of all files...")
        nbs, mds = get_all_nbs(), get_all_mds()
    elif CHECK == "latest":
        logger_action.info("Getting list of latest modified files...")
        nbs, mds = get_modified_nbs(), get_modified_mds()
    else:
        raise ValueError(f"{CHECK} is a wrong value. Expecting all or latest")

    logger_action.info(f"Files: {', '.join(nbs + mds)}")

    badge, patterns = Badge(), Patterns()

    if nbs:
        for nb in nbs:
            logger_action.info(f"{nb}: Reading...")
            nb_data = read_file(nb)
            file = File(path=nb, type="notebook", track=TRACK, branch=TARGET_BRANCH, repo=TARGET_REPOSITORY)
            cells = check_cells(cells=nb_data["cells"], file=file, badge=badge, patterns=patterns, logger=logger_badge)
            if cells:
                logger_action.info(f"{nb} Saving...")
                nb_data["cells"] = cells
                write_file(nb_data, nb)
            else:
                logger_action.info(f"{nb}: Nothing to add...")
    if mds:
        for md in mds:
            logger_action.info(f"{md}: Reading...")
            md_data = read_file(md)
            file = File(path=md, type="md", track=TRACK, branch=TARGET_BRANCH, repo=TARGET_REPOSITORY)
            text = check_md(text=[*md_data], file=file, badge=badge, patterns=patterns, logger=logger_badge)
            if text:
                logger_action.info(f"{md} Saving...")
                md_data = text
                write_file(md_data, md)
            else:
                logger_action.info(f"{md}: Nothing to add...")


if __name__ == "__main__":
    main()
