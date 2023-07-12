from collections.abc import Iterable

from geminiportal.handlers.base import TemplateHandler
from geminiportal.utils import parse_link_line


class NexHandler(TemplateHandler):
    """
    Everything in a single <pre> block, with => links supported.
    """

    template = "proxy/handlers/nex.html"

    def get_context(self):
        context = super().get_context()
        context["content"] = self.iter_content()
        return context

    def iter_content(self) -> Iterable[dict]:
        for line in self.text.splitlines(keepends=False):
            line = line.rstrip()
            if line.startswith("=>"):
                url, link_text, prefix = parse_link_line(line[2:], self.url)
                yield {
                    "item_type": "a",
                    "url": url.get_proxy_url(),
                    "external_indicator": url.get_external_indicator(),
                    "text": link_text,
                    "prefix": prefix,
                }
            else:
                yield {
                    "item_type": "p",
                    "text": line,
                }
