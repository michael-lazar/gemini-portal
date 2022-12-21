import asyncio
import os
import tempfile

import pytest

from geminiportal.favicons import FaviconCache
from geminiportal.urls import URLReference


async def test_favicon_cache():
    url = URLReference("gemini://mozz.us")

    with tempfile.TemporaryDirectory() as tempdir:
        db_name = os.path.join(tempdir, "db-file")
        cache = FaviconCache(db_name)

        assert cache.check(url) is None
        assert len(cache.tasks) == 1

        assert cache.check(url) is None
        assert len(cache.tasks) == 1

        cache.shutdown()


@pytest.mark.integration
async def test_favicon_cache_update():
    url = URLReference("gemini://mozz.us")

    with tempfile.TemporaryDirectory() as tempdir:
        db_name = os.path.join(tempdir, "db-file")
        cache = FaviconCache(db_name)

        assert cache.check(url) is None
        assert len(cache.tasks) == 1

        task = next(iter(cache.tasks.values()))
        await asyncio.wait_for(task, 10)
        assert cache.check(url) == "🐟"
        assert len(cache.tasks) == 0

        cache.shutdown()
