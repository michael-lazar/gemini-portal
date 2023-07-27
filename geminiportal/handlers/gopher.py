from __future__ import annotations

from collections.abc import Iterable
from typing import Any, TypeAlias

from geminiportal.handlers.base import TemplateHandler
from geminiportal.urls import URLReference


class GopherItem:
    descriptions = {
        "0": "(FILE)",
        "1": "(DIR)",
        "2": "(CSO)",
        "3": "",
        "4": "(HQX)",
        "5": "(BIN)",
        "6": "(UUE)",
        "7": " (?) ",
        "8": "(TEL)",
        "9": "(BIN)",
        "i": "",
        "+": "",
        "h": "(HTML)",
        "H": "(HTML)",
        "g": "(IMG)",
        "I": "(IMG)",
        "s": "(SND)",
        "m": "(MIME)",
        "T": "(TEL)",
        "p": "(PNG)",
    }

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
        self.type_description = self.descriptions.get(self.item_type, "(UNKN)")

        if selector.startswith("URL:"):
            self.url = self.base.join(selector[4:])
        elif item_type == "2":
            netloc = self.get_netloc(105)
            self.url = self.base.join(f"cso://{netloc}")
        elif item_type in ("8", "T"):
            netloc = self.get_netloc(23)
            self.url = self.base.join(f"telnet://{netloc}")
        elif item_type not in ("i", "+", "3"):
            netloc = self.get_netloc(70)
            url = f"gopher://{netloc}/{self.item_type}{self.selector}"
            if self.gopher_plus_string:
                url += f"%09%09{self.gopher_plus_string}"
            self.url = self.base.join(url)
        else:
            self.url = None

        if self.url:
            self.external_indicator = self.url.get_external_indicator()
            self.mimetype = self.url.guess_mimetype()
            if self.mimetype in (
                "application/gopher-menu",
                "application/gopher+-menu",
            ):
                # Don't display gopher menu mimetype because it adds clutter
                self.mimetype = None
        else:
            self.external_indicator = None
            self.mimetype = None

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
                "".join(parts[4:]),
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

    def __init__(
        self,
        url: URLReference,
        content: bytes,
        mimetype: str,
        charset: str | None = None,
    ):
        if charset is None:
            # More correct would probably be latin-1, but more people use
            # unicode on modern gopher servers. It would be nice if we could
            # change this with a dropdown in the browser.
            charset = "utf-8"

        super().__init__(url, content, mimetype, charset)

    def get_context(self) -> dict[str, Any]:
        context = super().get_context()
        context["content"] = self.iter_content()
        return context

    def iter_content(self) -> Iterable[GopherItem]:
        for line in self.text.splitlines():
            line = line.rstrip()
            if line == ".":
                break  # Gopher directory EOF
            yield GopherItem.from_item_description(line, self.url)


GopherPlusAttributeData: TypeAlias = dict[str, Any]
GopherPlusAttributeMap: TypeAlias = dict[str, GopherPlusAttributeData]

# TODO: Make the links in the +Views clickable
# TODO: Make the admin email a hyperlink


class GopherPlusHandler(TemplateHandler):
    template = "proxy/handlers/gopherplus.html"

    attribute_map: GopherPlusAttributeMap
    active_attribute: str | None
    active_attribute_data: GopherPlusAttributeData
    line_buffer = list[str]

    def __init__(
        self,
        url: URLReference,
        content: bytes,
        mimetype: str,
        charset: str | None = None,
    ):
        if charset is None:
            # More correct would probably be latin-1, but more people use
            # unicode on modern gopher servers. It would be nice if we could
            # change this with a dropdown in the browser.
            charset = "utf-8"

        super().__init__(url, content, mimetype, charset)

    def get_context(self) -> dict[str, Any]:
        context = super().get_context()
        context["content"] = self.iter_content()
        return context

    def iter_content(self) -> Iterable[GopherPlusAttributeMap]:
        self.attribute_map = {}
        self.active_attribute = None
        self.active_attribute_data = {}
        self.line_buffer = []

        for line in self.text.splitlines():
            if line.startswith("+"):
                parts = line[1:].split(":", maxsplit=1)
                attribute = parts[0]
                if len(parts) == 1:
                    attribute_data = {}
                else:
                    item_description = parts[1]
                    if item_description.startswith(" "):
                        # Strip out the space after the colon.
                        item_description = item_description[1:]

                    item = GopherItem.from_item_description(item_description, self.url)
                    attribute_data = {"item": item}

                yield from self.flush(attribute, attribute_data)
            else:
                self.line_buffer.append(line[1:])

        yield from self.flush()

    def flush(
        self,
        attribute: str | None = None,
        attribute_data: dict | None = None,
    ) -> Iterable[GopherPlusAttributeMap]:
        # Flush the previous attribute
        if self.active_attribute:
            self.active_attribute_data["content"] = "\n".join(self.line_buffer)
            self.attribute_map[self.active_attribute] = self.active_attribute_data

        # If we're starting a new info block, yield any existing attributes
        if attribute in ("INFO", None):
            if self.attribute_map:
                yield self.attribute_map
                self.attribute_map = {}  # noqa

        self.active_attribute = attribute
        self.active_attribute_data = attribute_data or {}
        self.line_buffer = []
