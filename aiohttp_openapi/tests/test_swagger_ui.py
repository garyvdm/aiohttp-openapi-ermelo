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
        api_doc_uis=(SwaggerUI(),),
    )
    openapi_app.add_route("GET", "/", hello, Operation(tags=["foo"], description="home"))

    async with setup_test_client(app) as client:
        yield client, openapi_app


async def test_basics():
    async with swagger_app() as (client, openapi_app):
        resp: ClientResponse = await client.get(cast(OpenAPIApp, openapi_app).api_doc_ui_urls[0])
        assert resp.status == 200
        assert resp.content_type == "text/html"
        print(await resp.text())


@mark.playwright
async def test_e2e(page: Page):
    async with swagger_app() as (client, openapi_app):
        url = client.make_url(openapi_app.api_doc_ui_urls[0])
        await page.goto(str(url))
        await expect(page.locator("#swagger-ui")).not_to_be_empty()
