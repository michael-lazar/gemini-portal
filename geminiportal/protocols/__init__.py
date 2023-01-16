import re

from geminiportal.protocols.base import BaseRequest
from geminiportal.protocols.finger import FingerRequest
from geminiportal.protocols.gemini import GeminiRequest
from geminiportal.protocols.spartan import SpartanRequest
from geminiportal.protocols.text import TxtRequest
from geminiportal.urls import URLReference

# Hosts that have requested that their content be removed from the proxy
BLOCKED_HOSTS = ["vger.cloud", "warpengineer.space"]

# Ports that the proxied servers can be hosted on
ALLOWED_PORTS = {79, 7070, 300, 301, 3000, 3333, *range(1960, 2021)}


_blocked_hosts = [re.compile(rf"(?:.+\.)?{host}\.?$", flags=re.I) for host in BLOCKED_HOSTS]


def validate_url(url: URLReference) -> None:
    host, port = url.conn_info

    for pattern in _blocked_hosts:
        if pattern.match(host):
            raise ValueError(
                "This host has kindly requested that their content "
                "not be accessed via web proxy."
            )

    if port not in ALLOWED_PORTS:
        raise ValueError("Proxied content is not allowed on this port.")


def build_proxy_request(url: URLReference) -> BaseRequest:
    validate_url(url)

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
