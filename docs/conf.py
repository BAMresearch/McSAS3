# -*- coding: utf-8 -*-


import subprocess
from os.path import abspath, dirname, join

import toml

base_path = dirname(dirname(abspath(__file__)))
project_meta = toml.load(join(base_path, "pyproject.toml"))

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.coverage",
    "sphinx.ext.doctest",
    "sphinx.ext.extlinks",
    "sphinx.ext.ifconfig",
    "sphinx.ext.napoleon",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "myst_parser",
]
autosummary_generate = True  # Turn on sphinx.ext.autosummary
templates_path = ["_templates"]
source_suffix = ".rst"
master_doc = "index"
project = "McSAS3"
year = "2018-2023"
author = "Brian R. Pauw"
copyright = "{0}, {1}".format(year, author)
version = "1.0.2"
release = version
commit_id = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).strip().decode("ascii")

autodoc_mock_imports = [
    "ipykernel",
    "notebook",
    "pandas",
    "ipywidgets",
    "matplotlib",
    "scipy",
    "h5py",
    "pint",
    "sasmodels",
]

pygments_style = "trac"
extlinks = {
    "issue": (join(project_meta["project"]["urls"]["repository"], "issues", "%s"), "#%s"),
    "pr": (join(project_meta["project"]["urls"]["repository"], "pull", "%s"), "PR #%s"),
}
html_theme = "furo"

html_use_smartypants = True
html_last_updated_fmt = f"%b %d, %Y (git {commit_id})"
html_split_index = False
html_short_title = "%s-%s" % (project, version)

napoleon_use_ivar = True
napoleon_use_rtype = False
napoleon_use_param = False

linkcheck_ignore = [
    join(
        project_meta["project"]["urls"]["documentation"],
        project_meta["tool"]["coverage"]["report"]["path"],
    )
    + r".*",
]
