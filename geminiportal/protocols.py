import asyncio
import re
import ssl
from contextlib import asynccontextmanager
from typing import AsyncIterator
from urllib.parse import ParseResult, quote_from_bytes, unquote_to_bytes, urlparse

# Hosts that have requested that their content be removed from the proxy
BLOCKED_HOSTS = [
    "vger.cloud",
    "warpengineer.space",
]


# Ports that the proxied servers can be hosted on
ALLOWED_PORTS = set(range(1960, 2021))
ALLOWED_PORTS |= {7070, 300, 301, 3000, 3333}


class ProxyConnectionError(Exception):
    pass


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
                    self.received = True

        # This is a private debugging hook provided by the SSL library
        context._msg_callback = msg_callback  # type: ignore

    def __bool__(self) -> bool:
        return self.received


class BaseResponse:
    """
    Encapsulates a response from the proxied server.
    """

    STATUS_CODES: dict[str, str] = {}

    status: str
    meta: str
    body: asyncio.StreamReader
    charset: str
    lang: str | None

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

    def __init__(self, status, meta, body):
        self.status = status
        self.meta = meta
        self.body = body
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

    def __init__(self, status, meta, body):
        self.status = status
        self.meta = meta
        self.body = body
        self.lang = None

        meta_params = self.get_meta_params(meta)
        self.charset = meta_params.get("charset", "UTF-8")

    def is_success(self):
        return self.status.startswith("2")

    def is_redirect(self):
        return self.status.startswith("3")


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

    def __init__(self, status, meta, body, tls_cert, tls_version, tls_cipher, tls_close_notify):
        self.status = status
        self.meta = meta
        self.body = body

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


class BaseRequest:
    """
    Encapsulates a request to the proxied server.
    """

    allowed_ports = ALLOWED_PORTS
    blocked_hosts = [re.compile(rf"(?:.+\.)?{host}\.?$", flags=re.I) for host in BLOCKED_HOSTS]

    def __init__(self, url: str, url_parts: ParseResult, host: str, port: int):
        self.url = url
        self.url_parts = url_parts
        self.host = host
        self.port = port

        self.writer: asyncio.StreamWriter | None = None

        self.validate()

    def validate(self) -> None:
        if any(pattern.match(self.host) for pattern in self.blocked_hosts):
            raise ProxyConnectionError(
                "This host has kindly requested that their content not be accessed via web proxy."
            )

        if self.port not in self.allowed_ports:
            raise ProxyConnectionError(f"Proxied content is not allowed on port {self.port}.")

    @asynccontextmanager
    async def get_response(self) -> AsyncIterator[BaseResponse]:
        response = await self.connect()
        try:
            yield response
        finally:
            await self.close()

    async def connect(self) -> BaseResponse:
        raise NotImplementedError

    async def close(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()

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

    async def connect(self) -> BaseResponse:
        context = self.create_ssl_context()
        tls_close_notify = CloseNotifyState(context)

        reader, self.writer = await asyncio.open_connection(self.host, self.port, ssl=context)
        ssock = self.writer.get_extra_info("ssl_object")

        tls_cert = ssock.getpeercert(True)
        tls_version = ssock.version()
        tls_cipher, _, _ = ssock.cipher()

        self.writer.write(f"{self.url}\r\n".encode())
        await self.writer.drain()

        raw_header = await reader.readline()
        status, meta = self.parse_header(raw_header)

        return GeminiResponse(
            status=status,
            meta=meta,
            body=reader,
            tls_cert=tls_cert,
            tls_version=tls_version,
            tls_cipher=tls_cipher,
            tls_close_notify=tls_close_notify,
        )


class SpartanRequest(BaseRequest):
    """
    Encapsulates a spartan:// request.
    """

    async def connect(self) -> BaseResponse:
        reader, self.writer = await asyncio.open_connection(self.host, self.port)

        path = self.url_parts.path or "/"
        data = unquote_to_bytes(self.url_parts.query)

        encoded_host = self.host.encode("idna")
        encoded_path = quote_from_bytes(unquote_to_bytes(path)).encode("ascii")

        self.writer.write(b"%s %s %d\r\n" % (encoded_host, encoded_path, len(data)))
        await self.writer.drain()

        if data:
            self.writer.write(data)
            await self.writer.drain()

        raw_header = await reader.readline()
        status, meta = self.parse_header(raw_header)

        return SpartanResponse(status, meta, reader)


class TxtRequest(BaseRequest):
    """
    Encapsulates a text:// request.
    """

    async def connect(self) -> BaseResponse:
        reader, self.writer = await asyncio.open_connection(self.host, self.port)

        self.writer.write(f"{self.url}\r\n".encode())
        await self.writer.drain()

        raw_header = await reader.readline()
        status, meta = self.parse_header(raw_header)

        return TxtResponse(status, meta, reader)


def build_proxy_request(url: str, url_parts: ParseResult | None = None) -> BaseRequest:
    if url_parts is None:
        url_parts = urlparse(url)

    if url_parts.hostname is None:
        raise ProxyConnectionError("Invalid proxy URL, missing hostname.")

    if url_parts.scheme == "spartan":
        return SpartanRequest(
            url=url,
            url_parts=url_parts,
            host=url_parts.hostname,
            port=url_parts.port or 300,
        )
    elif url_parts.scheme == "text":
        return TxtRequest(
            url=url,
            url_parts=url_parts,
            host=url_parts.hostname,
            port=url_parts.port or 1961,
        )
    else:
        return GeminiRequest(
            url=url,
            url_parts=url_parts,
            host=url_parts.hostname,
            port=url_parts.port or 1965,
        )
