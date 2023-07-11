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


url_re = re.compile(rf"(?:{'|'.join(URL_SCHEMES)})://[\S]+[\w/]", flags=re.UNICODE)


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
        buffer = []
        for line in self.text.splitlines(keepends=False):
            line = escape(line)
            line = url_re.sub(self.insert_anchor, line)
            buffer.append(line)

        body = "\n".join(buffer)
        return body

    def insert_anchor(self, match: re.Match) -> str:
        m = match.group()
        try:
            url = URLReference(m)
        except ValueError:
            return m  # Invalid URL, skip adding the anchor tag
        else:
            return f'<a href="{url.get_proxy_url()}">{url}</a>'
