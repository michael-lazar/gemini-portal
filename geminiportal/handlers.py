import re
from collections import Counter
from typing import AsyncIterator, Iterator

from quart import Response, escape, render_template

from geminiportal.protocols import BaseResponse
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
    raw_url = response.request.url.get_proxy_url(raw=1)
    inline_url = response.request.url.get_proxy_url(inline=1)

    if hasattr(response, "tls_cert"):
        cert_url = response.request.url.get_proxy_url(crt=1)
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
        handler_class: type[BaseFileHandler]

        if response.meta.startswith("text/plain"):
            if response.request.url.scheme == "text":
                handler_class = GeminiFixedHandler
            else:
                handler_class = TextFixedHandler
        else:
            if inline_images:
                handler_class = GeminiInlineFlowedHandler
            else:
                handler_class = GeminiFlowedHandler

        context["body"] = await handler_class(response.stream_text(), response.request.url).run()
        context["lang"] = response.lang
        content = await render_template("gemini.html", **context)
        return Response(content)

    else:
        return Response(response.stream_body(), content_type=response.meta)  # type: ignore


class BaseFileHandler:
    def __init__(self, text: AsyncIterator[str], url: URLReference):
        self.text = text
        self.url = url

    async def run(self) -> str:
        tokens = []
        async for token in self.process():  # noqa
            tokens.append(token)
        return "".join(tokens)

    async def process(self):
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


class TextFixedHandler(BaseFileHandler):
    """
    Everything in a single <pre> block.
    """

    async def process(self) -> AsyncIterator[str]:
        yield "<pre>"
        async for line in self.text:
            yield escape(line.rstrip() + "\n")
        yield "</pre>"


class GeminiFixedHandler(BaseFileHandler):
    """
    Everything in a single <pre> block, with => links supported.
    """

    async def process(self) -> AsyncIterator[str]:
        yield "<pre>"
        async for line in self.text:
            line = line.rstrip()
            if line.startswith("=>"):
                url, link_text = self.parse_gemini_link_line(line[2:])
                proxy_url = url.get_proxy_url()
                yield f'<a href="{escape(proxy_url)}">{escape(link_text)}</a>\n'
            else:
                yield escape(line.rstrip() + "\n")
        yield "</pre>"


class GeminiFlowedHandler(BaseFileHandler):
    """
    The full-featured gemtext -> html converter.
    """

    inline_images = False

    def __init__(self, text: AsyncIterator[str], url: URLReference):
        super().__init__(text, url)

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

    async def process(self) -> AsyncIterator[str]:
        yield '<div class="gemini">'
        async for line in self.text:
            line = line.rstrip()
            line = RABBIT_INLINE.sub("🐇", line)
            if line.startswith("```"):
                # python doesn't support "yield from" inside async functions,
                # which means I need to use this annoyingly verbose for loop.
                for token in self.flush():
                    yield token
                self.preformat_mode = not self.preformat_mode
            elif self.preformat_mode:
                if line == RABBIT_STANDALONE:
                    line = RABBIT_ART
                self.buffer.append(escape(line))
            elif line == RABBIT_STANDALONE:
                for token in self.flush():
                    yield token
                yield f"<pre>{RABBIT_ART}</pre>\n"
            elif line.startswith("=>"):
                for token in self.flush():
                    yield token
                url, link_text = self.parse_gemini_link_line(line[2:])
                gemini_link, link_text = self.parse_gemini_link_line(line[2:])
                mime_type = url.guess_mimetype()
                if self.inline_images and mime_type and mime_type.startswith("image"):
                    image_url = url.get_proxy_url(raw=True)
                    yield (
                        f'<figure><a href="{escape(image_url)}">'
                        f'<img src="{escape(image_url)}" alt="{escape(link_text)}"></img>'
                        f"</a><figcaption>{escape(link_text)}</figcaption></figure>\n"
                    )
                else:
                    image_url = url.get_proxy_url()
                    yield f'<a href="{escape(image_url)}">{escape(link_text)}</a><br/>\n'
            elif line.startswith("=:"):
                for token in self.flush():
                    yield token
                url, link_text = self.parse_gemini_link_line(line[2:])
                proxy_url = url.get_proxy_url()
                yield (
                    f'<form method="get" action="{escape(proxy_url)}" class="input-line">'
                    f"<label>{escape(link_text)}"
                    '<textarea name="q" rows="1" placeholder="Enter text..."></textarea>'
                    "</label>"
                    '<input type="submit" value="Submit">'
                    "</form>\n"
                )
            elif line.startswith("###"):
                for token in self.flush():
                    yield token
                text = line[3:].lstrip()
                anchor = self.get_anchor(text)
                yield f"<h3 id={anchor}>{escape(text)}</h3>\n"
            elif line.startswith("##"):
                for token in self.flush():
                    yield token
                text = line[2:].lstrip()
                anchor = self.get_anchor(text)
                yield f"<h2 id={anchor}>{escape(text)}</h3>\n"
            elif line.startswith("#"):
                for token in self.flush():
                    yield token
                text = line[1:].lstrip()
                anchor = self.get_anchor(text)
                yield f"<h1 id={anchor}>{escape(text)}</h3>\n"
            elif line.startswith("* "):
                if not self.list_mode:
                    for token in self.flush():
                        yield token
                    self.list_mode = True
                self.buffer.append(f"<li>{escape(line[1:].lstrip())}</li>")
            elif line.startswith(">"):
                if not self.quote_mode:
                    for token in self.flush():
                        yield token
                    self.quote_mode = True
                self.buffer.append(escape(line[1:]))
            else:
                if self.list_mode or self.quote_mode:
                    for token in self.flush():
                        yield token
                self.buffer.append(escape(line) + "\n")
        for token in self.flush():
            yield token
        yield "</div>"

    def flush(self) -> Iterator[str]:
        if self.buffer:
            if self.preformat_mode:
                text = "\n".join(self.buffer)
                yield f"<pre>{text}</pre>\n"
            elif self.list_mode:
                text = "\n".join(self.buffer)
                yield f"<ul>{text}</ul>\n"
                self.list_mode = False
            elif self.quote_mode:
                text = "\n".join(self.buffer)
                yield f"<blockquote>{text}</blockquote>\n"
                self.quote_mode = False
            else:
                text = "".join(self.buffer)
                yield f"<p>{text}</p>\n"
            self.buffer = []


class GeminiInlineFlowedHandler(GeminiFlowedHandler):
    inline_images = True
