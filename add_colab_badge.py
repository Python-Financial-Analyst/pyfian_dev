"""
Automatically adds or updates a Colab badge in the first cell of Jupyter notebooks.

This script scans specified directories for .ipynb files and ensures each notebook's first cell
contains a markdown badge linking to Google Colab for the corresponding file
in the GitHub repository.

Examples
--------
Run from the root of your repository:

    python add_colab_badge.py
"""

import os

import nbformat

# Set your GitHub repo path and branch
GITHUB_REPO = "Python-Financial-Analyst/pyfian_dev"
BRANCH = "main"

TARGET_DIRS = [
    "notebooks",
    "docs/source/Topics/",
]


def expected_badge(notebook_rel_path):
    """
    Generate the markdown for a Colab badge linking to the notebook in the GitHub repo.

    Parameters
    ----------
    notebook_rel_path : str
        Relative path to the notebook from the repo root.

    Returns
    -------
    str
        Markdown string for the Colab badge.
    """
    badge = f"""
<a href="https://colab.research.google.com/github/{GITHUB_REPO}/blob/{BRANCH}/{notebook_rel_path}" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab"/>
</a>
""".strip()  # noqa: E501
    return badge


def update_notebook(path, repo_root):
    """
    Add or update the Colab badge in the first cell of a notebook.

    Parameters
    ----------
    path : str
        Absolute path to the notebook file.
    repo_root : str
        Root directory of the repository.

    Returns
    -------
    None
    """
    rel_path = os.path.relpath(path, repo_root).replace("\\", "/")
    expected = expected_badge(rel_path)

    with open(path, encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)

    cells = nb.cells

    # Case 1: First cell is markdown but wrong badge → replace it
    if cells and cells[0].cell_type == "markdown":
        if "colab-badge.svg" in cells[0].source:
            if cells[0].source.strip() != expected:
                print(f"🔄 Replacing outdated badge in: {rel_path}")
                cells[0].source = expected
            else:
                print(f"✅ Badge already correct in: {rel_path}")
                return
        else:
            # No badge, insert at the top
            print(f"➕ Inserting badge into: {rel_path}")
            cells.insert(0, nbformat.v4.new_markdown_cell(expected))
    else:
        # No cells or first cell isn't markdown
        print(f"➕ Inserting badge into: {rel_path}")
        cells.insert(0, nbformat.v4.new_markdown_cell(expected))

    # Save updated notebook
    with open(path, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)


def scan_target_dirs(base_dir, target_dirs):
    """
    Scan the given target directories for Jupyter notebooks and update their Colab badge.

    Parameters
    ----------
    base_dir : str
        Root directory of the repository.
    target_dirs : list of str
        List of subdirectories to scan for notebooks.

    Returns
    -------
    None
    """
    for target_dir in target_dirs:
        full_target_dir = os.path.join(base_dir, target_dir)
        if not os.path.isdir(full_target_dir):
            print(f"⚠️ Skipping missing directory: {full_target_dir}")
            continue
        for root, _, files in os.walk(full_target_dir):
            for file in files:
                if file.endswith(".ipynb"):
                    full_path = os.path.join(root, file)
                    update_notebook(full_path, base_dir)


if __name__ == "__main__":
    scan_target_dirs(".", target_dirs=TARGET_DIRS)
