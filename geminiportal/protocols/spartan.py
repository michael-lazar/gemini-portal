from __future__ import annotations

from urllib.parse import quote_from_bytes, unquote_to_bytes

from geminiportal.protocols.base import BaseRequest, BaseResponse


class SpartanRequest(BaseRequest):
    """
    Encapsulates a spartan:// request.
    """

    async def fetch(self) -> SpartanResponse:
        reader, writer = await self.open_connection()

        path = self.url.path or "/"
        data = unquote_to_bytes(self.url.query)

        encoded_host = self.host.encode("idna")
        encoded_path = quote_from_bytes(unquote_to_bytes(path)).encode("ascii")

        request = b"%s %s %d\r\n%b" % (encoded_host, encoded_path, len(data), data)
        writer.write(request)
        await writer.drain()

        return SpartanResponse(self, reader, writer)


class SpartanResponse(BaseResponse):
    STATUS_CODES = {
        "2": "SUCCESS",
        "3": "REDIRECT",
        "4": "CLIENT ERROR",
        "5": "SERVER ERROR",
    }

    def __init__(self, request, reader, writer):
        self.request = request
        self.reader = reader
        self.writer = writer

        raw_header = await reader.readline()
        self.status, self.meta = self.parse_header(raw_header)

        self.mimetype, params = self.parse_meta(self.meta)
        self.charset = params.get("charset", "UTF-8")
        self.lang = None

    def is_success(self):
        return self.status == "2"

    def is_redirect(self):
        return self.status == "3"

    def is_error(self):
        return self.status.startswith(("4", "5"))
