"""Local PyInstaller hook for sasmodels.

This keeps the runtime kernel/model data required by McSAS3 while avoiding
bundling sasmodels documentation trees that significantly inflate the
standalone archives.
"""

from __future__ import annotations

from sasmodels import data_files

hiddenimports = [
    "pyopencl",
    "sasmodels.compare_many",
    "sasmodels.guyou",
    "sasmodels.jitter",
    "sasmodels.list_pars",
    "sasmodels.multiscat",
    "sasmodels.special",
    "sasmodels.models.two_yukawa",
]
module_collection_mode = "py"

datas: list[tuple[str, str]] = []
for target, filenames in data_files():
    if target.endswith("/models/img"):
        continue
    for filename in filenames:
        datas.append((filename, target))
        datas.append((filename, target.replace("sasmodels-data", "sasmodels")))
