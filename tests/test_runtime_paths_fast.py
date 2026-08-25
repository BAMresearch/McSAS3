from pathlib import Path

from mcsas3.runtime_paths import example_configuration_path, quickstart_testdata_path, runtime_resource_root


def test_runtime_resource_paths_resolve_checkout_resources():
    root = runtime_resource_root()

    assert root == Path(__file__).resolve().parents[1]
    assert example_configuration_path("read_config_csv.yaml").is_file()
    assert example_configuration_path("hist_config_dual.yaml").is_file()
    assert quickstart_testdata_path("quickstartdemo1.csv").is_file()
