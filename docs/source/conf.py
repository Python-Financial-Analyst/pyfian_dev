# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import subprocess
import sys
import pyfian

# ---------------------------------------------------------------------------
# Make the project-level notebooks/ directory accessible inside the Sphinx
# source tree by creating a junction (Windows) or symlink (Unix/macOS) at
# docs/source/notebooks -> <project_root>/notebooks.
# The link is transient (ignored by git) and is recreated automatically.
# ---------------------------------------------------------------------------
_source_dir = os.path.dirname(os.path.abspath(__file__))
_notebooks_link = os.path.join(_source_dir, "notebooks")
_notebooks_target = os.path.abspath(os.path.join(_source_dir, "..", "..", "notebooks"))

if not os.path.exists(_notebooks_link):
    if sys.platform == "win32":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", _notebooks_link, _notebooks_target],
            check=True,
        )
    else:
        os.symlink(_notebooks_target, _notebooks_link)

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Python Financial Analyst"
copyright = "2025, Pablo Orazi/Panteleymon Semka"
author = "Pablo Orazi/Panteleymon Semka"
release = pyfian.__version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "myst_nb",
    "autoapi.extension",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.mathjax",
    "sphinx.ext.doctest",
]

mathjax_config = {
    "tex2jax": {
        "inlineMath": [["$", "$"], ["\\(", "\\)"]],
        "displayMath": [["$$", "$$"], ["\\[", "\\]"]],
        "processEscapes": True,
    }
}
myst_enable_extensions = [
    "dollarmath",
    "amsmath",
]

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

autoapi_dirs = ["../../src/pyfian"]
autodoc_inherit_docstrings = True

autodoc_default_options = {
    "members": True,
    "inherited-members": True,
}

templates_path = ["_templates"]
exclude_patterns = []


nb_execution_mode = "cache"
# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
