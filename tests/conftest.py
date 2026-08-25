import pytest

INTEGRATION_TEST_FILES = {"test_optimizer_integraltest.py"}


def pytest_addoption(parser):
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests that exercise multiple layers or file-backed workflows.",
    )
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="Run explicitly slow tests. Implies --run-integration.",
    )


def pytest_ignore_collect(collection_path, config):
    run_slow = config.getoption("--run-slow")
    run_integration = config.getoption("--run-integration") or run_slow

    if not run_integration and collection_path.name in INTEGRATION_TEST_FILES:
        return True

    return False


def pytest_collection_modifyitems(config, items):
    run_slow = config.getoption("--run-slow")
    run_integration = config.getoption("--run-integration") or run_slow

    skipped = []
    selected = []

    for item in items:
        is_integration = item.get_closest_marker("integration") is not None
        is_slow = item.get_closest_marker("slow") is not None

        if is_slow and not run_slow:
            item.add_marker(pytest.mark.skip(reason="need --run-slow option to run"))
            skipped.append(item)
            continue

        if is_integration and not run_integration:
            item.add_marker(pytest.mark.skip(reason="need --run-integration option to run"))
            skipped.append(item)
            continue

        selected.append(item)

    if skipped:
        config.hook.pytest_deselected(items=skipped)
        items[:] = selected
