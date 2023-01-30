import asyncio
import subprocess


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
