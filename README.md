# Colab Badge GitHub Action

[![Unit Tests](https://github.com/trsvchn/colab-badge-action/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/trsvchn/colab-badge-action/actions/workflows/unit-tests.yml)
[![codecov](https://codecov.io/gh/trsvchn/colab-badge-action/branch/main/graph/badge.svg?token=2W6CRFZ7CB)](https://codecov.io/gh/trsvchn/colab-badge-action)

Adds "Open in Colab" badges to Jupyter Notebooks and Markdown files. Updates badges for renamed or moved notebooks.

## Usage

### Badge Tag

- Use `{{ badge }}` tag  to generate a badge for the notebook containing this tag (self-linking). Works only for Jupyter notebooks.

The following options work for bath Jupyter and Markdown files (new in `v4`):

- Use `{{ badge nb_path }}` tag to generate a badge for a local notebook `nb_path`, and insert it to the file containing that tag (tag will be replaced with generated badge code). e.g. `{{ badge dir1/di2/nb.ipynb }}`.
- Use `{{ badge /nb_path }}` tag to generate a badge for a remote (located in another repo) notebook `/nb_path`, and insert it to the file containing that tag. e.g. `{{ badge /usr2/repo/blob/main/nb.ipynb }}`. You can use full link (url) as well: `{{ badge https://github.com/usr2/repo/blob/main/nb.ipynb }}`.
- Use `{{ badge //drive/nb_id }}` tag to generate a badge for google drive notebook, and insert it to the file containing that tag. e.g. `{{ badge //drive/abcde }}`

Note: repo name and branch name are omitted for local notebooks, for notebooks from another repo only hostname can be ommited. In both cases file extension `.ipynb` can be omitted.

![Add tag](assets/img1.png)

Action will create a badge for you:

![With badge](assets/img2.png)

### Example Workflow

A workflow file for adding/updating badges for notebooks in a repo:

```yaml
name: Example Workflow
on: [push]

jobs:
  badges:
    name: Example Badge Job
    runs-on: ubuntu-latest
    steps:
      - name: Checkout first
        id: checkout
        uses: actions/checkout@v2

      - name: Add/Update badges
        id: badges
        uses: trsvchn/colab-badge-action@v4
        with:
          check: "all"
          target_branch: main
          target_repository: user/user-repo
          update: true

      - name: Use your favorite commit&push action here
        uses: action/commit@push
        with: ...
```

### Inputs

| Input | Description | Default |
|:------|:------------|:--------|
| `check` | Check every notebook/markdown: `"all"` or just modified files from a current commit: `"latest"`. | `"all"` | 
| `target_branch` | Branch that the badge will target. | `""` (current branch) |
| `target_repository` | Repo that the badge will target. | `""` (current repository) |
| `update` | Update a badge if a piece of information relevant to it has changedL `true`. With `false` inserts badges with no further updates (ignores changes). Works only for notebooks. | `true` |
| `verbose` | Verbose mode. Print some information during execution. | `false` |
