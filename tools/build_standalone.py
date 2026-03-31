#!/usr/bin/env python3
"""Build standalone CLI bundles for the supported McSAS3 entry points."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import importlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
HOOKS_DIR = ROOT / "tools" / "pyinstaller_hooks"
BUILD_ROOT = ROOT / "build" / "standalone"
DIST_ROOT = ROOT / "dist" / "standalone"
os.environ.setdefault("PYINSTALLER_CONFIG_DIR", str(BUILD_ROOT / "pyinstaller-cache"))
os.environ.setdefault("MPLCONFIGDIR", str(BUILD_ROOT / "matplotlib-cache"))

ENTRYPOINTS = (
    (
        "mcsas3-runner",
        ROOT / "src" / "mcsas3" / "mcsas3_cli_runner.py",
        ("plotly", "IPython", "jedi", "nbformat", "jsonschema", "zmq"),
    ),
    (
        "mcsas3-histogrammer",
        ROOT / "src" / "mcsas3" / "mcsas3_cli_histogrammer.py",
        (),
    ),
)


def _platform_tag() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower().replace("x86_64", "amd64")
    return f"{system}-{machine}"


def _add_data_arg(source: Path, destination: str) -> str:
    return f"{source}{':' if platform.system() != 'Windows' else ';'}{destination}"


def _bundle_root() -> Path:
    return DIST_ROOT / _platform_tag()


def _modacor_src_dir() -> Path:
    configured = os.environ.get("MCSAS3_MODACOR_SRC")
    if configured:
        return Path(configured).expanduser().resolve()
    return ROOT.parent / "MoDaCor" / "src"


def _require_modacor_src() -> Path:
    modacor_src_dir = _modacor_src_dir()
    if not modacor_src_dir.is_dir():
        raise RuntimeError(
            "Standalone builds require the MoDaCor source tree. "
            f"Set MCSAS3_MODACOR_SRC or provide the sibling checkout at '{modacor_src_dir}'."
        )
    return modacor_src_dir


def _pyinstaller_args(name: str, script_path: Path, bundle_root: Path, excluded_modules: tuple[str, ...]) -> list[str]:
    modacor_src = _require_modacor_src()
    args = [
        "--noconfirm",
        "--clean",
        "--onedir",
        "--name",
        name,
        "--paths",
        str(SRC_DIR),
        "--paths",
        str(modacor_src),
        "--additional-hooks-dir",
        str(HOOKS_DIR),
        "--distpath",
        str(bundle_root / "apps"),
        "--workpath",
        str(BUILD_ROOT / "work"),
        "--specpath",
        str(BUILD_ROOT / "spec"),
        "--hidden-import",
        "modacor",
        "--hidden-import",
        "modacor.units",
        "--hidden-import",
        "modacor.dataclasses.basedata",
        "--hidden-import",
        "modacor.dataclasses.databundle",
        "--hidden-import",
        "modacor.dataclasses.processing_data",
        "--add-data",
        _add_data_arg(ROOT / "example_configurations", "example_configurations"),
        "--add-data",
        _add_data_arg(ROOT / "testdata" / "quickstartdemo1.csv", "testdata"),
        str(script_path),
    ]
    for module_name in excluded_modules:
        args.extend(["--exclude-module", module_name])
    return args


def _write_bundle_readme(bundle_root: Path) -> None:
    lines = [
        "McSAS3 standalone CLI bundle",
        "",
        "Included executables:",
        "- apps/mcsas3-runner/",
        "- apps/mcsas3-histogrammer/",
        "",
        "Each executable directory also includes bundled example configurations and quickstart data",
        "so the built-in default CLI paths resolve correctly in standalone mode.",
        "",
        "Build prerequisite:",
        f"- sibling MoDaCor checkout at {_modacor_src_dir()}",
        "- or set MCSAS3_MODACOR_SRC to the MoDaCor src directory before building",
        "",
        "Examples:",
        "  ./apps/mcsas3-runner/mcsas3-runner --help",
        "  ./apps/mcsas3-histogrammer/mcsas3-histogrammer --help",
    ]
    (bundle_root / "README_STANDALONE.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_build_info(bundle_root: Path) -> None:
    payload = {
        "platform": _platform_tag(),
        "system": platform.system(),
        "machine": platform.machine(),
        "artifacts": [name for name, _script, _excluded_modules in ENTRYPOINTS],
    }
    (bundle_root / "build_info.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _archive_bundle(bundle_root: Path) -> Path:
    archive_base = DIST_ROOT / f"mcsas3-standalone-{bundle_root.name}"
    archive_path = Path(
        shutil.make_archive(
            str(archive_base),
            "zip",
            root_dir=bundle_root.parent,
            base_dir=bundle_root.name,
        )
    )
    return archive_path


def _pyinstaller_main():
    """Import and return the PyInstaller entry module only when building."""

    return importlib.import_module("PyInstaller.__main__")


def _run_smoke_test(bundle_root: Path) -> None:
    suffix = ".exe" if platform.system() == "Windows" else ""
    for entry_name, _script, _excluded_modules in ENTRYPOINTS:
        executable = bundle_root / "apps" / entry_name / f"{entry_name}{suffix}"
        result = subprocess.run(
            [str(executable), "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Standalone smoke test failed for {entry_name}: exit {result.returncode}\n"
                f"stdout:\n{result.stdout}\n"
                f"stderr:\n{result.stderr}"
            )


def main() -> None:
    """Build standalone CLI directories and a zip archive for the current platform."""

    bundle_root = _bundle_root()
    shutil.rmtree(BUILD_ROOT, ignore_errors=True)
    shutil.rmtree(bundle_root, ignore_errors=True)
    bundle_root.mkdir(parents=True, exist_ok=True)
    pyinstaller_main = _pyinstaller_main()

    for entry_name, script_path, excluded_modules in ENTRYPOINTS:
        pyinstaller_main.run(_pyinstaller_args(entry_name, script_path, bundle_root, excluded_modules))

    _write_bundle_readme(bundle_root)
    _write_build_info(bundle_root)
    archive_path = _archive_bundle(bundle_root)
    _run_smoke_test(bundle_root)
    print(f"Standalone bundle created at {bundle_root}")
    print(f"Standalone archive created at {archive_path}")


if __name__ == "__main__":
    main()
