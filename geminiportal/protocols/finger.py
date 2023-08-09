from __future__ import annotations

from urllib.parse import unquote_to_bytes

from geminiportal.protocols.base import (
    BaseProxyResponseBuilder,
    BaseRequest,
    BaseResponse,
)


class FingerRequest(BaseRequest):
    """
    Encapsulates a finger:// request.
    """

    async def fetch(self) -> FingerResponse:
        reader, writer = await self.open_connection()

        request = unquote_to_bytes(self.url.finger_request)

        writer.write(b"%s\r\n" % request)
        await writer.drain()

        return FingerResponse(self, reader, writer)


class FingerResponse(BaseResponse):
    def __init__(self, request, reader, writer):
        self.request = request
        self.reader = reader
        self.writer = writer
        self.status = ""
        self.meta = ""
        self.mimetype = "text/plain"
        self.charset = None
        self.lang = None
        self.proxy_response_builder = FingerProxyResponseBuilder(self)


class FingerProxyResponseBuilder(BaseProxyResponseBuilder):
    response: FingerResponse

    async def build_proxy_response(self):
        return await self.render_from_handler()
