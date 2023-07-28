from __future__ import annotations

import ssl

from geminiportal.protocols.base import (
    BaseProxyResponseBuilder,
    BaseRequest,
    BaseResponse,
)


class GopherRequest(BaseRequest):
    """
    Encapsulates a gopher:// request.
    """

    async def fetch(self) -> GopherResponse | GopherPlusResponse:
        if self.url.scheme == "gophers":
            context = self.make_ssl_context()
        else:
            context = None

        reader, writer = await self.open_connection(ssl=context)

        request = self.url.get_gopher_request()
        writer.write(request)
        await writer.drain()

        if self.url.gopher_plus_string:
            # Parse the response header for gopher+
            raw_header = await reader.readline()
            header = raw_header.decode()

            if header[0] == "+":
                status, meta = "", ""
            elif header[1] == "-":
                raw_status_line = await reader.readline()
                status_line = raw_status_line.decode()
                status, meta = status_line[0], status_line[1:]
            else:
                raise ValueError("Invalid Gopher+ response header.")

            data_length = int(header[1:])

            return GopherPlusResponse(
                self,
                reader=reader,
                writer=writer,
                status=status,
                meta=meta,
                data_length=data_length,
            )
        else:
            return GopherResponse(self, reader, writer)

    def make_ssl_context(self) -> ssl.SSLContext:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context


class GopherResponse(BaseResponse):
    def __init__(self, request, reader, writer):
        self.request = request
        self.reader = reader
        self.writer = writer
        self.status = ""
        self.meta = ""
        self.lang = None

        self.mimetype = self.url.guess_mimetype() or "application/octet-stream"
        self.charset = "UTF-8"
        self.proxy_response_builder = GopherProxyResponseBuilder(self)


class GopherPlusResponse(BaseResponse):
    STATUS_CODES = {
        "": "SUCCESS",
        "1": "ITEM IS NOT AVAILABLE",
        "2": "TRY AGAIN LATER",
        "3": "ITEM HAS MOVED",
    }

    def __init__(self, request, reader, writer, status, meta, data_length):
        self.request = request
        self.reader = reader
        self.writer = writer
        self.status = status
        self.meta = meta
        self.lang = None

        # The data length flags make chunking the response stream very annoying,
        # so I'm going to ignore this feature and always wait for the server to
        # close the connection.
        self.data_length: int = data_length

        if self.status:
            # Render gopher+ error descriptions as plaintext documents.
            self.mimetype = "text/plain"
        else:
            self.mimetype = self.url.guess_mimetype() or "application/octet-stream"

        self.charset = "UTF-8"
        self.proxy_response_builder = GopherPlusProxyResponseBuilder(self)


class GopherProxyResponseBuilder(BaseProxyResponseBuilder):
    response: GopherResponse

    async def build_proxy_response(self):
        return await self.render_from_handler()


class GopherPlusProxyResponseBuilder(BaseProxyResponseBuilder):
    response: GopherPlusResponse

    async def build_proxy_response(self):
        # selectorF+<CRLF>
        #   returns document
        # selectorF!<CRLF>
        #   returns info block for the selector
        # selectorF+application/Postscript<CRLF>
        #   returns the document with the given mime type
        # selectorF$<CRLF>
        #   returns the info for every file in the directory
        # selectorF$+VIEWS+ABSTRACT<CRLF>
        #   returns just the given attributes
        return await self.render_from_handler()
