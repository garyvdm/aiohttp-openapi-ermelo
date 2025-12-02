from contextlib import asynccontextmanager
from typing import cast

from aiohttp import ClientResponse
from aiohttp.web import Application, Request, Response
from openapi_pydantic import Info, OpenAPI, Operation
from playwright.async_api import Page, expect
from pytest import mark

from aiohttp_openapi import OpenAPIApp
from aiohttp_openapi.swagger_ui import SwaggerUI
from aiohttp_openapi.tests.util import setup_test_client


async def hello(request: Request):
    return Response(text="Hello, world")


@asynccontextmanager
async def swagger_app():
    openapi_app = None

    app = Application()
    openapi_app = OpenAPIApp(
        app,
        OpenAPI(info=Info(title="test-api", version="v0.0.1")),
        doc_uis=(SwaggerUI(),),
    )
    openapi_app.add_route("GET", "/hello", hello, operation=Operation(tags=["foo"]))

    async with setup_test_client(app) as client:
        yield client, openapi_app


async def test_basics():
    async with swagger_app() as (client, openapi_app):
        resp: ClientResponse = await client.get(cast(OpenAPIApp, openapi_app).doc_ui_urls[0])
        assert resp.status == 200
        assert resp.content_type == "text/html"
        print(await resp.text())


async def test_multiple_api():
    app = Application()
    openapi_app1 = OpenAPIApp(
        app,
        OpenAPI(info=Info(title="api 1", version="v0.0.1")),
        name="api1",
        url_base="/api1/",
        doc_uis=(SwaggerUI(),),
    )
    openapi_app1.add_route("GET", "/api1/hello", hello)

    openapi_app2 = OpenAPIApp(
        app,
        OpenAPI(info=Info(title="api 2", version="v0.0.2")),
        name="api2",
        url_base="/api2/",
        doc_uis=(SwaggerUI(),),
    )
    openapi_app2.add_route("GET", "/api2/hello", hello)

    async with setup_test_client(app) as client:
        for openapi_app in (openapi_app1, openapi_app2):
            resp: ClientResponse = await client.get(openapi_app.doc_ui_urls[0])
            assert resp.status == 200
            text = await resp.text()
            assert openapi_app.schema_url.path in text


@mark.playwright
async def test_e2e(page: Page):
    async with swagger_app() as (client, openapi_app):
        url = client.make_url(openapi_app.doc_ui_urls[0])
        await page.goto(str(url))
        # await page.pause()
        # Just some basic checks to assert that the schema was loaded
        await expect(page.locator("#swagger-ui")).not_to_be_empty()
        await expect(page.locator(".opblock-summary-path")).to_have_text("/hello")
        # This exists when there are schema errors
        await expect(page.locator(".version-pragma")).to_have_count(0)
