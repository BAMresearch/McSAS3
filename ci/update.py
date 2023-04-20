#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Updates any files with templates in <project root>/ci/templates directory by
# running 'python3 ci/update.py --no-env'
# Typically, github workflow files are generated with the help of tox and its config.
import os
import pathlib
import subprocess
import sys

import jinja2
import toml
import yaml

base_path: pathlib.Path = pathlib.Path(__file__).resolve().parent.parent
templates_path = base_path / "ci" / "templates"


def check_call(args):
    print("+", *args)
    subprocess.check_call(args)


def exec_in_env():
    env_path = base_path / ".tox" / "bootstrap"
    if sys.platform == "win32":
        bin_path = env_path / "Scripts"
    else:
        bin_path = env_path / "bin"
    if not env_path.exists():
        import subprocess

        print("Making bootstrap env in: {0} ...".format(env_path))
        try:
            check_call([sys.executable, "-m", "venv", env_path])
        except subprocess.CalledProcessError:
            try:
                check_call([sys.executable, "-m", "virtualenv", env_path])
            except subprocess.CalledProcessError:
                check_call(["virtualenv", env_path])
        print("Installing `jinja2` into bootstrap environment...")
        check_call([bin_path / "pip", "install", "jinja2", "tox"])
    python_executable = bin_path / "python"
    if not python_executable.exists():
        python_executable = python_executable.with_suffix(".exe")

    print("Re-executing with: {0}".format(python_executable))
    print("+ exec", python_executable, __file__, "--no-env")
    os.execv(python_executable, [python_executable, __file__, "--no-env"])


def loadYaml(filepath: pathlib.Path):
    if not filepath.is_file():
        return {}
    with open(filepath, "r") as fh:
        try:
            return yaml.safe_load(fh)
        except yaml.YAMLError as exc:
            print(exc)
            return {}


def main():
    print("Project path: {0}".format(base_path))
    # use pyproject.toml as source for paths and urls
    project_meta = toml.load(base_path / "pyproject.toml")
    # use cookiecutter cfg to file template params not rendered yet
    cc = loadYaml(base_path / ".cookiecutterrc")
    pypi_host = cc.get("default_context", {}).get("pypi_host", "").split(".")[:-1]

    jinja = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(templates_path)),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )

    tox_environments = [
        line.strip()
        # 'tox' need not be installed globally, but must be importable
        # by the Python that is running this script.
        for line in subprocess.check_output(
            [sys.executable, "-m", "tox", "--listenvs"], universal_newlines=True
        ).splitlines()
    ]
    # add a version number to the generic Python3 name (just 'py') for templates to build ok
    tox_environments = [
        (line if len(line) > 2 else line + "".join(sys.version.split(".")[:2]))
        for line in tox_environments
        if line.startswith("py")
    ]

    for template in templates_path.rglob("*"):
        if template.is_file() and template.name != ".DS_Store":
            template_path = str(template.relative_to(templates_path))
            destination = base_path / template_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                jinja.get_template(template_path).render(
                    tox_environments=tox_environments,
                    docs_url=project_meta["project"]["urls"]["documentation"],
                    cov_report_path=project_meta["tool"]["coverage"]["report"]["path"],
                    # Python version to use for general tasks: docs (when tox did not set one)
                    py_ver=".".join(sys.version.split(".")[:2]),
                    pypi_token=(
                        "_".join(pypi_host + ["token"]).upper()
                        if len(pypi_host)
                        else "TEST_PYPI_TOKEN"
                    ),
                    pypi_repo="".join(pypi_host) if len(pypi_host) else "testpypi",
                )
            )
            print("Wrote {}".format(template_path))
    print("DONE.")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args == ["--no-env"]:
        main()
    elif not args:
        exec_in_env()
    else:
        print("Unexpected arguments {0}".format(args), file=sys.stderr)
        sys.exit(1)
