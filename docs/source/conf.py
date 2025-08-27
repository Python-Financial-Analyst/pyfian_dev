# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import pyfian

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

templates_path = ["_templates"]
exclude_patterns = []


nb_execution_mode = "cache"
# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
