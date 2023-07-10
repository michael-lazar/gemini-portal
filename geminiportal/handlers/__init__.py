from quart import Response

from geminiportal.handlers.audio import AudioHandler
from geminiportal.handlers.base import BaseHandler, StreamHandler
from geminiportal.handlers.gemini import (
    GeminiFixedHandler,
    GeminiFlowedHandler,
    GeminiFlowedHandler2,
)
from geminiportal.handlers.image import ImageHandler
from geminiportal.handlers.text import TextHandler
from geminiportal.protocols.base import BaseResponse


async def handle_proxy_response(
    response: BaseResponse,
    raw_data: bool,
    inline_images: bool,
) -> Response:
    """
    Convert a response from the proxy server into an HTTP response object.
    """
    handler_class: type[BaseHandler]

    if raw_data:
        handler_class = StreamHandler
    elif response.mimetype.startswith("image/"):
        handler_class = ImageHandler
    elif response.mimetype.startswith("audio/mpeg"):
        handler_class = AudioHandler
    elif response.mimetype.startswith("text/plain"):
        if response.url.scheme == "text":
            handler_class = GeminiFixedHandler
        else:
            handler_class = TextHandler
    elif response.mimetype.startswith("text/gemini"):
        if inline_images:
            handler_class = GeminiFlowedHandler2
        else:
            handler_class = GeminiFlowedHandler
    elif response.mimetype.startswith("text/nex"):
        handler_class = GeminiFixedHandler
    else:
        handler_class = StreamHandler

    handler = await handler_class.from_response(response)
    return await handler.render()
