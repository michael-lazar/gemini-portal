from __future__ import annotations

import re
from collections.abc import AsyncIterator
from typing import ClassVar

from quart import Response, render_template

from geminiportal.protocols.base import BaseResponse
from geminiportal.urls import URLReference

# Strip ANSI color characters from text responses
ANSI_ESCAPE = re.compile(
    r"""
    \x1B    # ESC
    [@-_]   # 7-bit C1 Fe
    [0-?]*  # Parameter bytes
    [ -/]*  # Intermediate bytes
    [@-~]   # Final byte
""",
    re.VERBOSE,
)


class BaseHandler:
    """
    File handler for a mimetype or set of mimetypes.
    """

    async def render(self) -> Response:
        raise NotImplementedError

    @classmethod
    def from_response(cls, response: BaseResponse):
        raise NotImplementedError


class StreamHandler(BaseHandler):
    """
    Send the proxied response stream straight through the HTTP connection.
    """

    def __init__(
        self,
        url: URLReference,
        content_iter: AsyncIterator[bytes],
        mimetype: str,
        charset: str | None = None,
    ):
        self.url = url
        self.content_iter = content_iter
        self.mimetype = mimetype
        self.charset = charset

    async def render(self) -> Response:
        content_type = self.get_content_type()
        return Response(self.content_iter, content_type=content_type)  # type: ignore

    def get_content_type(self) -> str:
        """
        Adjust the content type for text/gemini responses to allow streaming in
        the browser.
        """
        if self.mimetype == "text/gemini":
            mimetype = "text/plain"
        else:
            mimetype = self.mimetype

        if mimetype == "text/plain":
            charset = self.charset or "UTF-8"
            return f"{mimetype}; charset={charset}"
        else:
            return mimetype

    @classmethod
    async def from_response(cls, response: BaseResponse) -> StreamHandler:
        return cls(
            response.url,
            response.stream_body(),
            response.mimetype,
            response.charset,
        )


class TemplateHandler(BaseHandler):
    """
    Render the proxied response as HTML and insert it inside the page.
    """

    template: ClassVar[str]

    def __init__(
        self,
        url: URLReference,
        content: bytes,
        mimetype: str,
        charset: str | None = None,
    ):
        self.url = url
        self.content = content
        self.mimetype = mimetype
        self.charset = charset
        self._text: str | None = None

    @property
    def text(self) -> str:
        """
        Decode the content from bytes to text.
        """
        if self.charset is None:
            raise RuntimeError("Cannot access text attribute without a defined charset")

        if self._text is None:
            self._text = self.content.decode(encoding=self.charset, errors="replace")
            self._text = ANSI_ESCAPE.sub("", self._text)

        return self._text

    async def render(self) -> Response:
        context = self.get_context()
        content = await render_template(self.template, **context)
        return Response(content)

    @classmethod
    async def from_response(cls, response: BaseResponse) -> TemplateHandler:
        return cls(
            response.url,
            await response.get_body(),
            response.mimetype,
            response.charset,
        )

    def get_context(self) -> dict:
        return {}
