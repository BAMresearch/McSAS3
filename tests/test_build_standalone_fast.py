from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_build_standalone_module():
    module_path = Path(__file__).resolve().parents[1] / "tools" / "build_standalone.py"
    spec = importlib.util.spec_from_file_location("build_standalone", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_standalone_uses_local_sasmodels_hook(tmp_path):
    module = _load_build_standalone_module()
    args = module._pyinstaller_args("demo", Path("demo.py"), tmp_path, ())
    assert "--additional-hooks-dir" in args
    assert str(module.HOOKS_DIR) in args
    assert "--collect-all" not in args


def test_build_standalone_explicitly_includes_modacor_hidden_imports(tmp_path):
    module = _load_build_standalone_module()
    args = module._pyinstaller_args("demo", Path("demo.py"), tmp_path, ())

    assert "modacor" in args
    assert "modacor.units" in args
    assert "modacor.dataclasses.basedata" in args
    assert "modacor.dataclasses.databundle" in args
    assert "modacor.dataclasses.processing_data" in args
