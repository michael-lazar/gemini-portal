from __future__ import annotations

from geminiportal.protocols.base import BaseRequest, BaseResponse


class TxtRequest(BaseRequest):
    """
    Encapsulates a text:// request.
    """

    async def fetch(self) -> TxtResponse:
        reader, writer = await self.open_connection()

        gemini_url = self.url.get_gemini_request_url()
        writer.write(f"{gemini_url}\r\n".encode())
        await writer.drain()

        raw_header = await reader.readline()
        status, meta = self.parse_header(raw_header)

        return TxtResponse(self, reader, writer, status, meta)


class TxtResponse(BaseResponse):
    STATUS_CODES = {
        "20": "OK",
        "30": "REDIRECT",
        "40": "NOK",
    }

    def __init__(self, request, reader, writer, status, meta):
        self.request = request
        self.reader = reader
        self.writer = writer
        self.status = status
        self.meta = meta
        self.lang = None

        self.mimetype, params = self.parse_meta(meta)
        self.charset = params.get("charset", "UTF-8")

    def is_success(self):
        return self.status.startswith("2")

    def is_redirect(self):
        return self.status.startswith("3")

    def is_error(self):
        return self.status.startswith(("4", "5"))
