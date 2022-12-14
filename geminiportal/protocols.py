from __future__ import annotations

import asyncio
import codecs
import logging
import re
import socket
import ssl
from asyncio.exceptions import IncompleteReadError
from typing import AsyncIterator
from urllib.parse import quote_from_bytes, unquote_to_bytes

from geminiportal.urls import URLReference

_logger = logging.getLogger(__name__)

# Hosts that have requested that their content be removed from the proxy
BLOCKED_HOSTS = [
    "vger.cloud",
    "warpengineer.space",
]


# Ports that the proxied servers can be hosted on
ALLOWED_PORTS = set(range(1960, 2021))
ALLOWED_PORTS |= {79, 7070, 300, 301, 3000, 3333}

# Chunk size for streaming files, taken from the twisted FileSender class
CHUNK_SIZE = 2**14

# When not streaming, limit the maximum response size to avoid running out
# of RAM when downloading & converting large files to HTML.
MAX_BODY_SIZE = 2**15


class ProxyConnectionError(Exception):
    pass


class DecodingStreamReader:
    """
    https://stackoverflow.com/questions/35036921
    """

    def __init__(self, stream, encoding="utf-8", errors="strict"):
        self.stream = stream
        self.decoder = codecs.getincrementaldecoder(encoding)(errors=errors)

    async def readline(self):
        data = await self.stream.readline()
        if isinstance(data, (bytes, bytearray)):
            data = self.decoder.decode(data)
        return data

    def at_eof(self):
        return self.stream.at_eof()


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


class BaseRequest:
    """
    Encapsulates a request to the proxied server.
    """

    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter

    allowed_ports = ALLOWED_PORTS
    blocked_hosts = [re.compile(rf"(?:.+\.)?{host}\.?$", flags=re.I) for host in BLOCKED_HOSTS]

    def __init__(self, url: URLReference):
        host, port = url.conn_info

        for pattern in self.blocked_hosts:
            if pattern.match(host):
                raise ValueError(
                    "This host has kindly requested that their content "
                    "not be accessed via web proxy."
                )

        if port not in self.allowed_ports:
            raise ValueError("Proxied content is not allowed on this port.")

        self.host = host
        self.port = port
        self.url = url

    def __str__(self) -> str:
        return f"{self.__class__.__name__} {self.url}"

    async def get_response(self):
        _logger.info(self)
        try:
            response = await self._fetch()
        except socket.gaierror:
            raise ProxyConnectionError(f'Unable to connect to host "{self.host}".')
        except OSError:
            raise ProxyConnectionError("Connection Error.")

        _logger.info(response)
        return response

    async def _fetch(self) -> BaseResponse:
        raise NotImplementedError

    def close(self) -> None:
        try:
            _logger.info("Closing socket")
            self.writer.close()
        except Exception as e:
            # This will fail if the remote server has already closed the
            # socket via SSL close_notify, but there is no way to know
            # that ahead of time.
            _logger.warning(f"Error closing socket: {e}")

    @staticmethod
    def parse_header(raw_header: bytes) -> tuple[str, str]:
        header = raw_header.decode()
        parts = header.strip().split(maxsplit=1)
        if len(parts) == 0:
            status, meta = "", ""
        elif len(parts) == 1:
            status, meta = parts[0], ""
        else:
            status, meta = parts

        return status, meta


class GeminiRequest(BaseRequest):
    """
    Encapsulates a gemini:// request.
    """

    def create_ssl_context(self) -> ssl.SSLContext:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context

    async def _fetch(self) -> GeminiResponse:
        context = self.create_ssl_context()
        tls_close_notify = CloseNotifyState(context)

        self.reader, self.writer = await asyncio.open_connection(self.host, self.port, ssl=context)
        ssock = self.writer.get_extra_info("ssl_object")

        tls_cert = ssock.getpeercert(True)
        tls_version = ssock.version()
        tls_cipher, _, _ = ssock.cipher()

        gemini_url = self.url.get_gemini_request_url()
        self.writer.write(f"{gemini_url}\r\n".encode())
        await self.writer.drain()

        raw_header = await self.reader.readline()
        status, meta = self.parse_header(raw_header)

        return GeminiResponse(
            request=self,
            status=status,
            meta=meta,
            tls_cert=tls_cert,
            tls_version=tls_version,
            tls_cipher=tls_cipher,
            tls_close_notify=tls_close_notify,
        )


class SpartanRequest(BaseRequest):
    """
    Encapsulates a spartan:// request.
    """

    async def _fetch(self) -> SpartanResponse:
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)

        path = self.url.path or "/"
        data = unquote_to_bytes(self.url.query)

        encoded_host = self.host.encode("idna")
        encoded_path = quote_from_bytes(unquote_to_bytes(path)).encode("ascii")

        request = b"%s %s %d\r\n%b" % (encoded_host, encoded_path, len(data), data)
        self.writer.write(request)
        await self.writer.drain()

        raw_header = await self.reader.readline()
        status, meta = self.parse_header(raw_header)

        return SpartanResponse(self, status, meta)


