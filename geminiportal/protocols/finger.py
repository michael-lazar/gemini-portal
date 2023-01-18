from __future__ import annotations

from urllib.parse import unquote_to_bytes

from geminiportal.protocols.base import BaseRequest, BaseResponse


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
    STATUS_CODES = {"": "SUCCESS"}

    def __init__(self, request, reader, writer):
        self.request = request
        self.reader = reader
        self.writer = writer
        self.status = ""
        self.meta = "text/plain"
        self.mimetype = "text/plain"
        self.charset = "UTF-8"
        self.lang = None

    def is_input(self):
        return False

    def is_success(self):
        return True

    def is_redirect(self):
        return False
