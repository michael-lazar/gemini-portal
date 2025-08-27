import re

from quart import escape

from geminiportal.handlers.base import TemplateHandler
from geminiportal.urls import URLReference

# URLs that will be auto-detected in plain text responses
URL_SCHEMES = [
    "gemini",
    "spartan",
    "gopher",
    "gophers",
    "finger",
    "telnet",
    "text",
    "http",
    "https",
    "cso",
]

URL_PLACEHOLDER = "__URL_PLACEHOLDER__"


class PlaintextLinkConverter:
    url_re = re.compile(rf"(?:{'|'.join(URL_SCHEMES)})://\S+[\w/]", flags=re.UNICODE)
    placeholder_re = re.compile(URL_PLACEHOLDER)

    def __init__(self, text: str):
        self.text = text
        self.links: list[str] = []

    def convert(self) -> str:
        # Step 1. Replace any links in the text with a placeholder string.
        if URL_PLACEHOLDER not in self.text:
            self.text = self.url_re.sub(self._insert_placeholder, self.text)

        # Step 2. Escape the entire thing
        self.text = escape(self.text)

        self.links.reverse()
        if not self.links:
            return self.text

        # Step 3. Replace the placeholder strings with escaped anchor tags
        self.text = self.placeholder_re.sub(self._insert_anchor, self.text)

        return self.text

    def _insert_placeholder(self, match: re.Match) -> str:
        self.links.append(match.group())
        return URL_PLACEHOLDER

    def _insert_anchor(self, _) -> str:
        link = self.links.pop()
        link_safe = escape(link)

        try:
            url = URLReference(link)
        except ValueError:
            return link_safe  # Invalid URL, skip adding the anchor tag
        else:
            url = escape(url.get_proxy_url())
            return f'<a href="{url}">{link_safe}</a>'


class TextHandler(TemplateHandler):
    """
    Everything in a single <pre> block, with URLs converted into links.
    """

    template = "proxy/handlers/text.html"

    def get_context(self):
        context = super().get_context()
        context["body"] = self.get_body()
        return context

    def get_body(self) -> str:
        converter = PlaintextLinkConverter(self.text)
        return converter.convert()
