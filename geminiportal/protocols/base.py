from __future__ import annotations

import asyncio
import logging
import socket
from asyncio.exceptions import IncompleteReadError
from typing import AsyncIterator

from geminiportal.urls import URLReference

_logger = logging.getLogger(__name__)

# Chunk size for streaming files, taken from the twisted FileSender class
CHUNK_SIZE = 2**14

# When not streaming, limit the maximum response size to avoid running out
# of RAM when downloading & converting large files to HTML.
MAX_BODY_SIZE = 2**25


class ProxyConnectionError(Exception):
    pass


class BaseRequest:
    """
    Encapsulates a request to a protocol.
    """

    def __init__(self, url: URLReference):
        self.url = url

    @property
    def host(self):
        return self.url.conn_info[0]

    @property
    def port(self):
        return self.url.conn_info[1]

    async def get_response(self):
        _logger.info(f"{self.__class__.__name__}: Making request to {self.url}")
        try:
            response = await self.fetch()
        except socket.gaierror:
            raise ProxyConnectionError(f'Unable to connect to host "{self.host}".')
        except OSError:
            raise ProxyConnectionError("Connection Error.")

        _logger.info(f"{self.__class__.__name__}: Response received: {response.status}")
        return response

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
    charset: str
    lang: str | None

    def __str__(self) -> str:
        return f'{self.__class__.__name__} {self.status} "{self.meta}"'

    @property
    def url(self) -> URLReference:
        return self.request.url

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
            try:
                return await self.reader.readexactly(MAX_BODY_SIZE)
            except IncompleteReadError as e:
                return e.partial
        finally:
            self.close()

    async def get_body_text(self) -> str:
        """
        Return the entire response body as a decoded text string.
        """
        body = await self.get_body()
        return body.decode(self.charset, errors="replace")

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
