from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from geminiportal.protocols.base import BaseResponse

from geminiportal.handlers.audio import AudioHandler
from geminiportal.handlers.base import BaseHandler, StreamHandler
from geminiportal.handlers.gemini import GeminiHandler
from geminiportal.handlers.gopher import GopherHandler
from geminiportal.handlers.image import ImageHandler
from geminiportal.handlers.nex import NexHandler
from geminiportal.handlers.text import TextHandler


def get_handler_class(response: BaseResponse) -> type[BaseHandler]:
    handler_class: type[BaseHandler]

    if response.mimetype is None:
        handler_class = StreamHandler
    elif response.mimetype.startswith("image/"):
        handler_class = ImageHandler
    elif response.mimetype.startswith("audio/"):
        handler_class = AudioHandler
    elif response.mimetype.startswith("text/plain"):
        if response.url.scheme == "text":
            handler_class = NexHandler
        else:
            handler_class = TextHandler
    elif response.mimetype.startswith("text/gemini"):
        handler_class = GeminiHandler
    elif response.mimetype.startswith("application/nex"):
        handler_class = NexHandler
    elif response.mimetype.startswith("application/gopher-menu"):
        handler_class = GopherHandler
    else:
        handler_class = StreamHandler

    return handler_class
