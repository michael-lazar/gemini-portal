import os

from quart import render_template

from geminiportal.handlers.gemini import (
    GeminiFixedHandler,
    GeminiFlowedHandler,
    GeminiFlowedHandler2,
)
from geminiportal.handlers.text import TextHandler
from geminiportal.urls import URLReference

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def load_file(name: str) -> str:
    with open(os.path.join(DATA_DIR, name)) as fp:
        return fp.read()


async def load_response(name: str) -> str:
    content = load_file(name)
    data = await render_template("proxy/base.html", content=content)
    return data


sample_data = load_file("sample.gmi").encode()


async def test_text_fixed_handler(app):
    url = URLReference("gemini://mozz.us/test/file.gmi")
    handler = TextHandler(url, sample_data, "text/gemini", "UTF-8")
    async with app.app_context():
        response = await handler.render()
        body = await response.data
        assert body.decode() == await load_response("text_fixed.html")


async def test_gemini_fixed_handler(app):
    url = URLReference("gemini://mozz.us/test/file.gmi")
    handler = GeminiFixedHandler(url, sample_data, "text/gemini", "UTF-8")
    async with app.app_context():
        response = await handler.render()
        body = await response.data
        assert body.decode() == await load_response("gemini_fixed.html")


async def test_gemini_flowed_handler(app):
    url = URLReference("gemini://mozz.us/test/file.gmi")
    handler = GeminiFlowedHandler(url, sample_data, "text/gemini", "UTF-8")
    async with app.app_context():
        response = await handler.render()
        body = await response.data
        assert body.decode() == await load_response("gemini_flowed.html")


async def test_gemini_flowed_handler_2(app):
    url = URLReference("gemini://mozz.us/test/file.gmi")
    handler = GeminiFlowedHandler2(url, sample_data, "text/gemini", "UTF-8")
    async with app.app_context():
        response = await handler.render()
        body = await response.data
        assert body.decode() == await load_response("gemini_flowed_inline.html")
