# Colab Badge GitHub Action

[![Unit Tests](https://github.com/trsvchn/colab-badge-action/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/trsvchn/colab-badge-action/actions/workflows/unit-tests.yml)
[![codecov](https://codecov.io/gh/trsvchn/colab-badge-action/branch/dev/graph/badge.svg?token=2W6CRFZ7CB)](https://codecov.io/gh/trsvchn/colab-badge-action)

Adds "Open in Colab" badges to Jupyter Notebooks. Updates badges for renamed or moved notebooks.

## Usage

### Badge Tag

Inside a markdown cell add a double braces `{{ badge }}` tag to indicate the position for the badge:

![Add tag](assets/img1.png)

Action will create a badge for you:

![With badge](assets/img2.png)

You can use it inside a text as well:

![Add tag](assets/img3.png)

![With badge](assets/img4.png)

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
        uses: trsvchn/colab-badge-action@v3
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
