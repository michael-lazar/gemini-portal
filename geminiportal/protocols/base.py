from __future__ import annotations

import asyncio
import logging
import re
import socket
from asyncio.exceptions import IncompleteReadError
from collections.abc import AsyncIterator

from geminiportal.urls import URLReference

_logger = logging.getLogger(__name__)

# Chunk size for streaming files, taken from the twisted FileSender class
CHUNK_SIZE = 2**14

# When not streaming, limit the maximum response size to avoid running out
# of RAM when downloading & converting large files to HTML.
MAX_BODY_SIZE = 2**20

# Hosts that have requested that their content be removed from the proxy
BLOCKED_HOSTS = [
    "vger.cloud",
    "warpengineer.space",
    "michaelnordmeyer.com",
]

# Ports that the proxied servers can be hosted on
ALLOWED_PORTS = {
    70,
    79,
    300,
    301,
    3000,
    3333,
    1900,
    *range(1960, 2021),
    *range(7000, 7100),
}

# Time waiting to establish a connection before aborting
CONNECT_TIMEOUT = 10


class ProxyError(Exception):
    pass


class ProxyResponseSizeError(ProxyError):
    def __init__(self, partial: bytes):
        super().__init__(f"Maximum response size of {len(partial)} bytes read.")
        self.partial = partial


class BaseRequest:
    """
    Encapsulates a request to a protocol.
    """

    _blocked_hosts = [re.compile(rf"(?:.+\.)?{host}\.?$", flags=re.I) for host in BLOCKED_HOSTS]

    def __init__(self, url: URLReference):
        self.url = url
        self.host, self.port = url.conn_info

        self.clean()

    def clean(self):
        for pattern in self._blocked_hosts:
            if pattern.match(self.host):
                raise ValueError(
                    "This host has kindly requested that their content "
                    "not be accessed via web proxy."
                )
        if self.port not in ALLOWED_PORTS:
            raise ValueError(f"Proxied content is disabled over port {self.port}.")

    async def get_response(self):
        _logger.info(f"{self.__class__.__name__}: Making request to {self.url}")
        try:
            response = await self.fetch()
        except socket.gaierror:
            raise ProxyError(f'Unable to establish connection with host "{self.host}"')
        except OSError as e:
            raise ProxyError(f"Connection error: {e}")

        _logger.info(f"{self.__class__.__name__}: Response received: {response.status}")
        return response

    async def open_connection(self, **kwargs) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        future = asyncio.open_connection(self.host, self.port, **kwargs)
        try:
            return await asyncio.wait_for(future, timeout=CONNECT_TIMEOUT)
        except asyncio.TimeoutError:
            raise ProxyError("Timeout establishing connection with server")

    async def fetch(self) -> BaseResponse:
        raise NotImplementedError

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


class BaseResponse:
    """
    Encapsulates a response from the proxied server.
    """

    STATUS_CODES: dict[str, str] = {}

    request: BaseRequest
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    status: str
    meta: str
    mimetype: str
    charset: str
    lang: str | None

    def __str__(self) -> str:
        return f'{self.__class__.__name__} {self.status} "{self.meta}"'

    @property
    def url(self) -> URLReference:
        return self.request.url

    @property
    def status_display(self) -> str:
        if self.status in self.STATUS_CODES:
            return f"{self.status} {self.STATUS_CODES[self.status].title()}"
        else:
            return self.status

    @staticmethod
    def parse_meta(meta: str) -> tuple[str, dict[str, str]]:
        """
        Parse & normalize extra params from the MIME string.
        """
        parts = meta.split(";", maxsplit=1)
        if len(parts) == 2:
            mimetype, extra = parts
        else:
            mimetype, extra = parts[0], ""
        mimetype = mimetype.strip()

        params = {}
        for param in extra.split(";"):
            parts = param.strip().split("=", maxsplit=1)
            if len(parts) == 2:
                params[parts[0].lower()] = parts[1]

        return mimetype, params

    def close(self) -> None:
        """
        Close the socket connection.
        """
        _logger.info("Closing socket")
        try:
            self.writer.close()
        except Exception as e:
            # This will fail if the remote server has already closed the
            # socket via SSL close_notify, but there is no way to know
            # that ahead of time.
            _logger.warning(f"Error closing socket: {e}")

    async def get_body(self) -> bytes:
        """
        Return the entire response body as bytes, up to the max body size.
        """
        try:
            data = await self.reader.readexactly(MAX_BODY_SIZE)
        except IncompleteReadError as e:
            # If EOF was received before the MAX_BODY_SIZE, success!
            # Even though this says "partial", it's the entire body.
            self.close()
            return e.partial
        except Exception:
            self.close()
            raise
        else:
            # We have reached the MAX_BODY_SIZE before the EOF was
            # received. Don't close the connection just yet, because
            # we may want to continue streaming the connection.
            raise ProxyResponseSizeError(data)

    async def stream_body(self) -> AsyncIterator[bytes]:
        """
        Return a streaming iterator for the response bytes.
        """
        try:
            while chunk := await self.reader.read(CHUNK_SIZE):
                yield chunk
        finally:
            self.close()

    def is_input(self) -> bool:
        return False

    def is_success(self) -> bool:
        return False

    def is_redirect(self) -> bool:
        return False

    def is_error(self) -> bool:
        return False

    def is_cert_required(self) -> bool:
        return False
