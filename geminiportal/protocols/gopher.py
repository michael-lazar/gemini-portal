from __future__ import annotations

import ssl

from geminiportal.protocols.base import BaseRequest, BaseResponse


class GopherRequest(BaseRequest):
    """
    Encapsulates a gopher:// request.
    """

    async def fetch(self) -> GopherResponse:
        if self.url.scheme == "gophers":
            context = self.make_ssl_context()
        else:
            context = None

        reader, writer = await self.open_connection(ssl=context)

        request = self.url.get_gopher_request()
        writer.write(request)
        await writer.drain()

        return GopherResponse(self, reader, writer)

    def make_ssl_context(self) -> ssl.SSLContext:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context


class GopherResponse(BaseResponse):
    def __init__(self, request, reader, writer):
        self.request = request
        self.reader = reader
        self.writer = writer
        self.status = ""
        self.meta = ""
        self.lang = None

        self.mimetype = self.url.guess_mimetype() or "application/octet-stream"
        self.charset = "UTF-8"

    def is_success(self):
        return True
