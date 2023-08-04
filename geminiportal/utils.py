import asyncio
import subprocess
from collections.abc import AsyncIterator

from emoji import is_emoji

from geminiportal.urls import URLReference


async def describe_tls_cert(tls_cert: bytes) -> str:
    """
    Use openssl to print details about the given TLS certificate data.
    """
    proc = await asyncio.create_subprocess_exec(
        *["openssl", "x509", "-inform", "DER", "-text"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate(tls_cert)
    return stdout.decode(errors="ignore")


async def prepend_bytes_to_iterator(
    partial_bytes: bytes, content_iter: AsyncIterator[bytes]
) -> AsyncIterator[bytes]:
    yield partial_bytes

    async for chunk in content_iter:
        yield chunk


def parse_link_line(line: str, base: URLReference) -> tuple[URLReference, str, str]:
    # Prefix is part of the text at the beginning of the link
    # description that shouldn't be underlined.
    prefix = ""

    parts = line.split(maxsplit=1)
    if len(parts) == 1:
        link, link_text = parts[0], parts[0]
    else:
        link, link_text = parts
        prefix, link_text = split_emoji(link_text)
        if prefix:
            # Add a space after the emoji, this just makes it easier to insert
            # into a template string without using a conditional statement
            prefix = prefix + " "

    link_text = link_text.strip()
    url = base.join(link)
    return url, link_text, prefix


def split_emoji(line: str) -> tuple[str, str]:
    """
    Strips out a potential emoji at the beginning on a line of text.
    """
    for i in range(4, 0, -1):
        # Start with 4 characters and work backwards to 1 to check for
        # emojis that span multiple code points.
        if is_emoji(line[:i]):
            emoji = line[:i]
            link_text = line[i + 1 :].strip()
            return emoji, link_text

    return "", line
