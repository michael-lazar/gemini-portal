import os

from geminiportal.handlers import (
    GeminiFixedHandler,
    GeminiFlowedHandler,
    GeminiInlineFlowedHandler,
    TextFixedHandler,
)
from geminiportal.urls import URLReference

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def load_file(name: str) -> str:
    with open(os.path.join(DATA_DIR, name)) as fp:
        return fp.read()


SAMPLE_TEXT = load_file("sample.gmi")


async def test_text_fixed_handler(app):
    url = URLReference("gemini://mozz.us/test/file.gmi")
    handler = TextFixedHandler(SAMPLE_TEXT, url)
    async with app.app_context():
        text = handler.process()
    assert text == load_file("text_fixed.html")


async def test_gemini_fixed_handler(app):
    url = URLReference("gemini://mozz.us/test/file.gmi")
    handler = GeminiFixedHandler(SAMPLE_TEXT, url)
    async with app.app_context():
        text = handler.process()
    assert text == load_file("gemini_fixed.html")


async def test_gemini_flowed_handler(app):
    url = URLReference("gemini://mozz.us/test/file.gmi")
    handler = GeminiFlowedHandler(SAMPLE_TEXT, url)
    async with app.app_context():
        text = handler.process()
    assert text == load_file("gemini_flowed.html")


async def test_gemini_inline_flowed_handler(app):
    url = URLReference("gemini://mozz.us/test/file.gmi")
    handler = GeminiInlineFlowedHandler(SAMPLE_TEXT, url)
    async with app.app_context():
        text = handler.process()
    assert text == load_file("gemini_flowed_inline.html")