class TxtRequest(BaseRequest):
    """
    Encapsulates a text:// request.
    """

    async def _fetch(self) -> TxtResponse:
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)

        gemini_url = self.url.get_gemini_request_url()
        self.writer.write(f"{gemini_url}\r\n".encode())
        await self.writer.drain()

        raw_header = await self.reader.readline()
        status, meta = self.parse_header(raw_header)

        return TxtResponse(self, status, meta)


class FingerRequest(BaseRequest):
    """
    Encapsulates a finger:// request.
    """

    async def _fetch(self) -> FingerResponse:
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)

        request = unquote_to_bytes(self.url.finger_request)

        self.writer.write(b"%s\r\n" % request)
        await self.writer.drain()

        return FingerResponse(self)


class BaseResponse:
    """
    Encapsulates a response from the proxied server.
    """

    STATUS_CODES: dict[str, str] = {}

    request: BaseRequest
    status: str
    meta: str
    charset: str
    lang: str | None

    def __str__(self) -> str:
        return f'{self.__class__.__name__} {self.status} "{self.meta}"'

    @property
    def status_string(self) -> str:
        if self.status in self.STATUS_CODES:
            return f"{self.status} {self.STATUS_CODES[self.status].title()}"
        else:
            return self.status

    @staticmethod
    def get_meta_params(meta: str) -> dict[str, str]:
        """
        Parse & normalize extra params from the MIME string.
        """
        params = {}
        for param in meta.split(";"):
            parts = param.strip().split("=", maxsplit=1)
            if len(parts) == 2:
                params[parts[0].lower()] = parts[1]
        return params

    async def get_body(self) -> bytes:
        """
        Return the entire response body as bytes, up to the max body size.
        """
        try:
            try:
                return await self.request.reader.readexactly(MAX_BODY_SIZE)
            except IncompleteReadError as e:
                return e.partial
        finally:
            self.request.close()

    async def get_body_text(self) -> str:
        """
        Return the entire response body as text.
        """
        body = await self.get_body()
        return body.decode(self.charset, errors="replace")

    async def stream_body(self) -> AsyncIterator[bytes]:
        """
        Return a streaming iterator for the response bytes.
        """
        try:
            while chunk := await self.request.reader.read(CHUNK_SIZE):
                yield chunk
        finally:
            self.request.close()

    async def stream_text(self) -> AsyncIterator[str]:
        """
        Return a streaming iterator for the decoded body lines.
        """
        try:
            reader = DecodingStreamReader(
                self.request.reader,
                encoding=self.charset,
                errors="replace",
            )
            while line := await reader.readline():
                yield line
        finally:
            self.request.close()

    def is_input(self) -> bool:
        return False

    def is_success(self) -> bool:
        return False

    def is_redirect(self) -> bool:
        return False


class SpartanResponse(BaseResponse):

    STATUS_CODES = {
        "2": "SUCCESS",
        "3": "REDIRECT",
        "4": "CLIENT ERROR",
        "5": "SERVER ERROR",
    }

    def __init__(self, request, status, meta):
        self.request = request
        self.status = status
        self.meta = meta
        self.lang = None

        meta_params = self.get_meta_params(meta)
        self.charset = meta_params.get("charset", "UTF-8")

    def is_success(self):
        return self.status == "2"

    def is_redirect(self):
        return self.status == "3"


class TxtResponse(BaseResponse):

    STATUS_CODES = {
        "20": "OK",
        "30": "REDIRECT",
        "40": "NOK",
    }

    def __init__(self, request, status, meta):
        self.request = request
        self.status = status
        self.meta = meta
        self.lang = None

        meta_params = self.get_meta_params(meta)
        self.charset = meta_params.get("charset", "UTF-8")

    def is_success(self):
        return self.status.startswith("2")

    def is_redirect(self):
        return self.status.startswith("3")


class FingerResponse(BaseResponse):

    STATUS_CODES = {
        "": "SUCCESS",
    }

    def __init__(self, request):
        self.request = request
        self.status = ""
        self.meta = "text/plain"
        self.charset = "UTF-8"
        self.lang = None

    def is_input(self):
        return False

    def is_success(self):
        return True

    def is_redirect(self):
        return False


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
        status,
        meta,
        tls_cert,
        tls_version,
        tls_cipher,
        tls_close_notify,
    ):
        self.request = request
        self.status = status
        self.meta = meta

        self.tls_cert = tls_cert
        self.tls_version = tls_version
        self.tls_cipher = tls_cipher
        self.tls_close_notify = tls_close_notify

        meta_params = self.get_meta_params(meta)
        self.charset = meta_params.get("charset", "UTF-8")
        self.lang = meta_params.get("lang", None)

    @property
    def tls_close_notify_received(self):
        return bool(self.tls_close_notify)

    def is_input(self):
        return self.status.startswith("1")

    def is_success(self):
        return self.status.startswith("2")

    def is_redirect(self):
        return self.status.startswith("3")


def build_proxy_request(url: URLReference) -> BaseRequest:
    if url.scheme == "spartan":
        return SpartanRequest(url)
    elif url.scheme == "text":
        return TxtRequest(url)
    elif url.scheme == "finger":
        return FingerRequest(url)
    elif url.scheme == "gemini":
        return GeminiRequest(url)
    else:
        raise ValueError("Unsupported URL scheme")
