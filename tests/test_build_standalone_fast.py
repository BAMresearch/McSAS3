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


def test_build_standalone_uses_modacor_env_override(monkeypatch, tmp_path):
    module = _load_build_standalone_module()
    monkeypatch.setenv("MCSAS3_MODACOR_SRC", str(tmp_path))
    assert module._modacor_src_dir() == tmp_path.resolve()


def test_build_standalone_uses_local_sasmodels_hook(monkeypatch, tmp_path):
    module = _load_build_standalone_module()
    monkeypatch.setenv("MCSAS3_MODACOR_SRC", str(tmp_path))
    args = module._pyinstaller_args("demo", Path("demo.py"), tmp_path, ())
    assert "--additional-hooks-dir" in args
    assert str(module.HOOKS_DIR) in args
    assert "--collect-all" not in args
