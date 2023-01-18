import re
from collections import Counter

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


def parse_link_line(line: str, base: URLReference) -> tuple[URLReference, str]:
    parts = line.split(maxsplit=1)
    if len(parts) == 0:
        link, link_text = "", ""
    elif len(parts) == 1:
        link, link_text = parts[0], parts[0]
    else:
        link, link_text = parts

    url = base.join(link)
    return url, link_text


class GeminiFixedHandler(TemplateHandler):
    """
    Everything in a single <pre> block, with => links supported.
    """

    async def get_body(self) -> str:
        buffer = []
        for line in self.text.splitlines(keepends=False):
            line = line.rstrip()
            if line.startswith("=>"):
                url, link_text = parse_link_line(line[2:], self.url)
                proxy_url = url.get_proxy_url()
                buffer.append(f'<a href="{escape(proxy_url)}">{escape(link_text)}</a>')
            else:
                buffer.append(escape(line))

        body = "\n".join(buffer)
        return f"<pre>{body}</pre>\n"


class GeminiFlowedHandler(TemplateHandler):
    """
    The full-featured gemtext -> html converter.
    """

    inline_images = False

    _rabbit_re = re.compile(RABBIT_INLINE)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.sections: list[str] = []
        self.buffer: list[str] = []
        self.preformat_mode = False
        self.list_mode = False
        self.quote_mode = False
        self.anchor_counter: Counter[str] = Counter()

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

    async def get_body(self) -> str:
        for line in self.text.splitlines(keepends=False):
            line = line.rstrip()
            line = self._rabbit_re.sub("🐇", line)
            if line.startswith("```"):
                self.flush()
                self.preformat_mode = not self.preformat_mode
            elif self.preformat_mode:
                if line == RABBIT_STANDALONE:
                    line = RABBIT_ART
                self.buffer.append(escape(line))
            elif line == RABBIT_STANDALONE:
                self.flush()
                self.sections.append(f"<pre>{RABBIT_ART}</pre>")
            elif line.startswith("=>"):
                self.flush()
                url, link_text = parse_link_line(line[2:], self.url)
                gemini_link, link_text = parse_link_line(line[2:], self.url)
                mime_type = url.guess_mimetype()
                if self.inline_images and mime_type and mime_type.startswith("image"):
                    image_url = url.get_proxy_url(raw=True)
                    self.sections.append(
                        f'<figure><a href="{escape(image_url)}">'
                        f'<img src="{escape(image_url)}" alt="{escape(link_text)}">'
                        f"</a><figcaption>{escape(link_text)}</figcaption></figure>"
                    )
                else:
                    image_url = url.get_proxy_url()
                    self.sections.append(
                        f'<a href="{escape(image_url)}">{escape(link_text)}</a><br/>'
                    )
            elif line.startswith("=:"):
                self.flush()
                url, link_text = parse_link_line(line[2:], self.url)
                proxy_url = url.get_proxy_url()
                self.sections.append(
                    f'<form method="get" action="{escape(proxy_url)}" class="input-line">'
                    f"<label>{escape(link_text)}"
                    '<textarea name="q" rows="1" placeholder="Enter text..."></textarea>'
                    "</label>"
                    '<input type="submit" value="Submit">'
                    "</form>"
                )
            elif line.startswith("###"):
                self.flush()
                text = line[3:].lstrip()
                anchor = self.get_anchor(text)
                self.sections.append(f"<h3 id={anchor}>{escape(text)}</h3>")
            elif line.startswith("##"):
                self.flush()
                text = line[2:].lstrip()
                anchor = self.get_anchor(text)
                self.sections.append(f"<h2 id={anchor}>{escape(text)}</h2>")
            elif line.startswith("#"):
                self.flush()
                text = line[1:].lstrip()
                anchor = self.get_anchor(text)
                self.sections.append(f"<h1 id={anchor}>{escape(text)}</h1>")
            elif line.startswith("* "):
                if not self.list_mode:
                    self.flush()
                    self.list_mode = True
                self.buffer.append(f"<li>{escape(line[1:].lstrip())}</li>")
            elif line.startswith(">"):
                if not self.quote_mode:
                    self.flush()
                    self.quote_mode = True
                self.buffer.append(escape(line[1:]))
            else:
                if self.list_mode or self.quote_mode:
                    self.flush()
                self.buffer.append(escape(line) + "\n")
        self.flush()

        body = "\n".join(self.sections)
        return f'<div class="gemini">{body}</div>\n'

    def flush(self) -> None:
        if self.buffer:
            if self.preformat_mode:
                text = "\n".join(self.buffer)
                self.sections.append(f"<pre>{text}</pre>")
            elif self.list_mode:
                text = "\n".join(self.buffer)
                self.sections.append(f"<ul>{text}</ul>")
                self.list_mode = False
            elif self.quote_mode:
                text = "\n".join(self.buffer)
                self.sections.append(f"<blockquote>{text}</blockquote>")
                self.quote_mode = False
            else:
                text = "".join(self.buffer)
                self.sections.append(f"<p>{text}</p>")
            self.buffer = []


class GeminiFlowedHandler2(GeminiFlowedHandler):
    inline_images = True
