"""
Sphinx configuration file for the SlideDeck AI documentation.
This file sets up Sphinx to generate documentation from the source code
located in the 'src' directory, and includes support for Markdown files
using the MyST parser.
"""
import os
import sys

# --- Path setup ---
# Crucial: This tells Sphinx to look in 'src' to find the 'slidedeckai' package.
sys.path.insert(0, os.path.abspath('../src'))

# --- Project information ---
project = 'SlideDeck AI'
copyright = '2025, Barun Saha'
author = 'Barun Saha'

# --- General configuration ---
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.napoleon',    # Converts Google/NumPy style docstrings
    'sphinx.ext.viewcode',
    'myst_parser',            # Enables Markdown support (.md files)
]
autosummary_generate = True

# --- Autodoc configuration for sorting ---
autodoc_member_order = 'alphabetical'

# Tell Sphinx to look for custom templates
templates_path = ['_templates']

# Configure MyST to allow cross-referencing and nested structure
myst_enable_extensions = [
    'deflist',
    'html_image',
    'linkify',
    'replacements',
    'html_admonition'
]
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

html_theme = 'pydata_sphinx_theme'
master_doc = 'index'
html_show_sourcelink = True
