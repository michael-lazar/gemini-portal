from geminiportal.protocols.base import BaseRequest
from geminiportal.protocols.finger import FingerRequest
from geminiportal.protocols.gemini import GeminiRequest
from geminiportal.protocols.gopher import GopherRequest
from geminiportal.protocols.nex import NexRequest
from geminiportal.protocols.spartan import SpartanRequest
from geminiportal.protocols.text import TxtRequest
from geminiportal.urls import URLReference


def build_proxy_request(url: URLReference, raw_mode: bool = False) -> BaseRequest:
    if url.scheme == "spartan":
        return SpartanRequest(url, raw_mode)
    elif url.scheme == "text":
        return TxtRequest(url, raw_mode)
    elif url.scheme == "finger":
        return FingerRequest(url, raw_mode)
    elif url.scheme == "gemini":
        return GeminiRequest(url, raw_mode)
    elif url.scheme == "nex":
        return NexRequest(url, raw_mode)
    elif url.scheme == "gopher":
        return GopherRequest(url, raw_mode)
    elif url.scheme == "gophers":
        return GopherRequest(url, raw_mode)
    else:
        raise ValueError(f"Unsupported URL scheme: {url.scheme}")
