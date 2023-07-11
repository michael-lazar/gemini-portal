import os

from geminiportal.handlers.gemini import GeminiFixedHandler, GeminiFlowedHandler
from geminiportal.handlers.text import TextHandler
from geminiportal.urls import URLReference

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def load_file(name: str) -> str:
    with open(os.path.join(DATA_DIR, name)) as fp:
        return fp.read()


demo_data = load_file("demo.gmi").encode()


async def test_text_fixed_handler(app):
    url = URLReference("gemini://mozz.us/test/file.gmi")
    handler = TextHandler(url, demo_data, "text/gemini", "UTF-8")
    async with app.app_context():
        response = await handler.render()
        body = await response.data
        assert load_file("test_handlers/text_fixed.html") == body.decode()


async def test_gemini_fixed_handler(app):
    url = URLReference("gemini://mozz.us/test/file.gmi")
    handler = GeminiFixedHandler(url, demo_data, "text/gemini", "UTF-8")
    async with app.app_context():
        response = await handler.render()
        body = await response.data
        assert load_file("test_handlers/gemini_fixed.html") == body.decode()


async def test_gemini_flowed_handler(app):
    url = URLReference("gemini://mozz.us/test/file.gmi")
    handler = GeminiFlowedHandler(url, demo_data, "text/gemini", "UTF-8")
    async with app.app_context():
        response = await handler.render()
        body = await response.data
        assert load_file("test_handlers/gemini_flowed.html") == body.decode()
