import importlib.util
from pathlib import Path


def _load_dependency_diagram_module():
    root = Path(__file__).resolve().parents[1]
    module_path = root / "tools" / "generate_dependency_diagram.py"
    spec = importlib.util.spec_from_file_location("generate_dependency_diagram", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load dependency diagram generator module.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generated_dependency_diagram_is_current():
    root = Path(__file__).resolve().parents[1]
    module = _load_dependency_diagram_module()

    expected = module.generate_markdown()
    actual = (root / "design_documentation" / "generated_module_dependencies.md").read_text(encoding="utf-8")

    assert actual == expected
