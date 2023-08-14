from geminiportal.protocols.base import BaseRequest
from geminiportal.protocols.finger import FingerRequest
from geminiportal.protocols.gemini import GeminiRequest
from geminiportal.protocols.gopher import GopherRequest
from geminiportal.protocols.nex import NexRequest
from geminiportal.protocols.spartan import SpartanRequest
from geminiportal.protocols.text import TxtRequest
from geminiportal.urls import URLReference


def build_proxy_request(
    url: URLReference,
    raw_mode: bool = False,
    charset: str | None = None,
    vr_mode: bool = False,
) -> BaseRequest:
    request_class: type[BaseRequest]

    if url.scheme == "spartan":
        request_class = SpartanRequest
    elif url.scheme == "text":
        request_class = TxtRequest
    elif url.scheme == "finger":
        request_class = FingerRequest
    elif url.scheme == "gemini":
        request_class = GeminiRequest
    elif url.scheme == "nex":
        request_class = NexRequest
    elif url.scheme == "gopher":
        request_class = GopherRequest
    elif url.scheme == "gophers":
        request_class = GopherRequest
    else:
        raise ValueError(f"Unsupported URL scheme: {url.scheme}")

    return request_class(url, raw_mode, charset, vr_mode)
