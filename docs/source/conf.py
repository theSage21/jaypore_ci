# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Jaypore CI"
copyright = "2022, Arjoonn Sharma"
author = "Arjoonn Sharma"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ["sphinx.ext.autodoc", "sphinx.ext.autosummary"]

templates_path = ["_templates"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_sidebars = {
    "**": [
        "about.html",
        "navigation.html",
        "relations.html",
        "searchbox.html",
        "donate.html",
    ]
}
html_theme = "alabaster"
html_static_path = ["_static"]
html_theme_options = {
    "logo": "logo.png",
    "logo_name": "Jaypore CI",
    "touch_icon": "logo.png",
    "github_user": "theSage21",
    "github_repo": "jaypore_ci",
    "github_banner": True,
    "github_button": True,
    "description": "Simple, flexible, powerful; Like the city of Jaypore.",
}
