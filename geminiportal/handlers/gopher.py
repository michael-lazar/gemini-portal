from __future__ import annotations

import os.path
from collections.abc import Iterable
from typing import Any

from geminiportal.handlers.base import TemplateHandler
from geminiportal.urls import URLReference, quote_gopher


class GopherIcon:
    BASE_DIR = "/static/icons/httpd/"

    def __init__(self, short_name: str, path: str):
        self.short_name = short_name
        self.path = path

    @property
    def display(self) -> str:
        return f"({self.short_name})".center(6)

    @property
    def url(self) -> str:
        return os.path.join(self.BASE_DIR, self.path)


ICON_UNKNOWN = GopherIcon("UNKN", "generic.gif")
ICON_URL = GopherIcon("URL", "link.gif")
ICON_TYPES = {
    "0": GopherIcon("FILE", "text.gif"),
    "1": GopherIcon("DIR", "dir.gif"),
    "2": GopherIcon("CSO", "comp.gray.gif"),
    "3": GopherIcon("ERR", "broken.gif"),
    "4": GopherIcon("HQX", "binhex.gif"),
    "5": GopherIcon("DOS", "diskimg.gif"),
    "6": GopherIcon("UUE", "uuencoded.gif"),
    "7": GopherIcon("?", "index.gif"),
    "8": GopherIcon("TEL", "comp.blue.gif"),
    "9": GopherIcon("BIN", "binary.gif"),
    "h": GopherIcon("HTML", "layout.gif"),
    "H": GopherIcon("HTML", "layout.gif"),
    "g": GopherIcon("GIF", "image2.gif"),
    "I": GopherIcon("IMG", "image2.gif"),
    "s": GopherIcon("SND", "sound2.gif"),
    "M": GopherIcon("MBOX", "blank.gif"),
    "T": GopherIcon("3270", "comp.blue.gif"),
    "p": GopherIcon("PNG", "image2.gif"),
    ":": GopherIcon("BMP", "image2.gif"),
    ";": GopherIcon("MOV", "movie.gif"),
    "<": GopherIcon("SND", "sound2.gif"),
    "d": GopherIcon("DOC", "layout.gif"),
    "r": GopherIcon("RTF", "a.gif"),
    "P": GopherIcon("PDF", "pdf.gif"),
    "X": GopherIcon("XML", "pdf.gif"),
}


class GopherItem:
    url: URLReference | None

    def __init__(
        self,
        base: URLReference,
        item_type: str,
        item_text: str,
        selector: str,
        host: str,
        port: int,
        gopher_plus_string: str = "",
    ):
        self.base = base
        self.item_type = item_type
        self.item_text = item_text
        self.selector = selector
        self.host = host
        self.port = port
        self.gopher_plus_string = gopher_plus_string

        self.is_query = item_type == "7"
        self.is_url = self.item_type == "h" and self.selector.startswith("URL:")

        if self.is_url:
            self.url = self.base.join(selector[4:])
        elif item_type == "2":
            netloc = self.get_netloc(105)
            self.url = self.base.join(f"cso://{netloc}")
        elif item_type in ("8", "T"):
            netloc = self.get_netloc(23)
            self.url = self.base.join(f"telnet://{netloc}")
        elif item_type not in ("i", "+", "3"):
            netloc = self.get_netloc(70)
            url = f"gopher://{netloc}/{self.item_type}{quote_gopher(self.selector)}"
            if self.gopher_plus_string:
                url += f"%09%09{quote_gopher(self.gopher_plus_string)}"
            self.url = self.base.join(url)
        else:
            self.url = None

        if self.url:
            self.external_indicator = self.url.get_external_indicator()
            self.mimetype = self.url.guess_mimetype()
            if self.mimetype in ("application/gopher-menu", "application/gopher+-menu"):
                # Don't display gopher menu mimetype because it adds clutter
                self.mimetype = None
        else:
            self.external_indicator = None
            self.mimetype = None

        self.icon: dict | None
        if self.item_type in ("+", "i"):
            self.icon = None
        elif self.is_url:
            self.icon = ICON_URL
        else:
            self.icon = ICON_TYPES.get(self.item_type, ICON_UNKNOWN)

    @classmethod
    def from_item_description(cls, line: str, base: URLReference) -> GopherItem:
        parts = line.split("\t")
        try:
            return GopherItem(
                base,
                parts[0][0],
                parts[0][1:],
                parts[1],
                parts[2],
                int(parts[3]),
                "\t".join(parts[4:]),
            )
        except Exception:
            return GopherItem(base, "i", line, "", "", 0)

    def get_netloc(self, default_port: int):
        encoded_host = self.host.encode("idna").decode("ascii")
        if self.port == default_port:
            return encoded_host
        else:
            return f"{encoded_host}:{self.port}"


class GopherHandler(TemplateHandler):
    template = "proxy/handlers/gopher.html"

    def get_context(self) -> dict[str, Any]:
        context = super().get_context()
        context["content"] = list(self.iter_content())
        return context

    def iter_content(self) -> Iterable[GopherItem]:
        for line in self.text.splitlines():
            line = line.rstrip()
            if line == ".":
                break  # Gopher directory EOF
            yield GopherItem.from_item_description(line, self.url)
