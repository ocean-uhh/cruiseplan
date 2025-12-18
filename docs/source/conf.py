# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

# -- Path setup --------------------------------------------------------------
# Should not need to add paths if the docs.yml and docs_deploy.yml install the package.
# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here.
# Critical for local builds to find the package without installation
# import os
# import sys
# sys.path.insert(0, os.path.abspath('../..'))
# sys.path.insert(0, os.path.abspath('..'))

# Get version from package
try:
    from cruiseplan._version import __version__

    release = __version__
    version = __version__.split(".")[0:2]  # Short version (e.g., "0.1")
    version = ".".join(version)
    print(f"✓ Sphinx: Using version {version}, release {release}")
except ImportError:
    release = "unknown"
    version = "unknown"
    print("⚠ Sphinx: Could not import version, using 'unknown'")

# -- Project information -----------------------------------------------------
project = f"CruisePlan v{version}"
author = "Eleanor Frajka-Williams, Yves Sorge"
copyright = " "  # Single space to avoid empty string issues

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration
extensions = [
    "sphinx.ext.autodoc",  # Core library for html generation from docstrings
    "sphinx.ext.napoleon",  # Support for NumPy and Google style docstrings
    "sphinx.ext.viewcode",  # Add links to highlighted source code
    "sphinx.ext.todo",  # Support for todo items
    "sphinx_rtd_theme",  # Read the Docs theme
    "myst_parser",  # Markdown support (optional, for .md files)
    "nbsphinx",  # Jupyter Notebook support
]

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]


source_suffix = {
    ".rst": "restructuredtext",
    ".txt": "markdown",
    ".md": "markdown",
}

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ["_build"]

# If true, '()' will be appended to :func: etc. cross-reference text.
# add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
# add_module_names = True


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output
html_theme = "sphinx_rtd_theme"

# Theme configuration
html_theme_options = {
    "display_version": True,
    "prev_next_buttons_location": "bottom",
    "style_external_links": False,
    "collapse_navigation": True,
    "sticky_navigation": True,
    "navigation_depth": 4,
    "includehidden": True,
    "titles_only": False,
    "version_selector": True,
    "language_selector": True,
}

# Ensure version is displayed
html_show_sourcelink = False
html_show_sphinx = True

# Disable copyright footer
html_show_copyright = False

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

# Custom styling and logo
html_css_files = [
    "css/custom.css",
]
# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
html_logo = "_static/cruise_plan_logo.png"

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = f"{project} v{release}"

# A shorter title for the navigation bar.  Default is the same as html_title.
# html_short_title = None

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
# html_last_updated_fmt = '%b %d, %Y'

# If false, no index is generated.
# html_use_index = True

# If true, the index is split into individual pages for each letter.
# html_split_index = False

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
# html_favicon = None

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
# html_show_copyright = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
# html_show_sphinx = True

# -- Extension configuration -------------------------------------------------
# Napoleon settings to handle your NumPy style docstrings
napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True

# Todo settings
todo_include_todos = True

# If true, keep warnings as "system message" paragraphs in the built documents.
# keep_warnings = False


# -- Options for LaTeX output ---------------------------------------------
latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    # 'papersize': 'letterpaper',
    # The font size ('10pt', '11pt' or '12pt').
    # 'pointsize': '10pt',
    # Additional stuff for the LaTeX preamble.
    # 'preamble': '',
}

latex_documents = [
    (
        "index",
        "CruisePlanDocumentation.tex",
        "CruisePlan Documentation",
        author,
        "manual",
    ),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
# latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
# latex_use_parts = False

# If true, show page references after internal links.
# latex_show_pagerefs = False

# If true, show URL addresses after external links.
# latex_show_urls = False

# Documents to append as an appendix to all manuals.
# latex_appendices = []

# If false, no module index is generated.
# latex_domain_indices = True
