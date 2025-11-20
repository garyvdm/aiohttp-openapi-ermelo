from contextlib import asynccontextmanager

from aiohttp.test_utils import TestClient, TestServer
from aiohttp.web import Application


@asynccontextmanager
async def setup_test_client(app: Application):
    client = TestClient(TestServer(app))
    await client.start_server()
    try:
        yield client
    finally:
        await client.close()
