import re
from collections import Counter
from collections.abc import Iterable
from typing import Any

from emoji import is_emoji
from quart import escape

from geminiportal.handlers.base import TemplateHandler
from geminiportal.urls import URLReference

RABBIT_INLINE = ":rаbbiΤ:"
RABBIT_STANDALONE = ";rаbbiΤ;"
RABBIT_ART = r"""
          /|
    /\   //
   |/\'-'/ .::.
     /^Y^\::''.
     \_ /=| `'
    /`_)=( \
    \ /=/'-/
   {/ |/  \
  __\  _  /__
 '----' '----'
"""


def parse_link_line(line: str, base: URLReference) -> tuple[URLReference, str, str]:
    # Prefix is part of the text at the beginning of the link
    # description that shouldn't be underlined.
    prefix = ""

    parts = line.split(maxsplit=1)
    if len(parts) == 0:
        link, link_text = "", ""
    elif len(parts) == 1:
        link, link_text = parts[0], parts[0]
    else:
        link, link_text = parts
        if is_emoji(link_text[0]):
            prefix = link_text[0] + " "
            link_text = link_text[1:].lstrip()

    url = base.join(link)
    return url, link_text, prefix


class GeminiFixedHandler(TemplateHandler):
    """
    Everything in a single <pre> block, with => links supported.
    """

    template = "proxy/handlers/text.html"

    def get_context(self):
        context = super().get_context()
        context["body"] = self.get_body()
        return context

    def get_body(self) -> str:
        buffer = []
        for line in self.text.splitlines(keepends=False):
            line = line.rstrip()
            if line.startswith("=>"):
                url, link_text, prefix = parse_link_line(line[2:], self.url)
                proxy_url = url.get_proxy_url()
                buffer.append(f'{prefix}<a href="{escape(proxy_url)}">{escape(link_text)}</a>')
            else:
                buffer.append(escape(line))

        body = "\n".join(buffer)
        return body


class GeminiFlowedHandler(TemplateHandler):
    """
    The full-featured gemtext -> html converter.
    """

    _rabbit_re = re.compile(RABBIT_INLINE)

    template = "proxy/handlers/gemini.html"
    inline_images = False

    line_buffer: list[str]
    active_type: str | None
    anchor_counter: Counter[str]

    def get_anchor(self, text: str) -> str:
        """
        Add link anchors to gemtext header lines.
        """
        text = text.strip()
        text = text.lower()
        text = text.replace(" ", "-")
        text = re.sub(r"[^\w-]", "", text)
        self.anchor_counter[text] += 1
        if self.anchor_counter[text] > 1:
            text += f"-{self.anchor_counter[text] - 1}"
        return text

    def get_context(self) -> dict[str, Any]:
        context = super().get_context()
        context["content"] = self.iter_content()
        return context

    def iter_content(self) -> Iterable[dict]:
        self.line_buffer = []
        self.active_type = None
        self.anchor_counter = Counter()

        for line in self.text.splitlines():
            line = line.rstrip()
            line = self._rabbit_re.sub("🐇", line)
            if line.startswith("```"):
                if self.active_type == "pre":
                    yield from self.flush()
                else:
                    yield from self.flush("pre")

            elif self.active_type == "pre":
                if line == RABBIT_STANDALONE:
                    line = RABBIT_ART
                self.line_buffer.append(line)

            elif line == RABBIT_STANDALONE:
                yield from self.flush()
                yield {
                    "item_type": "pre",
                    "lines": RABBIT_ART.splitlines(keepends=False),
                }

            elif line.startswith("=>"):
                yield from self.flush()
                url, link_text, prefix = parse_link_line(line[2:], self.url)
                mime_type = url.guess_mimetype()
                if self.inline_images and mime_type and mime_type.startswith("image"):
                    yield {
                        "item_type": "image",
                        "url": url.get_proxy_url(raw=True),
                        "text": link_text,
                        "prefix": prefix,
                    }
                else:
                    yield {
                        "item_type": "link",
                        "url": url.get_proxy_url(),
                        "text": link_text,
                        "prefix": prefix,
                    }

            elif line.startswith("=:"):
                yield from self.flush()
                url, link_text, prefix = parse_link_line(line[2:], self.url)
                yield {
                    "item_type": "prompt",
                    "url": url.get_proxy_url(),
                    "text": link_text,
                    "prefix": prefix,
                }

            elif line.startswith("###"):
                yield from self.flush()
                text = line[3:].lstrip()
                anchor = self.get_anchor(text)
                yield {"item_type": "h3", "text": text, "anchor": anchor}

            elif line.startswith("##"):
                yield from self.flush()
                text = line[2:].lstrip()
                anchor = self.get_anchor(text)
                yield {"item_type": "h2", "text": text, "anchor": anchor}

            elif line.startswith("#"):
                yield from self.flush()
                text = line[1:].lstrip()
                anchor = self.get_anchor(text)
                yield {"item_type": "h1", "text": text, "anchor": anchor}

            elif line.startswith("* "):
                yield from self.flush("ul")
                self.line_buffer.append(line[1:].lstrip())

            elif line.startswith("> ") or line == ">":
                yield from self.flush("blockquote")
                self.line_buffer.append(line[1:])

            elif line.startswith("---"):
                yield from self.flush()
                yield {"item_type": "hr"}

            else:
                yield from self.flush("p")
                self.line_buffer.append(line)

        yield from self.flush()

    def flush(self, new_type: str | None = None) -> Iterable[dict]:
        if self.active_type != new_type:
            if self.line_buffer and self.active_type:
                yield {
                    "item_type": self.active_type,
                    "lines": self.line_buffer,
                }

            self.line_buffer = []
            self.active_type = new_type


class GeminiFlowedHandler2(GeminiFlowedHandler):
    inline_images = True
