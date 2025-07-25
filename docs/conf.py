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
    "sphinx.ext.inheritance_diagram",
    "sphinx.ext.graphviz",
    "myst_parser",
]
inheritance_edge_attrs = dict(color="gray")  # readable in darkmode too
autosummary_generate = True  # Turn on sphinx.ext.autosummary
templates_path = ["_templates"]
source_suffix = ".rst"
master_doc = "index"
project = "McSAS3"
year = "2018-2025"
author = "Brian R. Pauw and Ingo Breßler"
copyright = "{0}, {1}".format(year, author)
version = "1.0.5"
release = version
commit_id = None
try:
    commit_id = (
        subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).strip().decode("ascii")
    )
except subprocess.CalledProcessError as e:
    print(e)


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
    "chempy",
    "graphviz",
    "mcsas3",
]

pygments_style = "trac"
extlinks = {
    "issue": (join(project_meta["project"]["urls"]["repository"], "issues", "%s"), "#%s"),
    "pr": (join(project_meta["project"]["urls"]["repository"], "pull", "%s"), "PR #%s"),
}
html_theme = "furo"

html_use_smartypants = True
html_last_updated_fmt = "%b %d, %Y"
if commit_id:
    html_last_updated_fmt += f" (git {commit_id})"
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
    # attempted fix of '406 Client Error: Not Acceptable for url'
    # https://github.com/sphinx-doc/sphinx/issues/1331
    join(project_meta["project"]["urls"]["repository"], "commit", r"[0-9a-fA-F]+")
]
linkcheck_anchors_ignore_for_url = [
    r"https://pypi\.org/project/[^/]+",
]
