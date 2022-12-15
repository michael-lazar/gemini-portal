import pytest
from pytest_socket import disable_socket

from geminiportal.app import app as _app


def pytest_addoption(parser):
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="run integration tests",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: mark test as integration")


def pytest_runtest_setup(item):
    if "integration" not in item.keywords:
        disable_socket(allow_unix_socket=True)


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-integration"):
        # Collect all tests, including integration tests
        return

    skip_integration = pytest.mark.skip(reason="integration test")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)


@pytest.fixture()
def app():
    _app.config["DEBUG"] = True
    _app.config["TESTING"] = True
    return _app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()
