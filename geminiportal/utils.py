import asyncio
import subprocess
from collections.abc import AsyncIterator


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
    partial_bytes: bytes,
    content_iter: AsyncIterator[bytes],
) -> AsyncIterator[bytes]:
    yield partial_bytes
    async for chunk in content_iter:
        yield chunk
