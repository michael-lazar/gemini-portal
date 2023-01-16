import re
from collections import Counter

from quart import Response, escape, render_template

from geminiportal.protocols.base import BaseResponse
from geminiportal.urls import URLReference

# Strip ANSI color characters
ansi_escape = re.compile(
    r"""
    \x1B    # ESC
    [@-_]   # 7-bit C1 Fe
    [0-?]*  # Parameter bytes
    [ -/]*  # Intermediate bytes
    [@-~]   # Final byte
""",
    re.VERBOSE,
)

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

URL_RE = re.compile(rf"(?:{'|'.join(URL_SCHEMES)})://\S+\w", flags=re.UNICODE)

RABBIT_INLINE = re.compile(":rаbbiΤ:")
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


async def handle_proxy_response(
    response: BaseResponse,
    raw_data: bool,
    inline_images: bool,
) -> Response:
    """
    Convert a response from the proxy server into an HTTP response object.
    """
    raw_url = response.url.get_proxy_url(raw=1)
    inline_url = response.url.get_proxy_url(inline=1)

    if hasattr(response, "tls_cert"):
        cert_url = response.url.get_proxy_url(crt=1)
    else:
        cert_url = None

    context = {
        "raw_url": raw_url,
        "inline_url": inline_url,
        "cert_url": cert_url,
    }

    if raw_data:
        meta = response.meta.replace("text/gemini", "text/plain")
        if meta.startswith("text/plain") and "charset" not in meta:
            meta += "; charset=UTF-8"
        return Response(response.stream_body(), content_type=meta)  # type: ignore

    elif response.meta.startswith("image/"):
        context["body"] = f'<a href="{escape(raw_url)}"><img src="{escape(raw_url)}"></img></a>'
        content = await render_template("gemini.html", **context)
        return Response(content)

    elif response.meta.startswith("audio/mpeg"):
        context["body"] = f'<audio controls="controls"><source src="{escape(raw_url)}"/></audio>'
        content = await render_template("gemini.html", **context)
        return Response(content)

    elif response.meta.startswith(("text/plain", "text/gemini")):
        handler_class: type[BaseHandler]

        if response.meta.startswith("text/plain"):
            if response.url.scheme == "text":
                handler_class = GeminiFixedHandler
            else:
                handler_class = TextFixedHandler
        else:
            if inline_images:
                handler_class = GeminiInlineFlowedHandler
            else:
                handler_class = GeminiFlowedHandler

        text = await response.get_body_text()
        handler = handler_class(text, response.url)

        context["body"] = handler.process()
        context["lang"] = response.lang
        content = await render_template("gemini.html", **context)
        return Response(content)

    else:
        return Response(response.stream_body(), content_type=response.meta)  # type: ignore


class BaseHandler:
    def __init__(self, text: str, url: URLReference):
        self.text = ansi_escape.sub("", text)
        self.url = url

    def process(self) -> str:
        raise NotImplementedError

    def parse_gemini_link_line(self, line: str) -> tuple[URLReference, str]:
        parts = line.split(maxsplit=1)
        if len(parts) == 0:
            link, link_text = "", ""
        elif len(parts) == 1:
            link, link_text = parts[0], parts[0]
        else:
            link, link_text = parts

        url = self.url.join(link)
        return url, link_text


class TextFixedHandler(BaseHandler):
    """
    Everything in a single <pre> block, with URLs converted into links.
    """

    def process(self) -> str:
        buffer = []
        for line in self.text.splitlines(keepends=False):
            line = escape(line)
            line = URL_RE.sub(self.insert_anchor, line)
            buffer.append(line)

        body = "\n".join(buffer)
        return f"<pre>{body}</pre>\n"

    def insert_anchor(self, match: re.Match) -> str:
        url = URLReference(match.group())
        return f'<a href="{url.get_proxy_url()}">{url}</a>'


class GeminiFixedHandler(BaseHandler):
    """
    Everything in a single <pre> block, with => links supported.
    """

    def process(self) -> str:
        buffer = []
        for line in self.text.splitlines(keepends=False):
            line = line.rstrip()
            if line.startswith("=>"):
                url, link_text = self.parse_gemini_link_line(line[2:])
                proxy_url = url.get_proxy_url()
                buffer.append(f'<a href="{escape(proxy_url)}">{escape(link_text)}</a>')
            else:
                buffer.append(escape(line))

        body = "\n".join(buffer)
        return f"<pre>{body}</pre>\n"


class GeminiFlowedHandler(BaseHandler):
    """
    The full-featured gemtext -> html converter.
    """

    inline_images = False

    def __init__(self, text: str, url: URLReference):
        super().__init__(text, url)

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

    def process(self) -> str:
        for line in self.text.splitlines(keepends=False):
            line = line.rstrip()
            line = RABBIT_INLINE.sub("🐇", line)
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
                url, link_text = self.parse_gemini_link_line(line[2:])
                gemini_link, link_text = self.parse_gemini_link_line(line[2:])
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
                url, link_text = self.parse_gemini_link_line(line[2:])
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


class GeminiInlineFlowedHandler(GeminiFlowedHandler):
    inline_images = True
