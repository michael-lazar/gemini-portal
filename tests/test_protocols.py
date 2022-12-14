import pytest

from geminiportal.protocols import (
    GeminiRequest,
    ProxyConnectionError,
    SpartanRequest,
    TxtRequest,
    build_proxy_request,
)


def test_build_proxy_request_gemini():
    request = build_proxy_request("gemini://mozz.us/hello")
    assert isinstance(request, GeminiRequest)
    assert request.port == 1965
    assert request.host == "mozz.us"


def test_build_proxy_request_spartan():
    request = build_proxy_request("spartan://mozz.us:3000/hello")
    assert isinstance(request, SpartanRequest)
    assert request.port == 3000
    assert request.host == "mozz.us"


def test_build_proxy_request_txt():
    request = build_proxy_request("text://174.138.124.169/hello")
    assert isinstance(request, TxtRequest)
    assert request.port == 1961
    assert request.host == "174.138.124.169"


def test_build_proxy_request_missing_host():
    with pytest.raises(ProxyConnectionError):
        build_proxy_request("mozz.us")


def test_build_proxy_request_blocked_host():
    with pytest.raises(ProxyConnectionError):
        build_proxy_request("gemini://vger.cloud/hello")


def test_build_proxy_request_blocked_port():
    with pytest.raises(ProxyConnectionError):
        build_proxy_request("gemini://mozz.us:22")


async def test_real_gemini_request():
    request = build_proxy_request("gemini://mozz.us")

    async with request.get_response() as response:
        assert response.is_success()
        assert await response.body.read()

        # mozz.us (running jetforce) should always send the close notify signal
        assert response.tls_close_notify_received
        assert response.tls_cert
        assert response.tls_version
        assert response.tls_cipher

    assert request.writer.is_closing()


async def test_real_spartan_request():
    request = build_proxy_request("spartan://mozz.us/echo?hello%20world")

    async with request.get_response() as response:
        assert response.is_success()
        assert await response.body.read() == b"hello world"

    assert request.writer.is_closing()
