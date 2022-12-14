import pytest

from geminiportal.app import app as _app


@pytest.fixture()
def app():
    yield _app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()
