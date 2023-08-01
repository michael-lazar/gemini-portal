from __future__ import annotations

import logging
import ssl

from quart import Response as QuartResponse
from quart import render_template

from geminiportal.protocols.base import (
    BaseProxyResponseBuilder,
    BaseRequest,
    BaseResponse,
)

_logger = logging.getLogger(__name__)


class CloseNotifyState:
    """
    Inject into the SSL context to register if the TLS close_notify signal
    was received at the end of the connection.
    """

    def __init__(self, context: ssl.SSLContext):
        self.received: bool = False

        def msg_callback(connection, direction, v, c, m, data):
            if m == ssl._TLSAlertType.CLOSE_NOTIFY:  # type: ignore  # noqa
                if direction == "read":
                    _logger.info("CLOSE_NOTIFY received")
                    self.received = True

        # This is a private debugging hook provided by the SSL library
        context._msg_callback = msg_callback  # type: ignore

    def __bool__(self) -> bool:
        return self.received


class GeminiRequest(BaseRequest):
    """
    Encapsulates a gemini:// request.
    """

    def create_ssl_context(self) -> ssl.SSLContext:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context

    async def fetch(self) -> GeminiResponse:
        context = self.create_ssl_context()
        tls_close_notify = CloseNotifyState(context)

        reader, writer = await self.open_connection(ssl=context)
        ssock = writer.get_extra_info("ssl_object")

        tls_cert = ssock.getpeercert(True)
        tls_version = ssock.version()
        tls_cipher, _, _ = ssock.cipher()

        gemini_url = self.url.get_gemini_request_url()
        writer.write(f"{gemini_url}\r\n".encode())
        await writer.drain()

        raw_header = await reader.readline()
        status, meta = self.parse_response_header(raw_header)

        return GeminiResponse(
            request=self,
            reader=reader,
            writer=writer,
            status=status,
            meta=meta,
            tls_cert=tls_cert,
            tls_version=tls_version,
            tls_cipher=tls_cipher,
            tls_close_notify=tls_close_notify,
        )


class GeminiResponse(BaseResponse):
    STATUS_CODES = {
        "10": "INPUT",
        "11": "SENSITIVE INPUT",
        "20": "SUCCESS",
        "30": "REDIRECT - TEMPORARY",
        "31": "REDIRECT - PERMANENT",
        "40": "TEMPORARY FAILURE",
        "41": "SERVER UNAVAILABLE",
        "42": "CGI ERROR",
        "43": "PROXY ERROR",
        "44": "SLOW DOWN",
        "50": "PERMANENT FAILURE",
        "51": "NOT FOUND",
        "52": "GONE",
        "53": "PROXY REQUEST REFUSED",
        "59": "BAD REQUEST",
        "60": "CLIENT CERTIFICATE REQUIRED",
        "61": "CERTIFICATE NOT AUTHORISED",
        "62": "CERTIFICATE NOT VALID",
    }

    tls_cert: bytes | None
    tls_version: str
    tls_cipher: str
    tls_close_notify: CloseNotifyState

    def __init__(
        self,
        request,
        reader,
        writer,
        status,
        meta,
        tls_cert,
        tls_version,
        tls_cipher,
        tls_close_notify,
    ):
        self.request = request
        self.reader = reader
        self.writer = writer
        self.status = status
        self.meta = meta

        self.tls_cert = tls_cert
        self.tls_version = tls_version
        self.tls_cipher = tls_cipher
        self.tls_close_notify = tls_close_notify

        self.mimetype, params = self.parse_meta(self.meta)
        self.charset = params.get("charset", "UTF-8")
        self.lang = params.get("lang", None)

        self.proxy_response_builder = GeminiProxyResponseBuilder(self)

    @property
    def tls_close_notify_received(self):
        return bool(self.tls_close_notify)

    def get_response_table(self):
        return {"Status": self.status_display, "Meta": self.meta}


class GeminiProxyResponseBuilder(BaseProxyResponseBuilder):
    response: GeminiResponse

    async def build_proxy_response(self):
        if self.response.status.startswith("1"):
            content = await render_template(
                "proxy/gemini-query.html",
                secret=self.response.status == "11",
                prompt=self.response.meta,
            )
            return QuartResponse(content)
        if self.response.status.startswith("2"):
            return await self.render_from_handler()
        elif self.response.status.startswith("3"):
            return self.render_redirect(self.response.meta)
        elif self.response.status.startswith(("4", "5")):
            return await self.render_error(self.response.meta)
        elif self.response.status.startswith("6"):
            content = await render_template("proxy/gemini-cert-required.html")
            return QuartResponse(content)
        else:
            return await self.render_unhandled()
