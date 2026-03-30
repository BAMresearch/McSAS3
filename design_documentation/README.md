# McSAS3 Design Documentation

This directory captures the current internal shape of McSAS3 and the most important
refactor target currently in scope: replacing the internal measurement containers with the
MoDaCor `ProcessingData` / `DataBundle` / `BaseData` model.

Documents in this directory:

- `upgrade_plan.md`: living stepwise upgrade plan for McSAS3 and coordinated McSAS3GUI work.
- `generated_module_dependencies.md`: generated Mermaid diagram of current top-level module
  dependencies in `src/mcsas3`; regenerate it with `python tools/generate_dependency_diagram.py`.
- `current_architecture.md`: historical package layout and runtime flow captured before the final
  `McData*` retirement; preserved for migration context.
- `canonical_data_contract.md`: agreed canonical `ProcessingData` stage names, bundle keys,
  default units, and current canonical workflow rules.
- `modacor_data_model_migration.md`: historical migration rationale and staging notes from the
  period when `McData*` still existed in the core repo.

This is an internal engineering baseline, not user-facing documentation.
