from __future__ import annotations

from quart import Response as QuartResponse
from quart import render_template
from werkzeug.utils import redirect

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

        self.mimetype, params = self.parse_meta(meta)
        self.charset = params.get("charset", "UTF-8")
        self.lang = None

        self.proxy_response_builder = TxtProxyResponseBuilder(self)


class TxtProxyResponseBuilder(BaseProxyResponseBuilder):
    response: TxtResponse

    async def build_proxy_response(self):
        if self.response.status == "2":
            return await self.render_from_handler()

        elif self.response.status == "3":
            location = self.response.url.join(self.response.meta).get_proxy_url()
            return redirect(location, 307)

        elif self.response.status in ("4", "5"):
            content = await render_template(
                "proxy/proxy-error.html",
                error=self.response.status_display,
                message=self.response.meta,
            )
            return QuartResponse(content)

        else:
            content = await render_template(
                "proxy/gateway-error.html",
                error="The response from the proxied server is unrecognized or invalid.",
            )
            return QuartResponse(content)
