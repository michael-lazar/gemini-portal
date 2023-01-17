from geminiportal.protocols.base import BaseRequest
from geminiportal.protocols.finger import FingerRequest
from geminiportal.protocols.gemini import GeminiRequest
from geminiportal.protocols.spartan import SpartanRequest
from geminiportal.protocols.text import TxtRequest
from geminiportal.urls import URLReference


def build_proxy_request(url: URLReference) -> BaseRequest:
    if url.scheme == "spartan":
        return SpartanRequest(url)
    elif url.scheme == "text":
        return TxtRequest(url)
    elif url.scheme == "finger":
        return FingerRequest(url)
    elif url.scheme == "gemini":
        return GeminiRequest(url)
    else:
        raise ValueError("Unsupported URL scheme")
