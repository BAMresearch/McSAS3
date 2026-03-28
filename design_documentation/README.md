# McSAS3 Design Documentation

This directory captures the current internal shape of McSAS3 and the most important
refactor target currently in scope: replacing the internal measurement containers with the
MoDaCor `ProcessingData` / `DataBundle` / `BaseData` model.

Documents in this directory:

- `upgrade_plan.md`: living stepwise upgrade plan for McSAS3 and coordinated McSAS3GUI work.
- `current_architecture.md`: current package layout, runtime flow, storage layout, and GUI
  coupling points.
- `canonical_data_contract.md`: agreed canonical `ProcessingData` stage names, bundle keys,
  default units, and transitional adapter rules.
- `modacor_data_model_migration.md`: proposed migration target, recommended data mapping,
  and a staged plan for moving McSAS3 off the legacy `measData` dict and mixed
  `DataFrame`/dict state.

This is an internal engineering baseline, not user-facing documentation.
