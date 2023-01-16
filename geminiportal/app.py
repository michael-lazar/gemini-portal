import asyncio
import logging
import subprocess
from datetime import datetime
from urllib.parse import quote

from quart import Quart, Response, escape, g, render_template, request
from quart.logging import default_handler
from werkzeug.wrappers.response import Response as WerkzeugResponse

from geminiportal.favicons import favicon_cache
from geminiportal.handlers import handle_proxy_response
from geminiportal.protocols import build_proxy_request
from geminiportal.protocols.base import ProxyConnectionError
from geminiportal.protocols.gemini import GeminiResponse
from geminiportal.urls import URLReference

logger = logging.getLogger("geminiportal")
logger.setLevel(logging.INFO)
logger.addHandler(default_handler)

app = Quart(__name__)
app.config.from_prefixed_env()


@app.errorhandler(ValueError)
async def handle_value_error(e) -> Response:
    content = await render_template("gemini.html", error=str(e), url=g.get("url"))
    return Response(content, status=400)


@app.errorhandler(ProxyConnectionError)
async def handle_unexpected_error(e):
    content = await render_template("gemini.html", error=str(e), url=g.get("url"))
    return Response(content, status=500)


@app.context_processor
def inject_context():
    kwargs = {}
    if "response" in g:
        kwargs["status"] = g.response.status_string
        kwargs["meta"] = g.response.meta
    if "url" in g:
        kwargs["url"] = g.url.get_url()
        kwargs["root_url"] = g.url.get_root_proxy_url()
        kwargs["parent_url"] = g.url.get_parent_proxy_url() or kwargs["root_url"]
    if "favicon" in g and g.favicon:
        kwargs["favicon"] = g.favicon
    return kwargs


@app.route("/robots.txt")
async def robots() -> Response:
    return await app.send_static_file("robots.txt")


@app.route("/about")
async def about() -> Response:
    now = datetime.utcnow()
    content = await render_template("about.html", year=now.year)
    return Response(content)


@app.route("/changes")
async def changes() -> Response:
    content = await render_template("changes.html")
    return Response(content)


@app.route("/")
async def home() -> Response | WerkzeugResponse:
    address = request.args.get("url")
    if address:
        # URL was provided via the address bar, redirect to the canonical endpoint
        proxy_url = URLReference(address).get_proxy_url(external=False)
        return app.redirect(proxy_url)

    content = await render_template("home.html", url="gemini://gemini.circumlunar.space")
    return Response(content)


@app.route("/<scheme>/<netloc>/", endpoint="proxy-netloc")
@app.route("/<scheme>/<netloc>/<path:path>", endpoint="proxy-path")
async def proxy(
    scheme: str = "gemini", netloc: str | None = None, path: str | None = None
) -> Response | WerkzeugResponse:
    """
    The main entrypoint for the web proxy.
    """
    address = request.args.get("url")
    if address:
        # URL was provided via the address bar, redirect to the canonical endpoint
        proxy_url = URLReference(address).get_proxy_url(external=False)
        return app.redirect(proxy_url)

    g.url = URLReference(f"{scheme}://{netloc}{'' if path is None else '/' + path}")

    query = request.args.get("q")
    if query:
        # Query was provided via the input box, redirect to the canonical endpoint
        g.url.query = quote(query)
        proxy_url = g.url.get_proxy_url(external=False)
        return app.redirect(proxy_url)

    proxy_request = build_proxy_request(g.url)
    response = await proxy_request.get_response()
    g.response = response

    g.favicon = favicon_cache.check(g.url)

    if request.args.get("raw_crt"):
        if not isinstance(response, GeminiResponse):
            raise ValueError("Cannot download certificate for non-TLS schemes")

        return Response(
            response.tls_cert,
            content_type="application/x-x509-ca-cert",
            headers={
                "Content-Disposition": f"attachment; filename={request.host}.cer",
            },
        )

    if request.args.get("crt"):
        if not isinstance(response, GeminiResponse):
            raise ValueError("Cannot download certificate for non-TLS schemes")

        await response.get_body()
        body = await build_certificate_page_body(response)
        content = await render_template("gemini.html", body=body)
        return Response(content)

    if response.is_input():
        secret = response.status == "11"
        content = await render_template("gemini.html", query=1, secret=secret)
        return Response(content)

    if response.is_redirect():
        location = g.url.join(response.meta).get_proxy_url()
        return app.redirect(location, 307)

    if response.is_success():
        return await handle_proxy_response(
            response=response,
            raw_data=bool(request.args.get("raw")),
            inline_images=bool(request.args.get("inline")),
        )

    content = await render_template("gemini.html")
    return Response(content)


async def build_certificate_page_body(response: GeminiResponse) -> str:
    proc = await asyncio.create_subprocess_exec(
        *["openssl", "x509", "-inform", "DER", "-text"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate(response.tls_cert)
    output = stdout.decode(errors="ignore")

    body = await render_template(
        "fragments/tls_context.html",
        openssl_output=escape(output),
        raw_cert_url=g.url.get_proxy_url(raw_crt=1),
        tls_close_notify_received=response.tls_close_notify_received,
        tls_version=response.tls_version,
        tls_cipher=response.tls_cipher,
    )
    return body


if __name__ == "__main__":
    app.config["DEBUG"] = True
    app.config["SERVER_NAME"] = None
    app.run()
