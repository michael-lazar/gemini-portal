from __future__ import annotations

from geminiportal.protocols.base import (
    BaseProxyResponseBuilder,
    BaseRequest,
    BaseResponse,
)


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
        status, meta = self.parse_response_header(raw_header)

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

        self.mimetype, params = self.parse_meta(self.meta)
        self.charset = params.get("charset", "UTF-8")
        self.lang = None

        self.proxy_response_builder = TxtProxyResponseBuilder(self)


class TxtProxyResponseBuilder(BaseProxyResponseBuilder):
    response: TxtResponse

    async def build_proxy_response(self):
        if self.response.status == "2":
            return await self.render_from_handler()
        elif self.response.status == "3":
            return await self.render_redirect(self.response.meta)
        elif self.response.status in ("4", "5"):
            return await self.render_error(self.response.meta)
        else:
            return await self.render_unhandled()
