import re
from contextlib import asynccontextmanager
from typing import cast

from aiohttp import ClientResponse
from aiohttp.web import Application, Request, Response
from openapi_pydantic import Info, OpenAPI, Operation
from playwright.async_api import Page, expect
from pytest import mark

from aiohttp_openapi import OpenAPIApp, RedocUI
from aiohttp_openapi.tests.util import setup_test_client


async def hello(request: Request):
    return Response(text="Hello, world")


@asynccontextmanager
async def redoc_app():
    openapi_app = None

    app = Application()
    openapi_app = OpenAPIApp(
        app,
        OpenAPI(info=Info(title="test-api", version="v0.0.1")),
        doc_uis=(RedocUI(),),
    )
    openapi_app.add_route("GET", "/hello", hello, operation=Operation(tags=["foo"]))

    async with setup_test_client(app) as client:
        yield client, openapi_app


async def test_basics():
    async with redoc_app() as (client, openapi_app):
        resp: ClientResponse = await client.get(cast(OpenAPIApp, openapi_app).doc_ui_urls[0])
        assert resp.status == 200
        assert resp.content_type == "text/html"
        print(await resp.text())


@mark.playwright
async def test_e2e(page: Page):
    async with redoc_app() as (client, openapi_app):
        url = client.make_url(openapi_app.doc_ui_urls[0])
        await page.goto(str(url))
        # await page.pause()
        # Just some basic checks to assert that the schema was loaded
        await expect(page.locator("redoc")).not_to_be_empty()
        await expect(page.locator(".api-info")).to_have_text(re.compile("test-api"))
